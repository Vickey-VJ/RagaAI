import os
import requests
import json
from dotenv import load_dotenv
from typing import Dict, Any, List

# Add project root to sys.path to allow importing other agents if necessary (though direct import is unlikely here)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# load_dotenv(os.path.join(PROJECT_ROOT, '.env')) # .env loading will be handled by the service

class OrchestratorAgent:
    def __init__(self):
        print("Initializing OrchestratorAgent...")
        self.session = requests.Session()
        
        # Load service URLs from environment variables
        # These should be set in your .env file and loaded by the service running this agent
        self.api_service_url = os.getenv("API_SERVICE_URL", "http://localhost:8000")
        self.scraping_service_url = os.getenv("SCRAPING_SERVICE_URL", "http://localhost:8001")
        self.retriever_service_url = os.getenv("RETRIEVER_SERVICE_URL", "http://localhost:8002")
        self.language_service_url = os.getenv("LANGUAGE_SERVICE_URL", "http://localhost:8003")
        self.analysis_service_url = os.getenv("ANALYSIS_SERVICE_URL", "http://localhost:8004")
        self.voice_service_url = os.getenv("VOICE_SERVICE_URL", "http://localhost:8005")
        
        print(f"Orchestrator configured with service URLs:")
        print(f"  API Service: {self.api_service_url}")
        print(f"  Scraping Service: {self.scraping_service_url}")
        print(f"  Retriever Service: {self.retriever_service_url}")
        print(f"  Language Service: {self.language_service_url}")
        print(f"  Analysis Service: {self.analysis_service_url}")
        print(f"  Voice Service: {self.voice_service_url}")

    def _call_service(self, url: str, method: str = "GET", params: Dict = None, data: Dict = None, json_payload: Dict = None, files: Dict = None, expect_json: bool = True) -> Any:
        try:
            if method.upper() == "POST":
                response = self.session.post(url, params=params, data=data, json=json_payload, files=files, timeout=60)
            else: # Default to GET
                response = self.session.get(url, params=params, timeout=30)
            
            response.raise_for_status() # Raises an HTTPError for bad responses (4XX or 5XX)
            
            if expect_json:
                # Try to parse JSON, but return text if it fails (e.g., for health checks returning plain text)
                try:
                    return response.json()
                except json.JSONDecodeError:
                    # If JSON is expected but decode fails, it might be an issue or just plain text response
                    print(f"Warning: Failed to decode JSON from {url}, returning raw text. Status: {response.status_code}")
                    return response.text
            else:
                # If not expecting JSON (e.g., for audio stream), return raw content
                return response.content
        except requests.exceptions.RequestException as e:
            print(f"Error calling {url}: {e}")
            return {"error": str(e), "status_code": e.response.status_code if e.response else 500}
        except Exception as e:
            print(f"An unexpected error occurred when calling {url}: {e}")
            return {"error": str(e), "status_code": 500}

    def _parse_user_query(self, user_query: str) -> Dict[str, Any]:
        """
        Uses LanguageService to understand the user query, identify entities, intent, etc.
        Placeholder: For now, we'll do very basic keyword spotting.
        A real implementation would call self.language_service_url/language/generate or a new specific endpoint.
        """
        print(f"Orchestrator: Parsing user query: '{user_query}'")
        
        parsed_elements = {
            "tickers": [],
            "keywords": [],
            "intent": "general_financial_query", 
            "target_info": ["risk", "earnings"]
        }
        
        upper_user_query = user_query.upper()

        NON_TICKER_WORDS = {
            "RISK", "ASIA", "TODAY", "WHAT", "OUR", "AND", "ANY", "FOR", "INC", "LLC", 
            "THE", "ARE", "YOU", "FROM", "STOCK", "STOCKS", "MARKET", "NEWS", 
            "EARNINGS", "SURPRISE", "EXPOSURE", "CURRENT", "RECENT", "HIGHLIGHT",
            "COMPANY", "COMPANIES", "TECH", "FINANCE", "INVESTMENT", "PORTFOLIO",
            "DATA", "INFO", "INFORMATION", "PLEASE", "THANKS", "THANK", "HELLO", "GOOD",
            "MORNING", "AFTERNOON", "EVENING", "IS", "AM", "PM", "CALL", "PUT", "OPTION", "OPTIONS",
            "BUY", "SELL", "HOLD", "PRICE", "TARGET", "ANALYSIS", "ANALYST", "REPORT",
            "TODAY", "TOMORROW", "YESTERDAY", "WEEK", "MONTH", "YEAR", "QUARTER", "ANNUAL",
            "HOW", "WHY", "WHEN", "WHERE", "WHICH", "WHO", "WILL", "CAN", "COULD", "SHOULD", "WOULD",
            "ME", "MY", "MINE", "YOUR", "YOURS", "HIM", "HIS", "HER", "HERS", "ITS", "WE", "US",
            "THEM", "THEIR", "THEIRS", "THIS", "THAT", "THESE", "THOSE", "A", "AN", "IN", "ON", "AT",
            "OF", "TO", "WITH", "BY", "AS", "BE", "HAS", "HAVE", "HAD", "DO", "DOES", "DID", "NOT"
            # Add more common words or context-specific non-tickers as needed
        }

        potential_tickers = []
        words = upper_user_query.split()

        for word in words:
            cleaned_word = ''.join(filter(str.isalnum, word))
            
            if cleaned_word.isupper() and 2 <= len(cleaned_word) <= 5 and not cleaned_word.isdigit():
                if cleaned_word not in NON_TICKER_WORDS:
                    potential_tickers.append(cleaned_word)
        
        parsed_elements["tickers"] = sorted(list(set(potential_tickers)))
        
        if "RISK" in upper_user_query:
            parsed_elements["keywords"].append("risk")
        if "EARNINGS" in upper_user_query or "SURPRISE" in upper_user_query:
            parsed_elements["keywords"].append("earnings")
            if "SURPRISE" in upper_user_query:
                 parsed_elements["keywords"].append("surprise")

        if not parsed_elements["tickers"] and "ASIA TECH" in upper_user_query:
            parsed_elements["keywords"].append("asia tech stocks")
        
        print(f"Orchestrator: Parsed query elements: {parsed_elements}")
        return parsed_elements

    async def process_query(self, user_query: str, output_format: str = "text") -> Dict[str, Any]:
        """
        Main orchestration logic.
        1. Parse user query.
        2. Gather data from various services.
        3. Analyze data.
        4. Generate response (text or voice).
        """
        print(f"Orchestrator: Received query: '{user_query}', output_format: {output_format}")
        
        parsed_query = self._parse_user_query(user_query)
        tickers = parsed_query.get("tickers", [])
        keywords_for_retrieval = parsed_query.get("keywords", []) + tickers # Use keywords and tickers for retrieval

        # Step 1: Gather Data
        market_data_results = {}
        news_articles_content = []
        sec_filings_content = []
        retrieved_docs_content = []

        # 1.1 Get stock data for identified tickers
        if not tickers:
            print("Orchestrator: No tickers identified. Skipping stock data fetch.")
        for ticker in tickers:
            if not ticker: 
                print("Orchestrator: Encountered an empty ticker string. Skipping this iteration.")
                continue 

            target_url = f"{self.api_service_url}/{ticker}"  # MODIFIED: Removed /stock/ prefix again
            print(f"Orchestrator: Attempting to fetch stock data for ticker '{ticker}' from URL: {target_url}")
            stock_data = self._call_service(target_url)
            if stock_data and not stock_data.get("error"):
                market_data_results[ticker] = stock_data.get("data", stock_data) # API might return {'data': ...}
            else:
                print(f"Orchestrator: Failed to get stock data for {ticker}: {stock_data.get('error', 'Unknown error') if stock_data else 'No response'}")

        # 1.2 Get SEC filings for identified tickers
        for ticker in tickers:
            print(f"Orchestrator: Fetching SEC filings for {ticker}...")
            filings_response = self._call_service(f"{self.scraping_service_url}/scrape/filings/{ticker}") # Renamed to avoid conflict
            if filings_response and not filings_response.get("error") and isinstance(filings_response.get("filings"), list):
                filings_list = filings_response.get("filings", [])
                for filing_item in filings_list:
                    if isinstance(filing_item, dict):
                        # Construct a descriptive string from metadata
                        desc = filing_item.get("description", "N/A")
                        form = filing_item.get("form_type", "N/A")
                        date = filing_item.get("filing_date", "N/A")
                        url = filing_item.get("document_url", "#")
                        sec_filings_content.append(f"Filing for {ticker} ({form} on {date}): {desc}. URL: {url}")
                print(f"Orchestrator: Processed {len(filings_list)} filing metadata entries for {ticker}.")
            else:
                print(f"Orchestrator: Failed to get SEC filings for {ticker}: {filings_response.get('error', 'Unknown error') if filings_response else 'No response'}")

        # 1.3 Retrieve relevant documents/news from Vector Store using keywords
        if keywords_for_retrieval:
            retrieval_query = " ".join(keywords_for_retrieval)
            print(f"Orchestrator: Searching vector store with query: '{retrieval_query}'")
            retrieved_data = self._call_service(
                f"{self.retriever_service_url}/search", # Corrected URL construction
                method="POST",
                json_payload={"query": retrieval_query, "top_k": 5} # Fetch top 5 relevant docs
            )
            if retrieved_data and not retrieved_data.get("error") and isinstance(retrieved_data.get("results"), list):
                for doc in retrieved_data["results"]:
                    # Assuming doc is like {"text": "content", "metadata": {...}, "score": 0.X}
                    retrieved_docs_content.append(doc.get("text", ""))
                print(f"Orchestrator: Retrieved {len(retrieved_docs_content)} documents from vector store.")
            else:
                print(f"Orchestrator: Failed to retrieve documents or no documents found: {retrieved_data.get('error', 'No results') if retrieved_data else 'No response'}")

        # For now, we'll treat retrieved_docs as general news/context
        # In a more advanced system, we might differentiate sources better
        news_articles_content.extend(retrieved_docs_content)

        # Step 2: Analyze Data
        # Consolidate market info for analysis. For simplicity, if multiple tickers,
        # we might pass them separately or focus on the primary one.
        # Here, we'll pass all gathered text and the first ticker's market info if available.
        analysis_input_market_info = market_data_results.get(tickers[0]) if tickers and market_data_results else None # MODIFIED: ensure market_data_results is not empty
        
        print(f"Orchestrator: Sending data to AnalysisService. News: {len(news_articles_content)}, Filings: {len(sec_filings_content)}")
        analysis_payload = {
            "market_info": analysis_input_market_info,
            "news_articles": news_articles_content,
            "company_filings": sec_filings_content,
            "company_ticker": tickers[0] if tickers else None
        }
        print(f"Orchestrator: Analysis payload: {json.dumps(analysis_payload, indent=2)}") # ADDED: Log the payload
        analysis_result = self._call_service(
            f"{self.analysis_service_url}/analysis/market_data",
            method="POST",
            json_payload=analysis_payload
        )
        if not analysis_result or analysis_result.get("error"):
            print(f"Orchestrator: AnalysisService call failed: {analysis_result.get('error', 'Unknown error') if analysis_result else 'No response'}")
            return {"error": "Failed to get analysis", "details": analysis_result.get('error', 'Unknown error') if analysis_result else 'No response'}

        # Step 3: Generate Final Response using Language Model
        # Use the structured output from AnalysisAgent as context for the LLM.
        # final_context_for_llm = f"User Query: {user_query}\\n\\nAnalysis Results:\\n" # Original context building
        # final_context_for_llm += json.dumps(analysis_result, indent=2) # Original context building

        analysis_result_str = json.dumps(analysis_result, indent=2)

        # This prompt asks the LLM to synthesize a direct answer based on the analysis.
        llm_prompt = (
            f"You are a financial assistant. Your task is to generate a concise and direct natural language answer "
            f"to the user's query based on the provided analysis results.\\n\\n"
            f"User Query: '{user_query}'\\n\\n"
            f"Analysis Results (JSON):\\n"
            f"{analysis_result_str}\\n\\n"
            f"Instructions for response generation:\\n"
            f"- Pay close attention to all sections of the Analysis Results, especially the 'earnings_analysis' section. "
            f"Within 'earnings_analysis', use the 'summary_status', 'confidence', and 'details' fields.\\n"
            f"- When reporting on earnings, your primary source should be the 'summary_status' field from the 'earnings_analysis' section. \\n"
            f"  - If 'summary_status' provides specific details (e.g., 'EPS beat expectations by X%', 'Net income decreased Y%'), then clearly state these details in your response. \\n"
            f"  - If 'summary_status' states something like 'No clear earnings surprise identified' or is generic, you should report this. However, also check the 'details' field within 'earnings_analysis' or other parts of the analysis results for any other relevant earnings context to briefly mention, if it provides additional insight not covered by the generic 'summary_status'.\\n"
            f"  - Always mention the 'confidence' level associated with the earnings analysis if provided in the 'earnings_analysis' section.\\n"
            f"- Also consider 'risk_assessment' and 'market_sentiment' from the Analysis Results for a comprehensive response.\\n"
            f"- Synthesize all this information into a helpful, unified response. Do not just repeat the raw analysis; provide an integrated summary that directly answers the user's likely questions about risk and earnings."
        )

        print("Orchestrator: Generating final response with LanguageService...")
        llm_response_data = self._call_service(
            f"{self.language_service_url}/language/generate", # Using the simpler generate endpoint
            method="POST",
            json_payload={"prompt": llm_prompt}
        )

        final_text_response = ""
        if llm_response_data and not llm_response_data.get("error") and llm_response_data.get("response"):
            final_text_response = llm_response_data["response"]
            print(f"Orchestrator: LLM generated response: {final_text_response[:200]}...")
        else:
            print(f"Orchestrator: LanguageService call failed or no response: {llm_response_data.get('error', 'No content') if llm_response_data else 'No response'}")
            # Fallback: return the structured analysis if LLM fails
            final_text_response = f"Could not generate a natural language summary. Raw analysis: {json.dumps(analysis_result, indent=2)}"

        # Step 4: (Optional) Voice Synthesis
        if output_format == "voice":
            print("Orchestrator: Synthesizing speech with VoiceService...")
            audio_response_content = self._call_service(
                f"{self.voice_service_url}/voice/synthesize/",
                method="POST",
                data={"text": final_text_response}, # gTTS/VoiceService expects form data for text
                expect_json=False # We expect raw bytes (audio stream)
            )
            
            if isinstance(audio_response_content, dict) and audio_response_content.get("error"): # Error from _call_service
                 print(f"Orchestrator: VoiceService call failed: {audio_response_content.get('error', 'Unknown error')}")
                 return {"text_response": final_text_response, "voice_response_bytes": None, "error": "Failed to synthesize voice due to service call error.", "status_code": audio_response_content.get("status_code", 500)}
            elif not isinstance(audio_response_content, bytes): # Unexpected response type
                 print(f"Orchestrator: VoiceService returned unexpected data type: {type(audio_response_content)}. Expected bytes.")
                 return {"text_response": final_text_response, "voice_response_bytes": None, "error": "Voice synthesis failed to return audio data.", "status_code": 500}
            elif len(audio_response_content) == 0: # Empty bytes
                 print(f"Orchestrator: VoiceService returned empty audio data.")
                 return {"text_response": final_text_response, "voice_response_bytes": None, "error": "Voice synthesis returned empty audio.", "status_code": 500}
            print(f"Orchestrator: Voice synthesis successful, received {len(audio_response_content)} bytes.")
            return {"text_response": final_text_response, "voice_response_bytes": audio_response_content, "content_type": "audio/mpeg"}

        return {"text_response": final_text_response, "analysis_details": analysis_result}

