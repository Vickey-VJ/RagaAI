import streamlit as st
import requests

st.title("AI Market Brief Generator")

ticker = st.text_input("Enter Stock Ticker", value="TSM")

if st.button("Generate Market Brief"):
    with st.spinner("Generating..."):
        response = requests.get("http://localhost:8005/orchestrate", params={"ticker": ticker})
        if response.status_code == 200:
            st.subheader("Market Brief")
            st.write(response.json()["brief"])
        else:
            st.error("Failed to generate brief.")