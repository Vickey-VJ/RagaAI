import streamlit as st
import requests
import os
import base64
import io
import json

# Configuration
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_SERVICE_URL", "http://localhost:8006")
ORCHESTRATOR_QUERY_ENDPOINT = f"{ORCHESTRATOR_URL}/orchestrate/query/"

# Determine if we're running on Streamlit Cloud
is_streamlit_cloud = os.getenv("STREAMLIT_SHARING", "") == "True" or os.getenv("STREAMLIT_SERVER_HEADLESS", "") == "True"

st.set_page_config(layout="wide", page_title="Finance Assistant")

st.title("Multi-Source Finance Assistant")

# Initialize session state variables
if 'last_query' not in st.session_state:
    st.session_state.last_query = ""
if 'text_response' not in st.session_state:
    st.session_state.text_response = ""
if 'audio_response_bytes' not in st.session_state:
    st.session_state.audio_response_bytes = None
if 'analysis_details' not in st.session_state:
    st.session_state.analysis_details = None
if 'error_message' not in st.session_state:
    st.session_state.error_message = ""
if 'query_in_progress' not in st.session_state:
    st.session_state.query_in_progress = False


with st.sidebar:
    st.header("Controls")
    output_format = st.radio("Response Format", ("Text", "Voice"), index=0)
    # Potentially add other controls here later, e.g., top_k for retrieval

st.header("Ask a financial question:")

query = st.text_input("E.g., What’s our risk exposure in Asia tech stocks today, and highlight any earnings surprises?", value=st.session_state.last_query)

if st.button("Get Briefing", disabled=st.session_state.query_in_progress):
    if query:
        st.session_state.last_query = query
        st.session_state.text_response = ""
        st.session_state.audio_response_bytes = None
        st.session_state.analysis_details = None
        st.session_state.error_message = ""
        st.session_state.query_in_progress = True
        
        st.info("Processing your query... This may take a moment.")

        try:
            if is_streamlit_cloud:
                # Mock response for Streamlit Cloud
                st.session_state.text_response = (
                    "This is a demo version running on Streamlit Cloud. "
                    "In this environment, the backend services are not available.\n\n"
                    f"Your query was: **{query}**\n\n"
                    "To run the full application with all services, please run it locally "
                    "following the instructions in the README.md file."
                )
                # Add some mock analysis details for demonstration
                st.session_state.analysis_details = {
                    "query": query,
                    "source_count": 3,
                    "sentiment": "neutral",
                    "key_entities": ["finance", "stocks", "investment"],
                    "note": "This is simulated data for the cloud demo."
                }
            else:
                payload = {
                    "query": query,
                    "output_format": "voice" if output_format == "Voice" else "text"
                }
                
                response = requests.post(ORCHESTRATOR_QUERY_ENDPOINT, json=payload, timeout=180) # Increased timeout

            if response.status_code == 200:
                if payload["output_format"] == "voice":
                    # Check if response is audio
                    if 'audio/' in response.headers.get('Content-Type', '').lower():
                        st.session_state.audio_response_bytes = response.content
                        st.session_state.text_response = "Voice response generated. Playing below." # Placeholder
                        
                        # Make a second call to get the text part
                        text_payload = {"query": query, "output_format": "text"}
                        text_response_data = requests.post(ORCHESTRATOR_QUERY_ENDPOINT, json=text_payload, timeout=180)
                        if text_response_data.status_code == 200:
                            text_json = text_response_data.json()
                            st.session_state.text_response = text_json.get("text_response", "Could not retrieve text summary for voice.")
                            st.session_state.analysis_details = text_json.get("analysis_details")
                        else:
                            st.session_state.text_response = "Voice response generated, but could not retrieve accompanying text."

                    else: # Should be JSON if not audio
                        json_response = response.json()
                        st.session_state.text_response = json_response.get("text_response")
                        st.session_state.analysis_details = json_response.get("analysis_details")
                        if "voice_response_bytes" in json_response and json_response["voice_response_bytes"]:
                            st.session_state.audio_response_bytes = base64.b64decode(json_response["voice_response_bytes"])

                else: # Text output format
                    json_response = response.json()
                    st.session_state.text_response = json_response.get("text_response")
                    st.session_state.analysis_details = json_response.get("analysis_details")
                    st.session_state.audio_response_bytes = None # Ensure no old audio plays

            elif response.status_code == 503:
                st.session_state.error_message = "Orchestrator service is not available. Please ensure all services are running."
            else:
                try:
                    error_detail = response.json().get("detail", response.text)
                except requests.exceptions.JSONDecodeError:
                    error_detail = response.text
                st.session_state.error_message = f"Error from orchestrator: {response.status_code} - {error_detail}"

        except requests.exceptions.Timeout:
            st.session_state.error_message = "The request timed out. The orchestrator might be taking too long."
        except requests.exceptions.ConnectionError:
            st.session_state.error_message = (
                f"Could not connect to the Orchestrator Service at {ORCHESTRATOR_QUERY_ENDPOINT}. "
                "Please ensure it's running and accessible."
            )
        except Exception as e:
            if not is_streamlit_cloud:  # Don't show technical errors in the cloud demo
                st.session_state.error_message = f"An unexpected error occurred: {str(e)}"
        finally:
            st.session_state.query_in_progress = False
            st.rerun() # Rerun to update UI based on new state

    else:
        st.warning("Please enter a query.")

# Display results
if st.session_state.error_message:
    st.error(st.session_state.error_message)

if st.session_state.text_response:
    st.subheader("Response:")
    st.markdown(st.session_state.text_response)

if st.session_state.audio_response_bytes:
    st.subheader("Voice Response:")
    st.audio(st.session_state.audio_response_bytes, format="audio/mpeg")

if st.session_state.analysis_details:
    st.subheader("Analysis Details:")
    st.json(st.session_state.analysis_details)

st.markdown("---")
st.markdown("Built by Vigneshwaran S")