if __name__ == '__main__':
    # This basic test won't work without running all dependent services.
    # It's primarily for seeing the agent initialize.
    # For a real test, you'd run this through the OrchestratorService.
    dotenv_path = os.path.join(PROJECT_ROOT, '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
        print(f"Loaded .env from {dotenv_path} for OrchestratorAgent direct test.")
    else:
        print(f".env file not found at {dotenv_path}. Service URLs might use defaults or be missing for direct test.")

    agent = OrchestratorAgent()
    # Example of how you might call it (requires services to be running)
    # import asyncio
    # user_query_example = "What’s our risk exposure in MSFT today, and highlight any earnings surprises?"
    # result = asyncio.run(agent.process_query(user_query_example))
    # print("\\n--- Orchestrator Result ---")
    # if "text_response" in result:
    #     print("Text Response:", result["text_response"])
    # if "voice_response_bytes" in result:
    #     print("Voice response generated (bytes).")
    #     # To save and play:
    #     # with open("orchestrator_test_speech.mp3", "wb") as f:
    #     #     f.write(result["voice_response_bytes"])
    #     # print("Saved to orchestrator_test_speech.mp3")
    # if "error" in result:
    #     print("Error:", result["error"])
    # print("Full analysis details:", result.get("analysis_details", {}))
    print("\\nOrchestratorAgent initialized. Run through OrchestratorService for full functionality.")

