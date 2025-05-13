import requests
import os
import time
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import sys

# Add project root to sys.path to allow importing .env if script is run from elsewhere
# and to ensure consistent .env loading.
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

# Load .env file from the project root
dotenv_path = os.path.join(project_root, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    print(f"Loaded .env file from: {dotenv_path}")
else:
    print(f"Warning: .env file not found at {dotenv_path}. Service URLs and API keys might be missing.")

# Configuration from environment variables or defaults
SCRAPING_SERVICE_BASE_URL = os.getenv("SCRAPING_SERVICE_URL", "http://localhost:8001")
RETRIEVER_SERVICE_BASE_URL = os.getenv("RETRIEVER_SERVICE_URL", "http://localhost:8002")
SEC_USER_AGENT = os.getenv("SEC_API_USER_AGENT", "Your Name Your.Email@example.com")

if SEC_USER_AGENT == "Your Name Your.Email@example.com":
    print("Warning: SEC_API_USER_AGENT is not set in .env. Using default. Please update it.")

# Target company tickers for data ingestion
# You can expand this list or load it from a configuration file
TARGET_TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"] # Example tickers

def chunk_text(text, chunk_size=1500, overlap=200):
    """
    Splits text into overlapping chunks.
    """
    if not text or not isinstance(text, str):
        return []
    if chunk_size <= overlap:
        # Fallback to non-overlapping if parameters are problematic
        overlap = 0 
        print("Warning: Chunk size must be greater than overlap. Setting overlap to 0.")

    chunks = []
    start = 0
    text_length = len(text)
    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunks.append(text[start:end])
        if end == text_length:
            break
        start += (chunk_size - overlap)
        if start >= text_length: # Should not happen with min() but as a safeguard
            break
    return chunks

def fetch_document_content_from_url(doc_url):
    """
    Fetches and parses content from a given SEC document URL.
    """
    headers = {"User-Agent": SEC_USER_AGENT}
    print(f"Fetching content from: {doc_url} with User-Agent: {SEC_USER_AGENT}")
    try:
        response = requests.get(doc_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        content_type = response.headers.get('content-type', '').lower()
        
        if 'html' in content_type or 'xml' in content_type:
            soup = BeautifulSoup(response.content, 'html.parser')
            # Attempt to remove common non-content tags
            for tag in soup(["script", "style", "header", "footer", "nav", "form"]):
                tag.decompose()
            
            # Try to find main content areas (these are guesses and might need SEC-specific selectors)
            main_content_tags = soup.find_all(['article', 'main', 'div.content', 'body'])
            text = ''
            if main_content_tags:
                for tag in main_content_tags:
                    text += tag.get_text(separator='\n', strip=True) + '\n\n'
            else: # Fallback to all text if specific tags aren't found
                text = soup.get_text(separator='\n', strip=True)

            if not text.strip() and response.text: # If soup failed to get text, use raw text
                 text = response.text # This might be messy for complex HTML

            return text.strip()
        elif 'text/plain' in content_type:
            return response.text.strip()
        else:
            print(f"Warning: Unhandled content type '{content_type}' for URL {doc_url}. Attempting to read as text.")
            return response.text.strip() # Best effort for other text-like types

    except requests.RequestException as e:
        print(f"Error fetching document {doc_url}: {e}")
        return None
    except Exception as e:
        print(f"Error parsing document {doc_url}: {e}")
        return None

def add_texts_to_retriever_service(texts_to_add):
    """
    Sends a list of text chunks to the RetrieverService.
    """
    if not texts_to_add:
        return
    
    # Correctly append only '/add' as RETRIEVER_SERVICE_BASE_URL already contains '/retriever'
    add_url = f"{RETRIEVER_SERVICE_BASE_URL}/add" 
    print(f"Sending {len(texts_to_add)} chunks to RetrieverService at {add_url}...")
    try:
        response = requests.post(add_url, json={"texts": texts_to_add}, timeout=60)
        response.raise_for_status()
        print(f"RetrieverService response: {response.json()}")
    except requests.RequestException as e:
        print(f"Error adding texts to RetrieverService: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while adding texts to retriever: {e}")

def main_ingestion_loop():
    print("--- Starting SEC Filings Ingestion Process ---")
    print(f"Target Tickers: {', '.join(TARGET_TICKERS)}")
    print(f"Scraping Service URL: {SCRAPING_SERVICE_BASE_URL}")
    print(f"Retriever Service URL: {RETRIEVER_SERVICE_BASE_URL}")
    print(f"Using SEC User-Agent: {SEC_USER_AGENT}")

    for ticker in TARGET_TICKERS:
        print(f"\n--- Processing Ticker: {ticker} ---")
        try:
            # 1. Get filing URLs from the ScrapingService
            filings_endpoint_url = f"{SCRAPING_SERVICE_BASE_URL}/scrape/filings/{ticker}"
            print(f"Querying ScrapingService for filings: {filings_endpoint_url}")
            
            scraper_response = requests.get(filings_endpoint_url, headers={"User-Agent": SEC_USER_AGENT}, timeout=60)
            scraper_response.raise_for_status()
            scraper_data = scraper_response.json()

            if not scraper_data or "filings" not in scraper_data or not scraper_data["filings"]:
                print(f"No filings found or unexpected response for {ticker} from ScrapingService.")
                continue

            filings_to_process = scraper_data["filings"]
            print(f"Found {len(filings_to_process)} filing entries for {ticker}.")

            for filing_info in filings_to_process:
                # The scraping_agent.py should provide 'document_url' for the primary filing document.
                # It might also provide 'text_summary_url' for plain text versions if available.
                # Prefer 'text_summary_url' if it exists and points to a .txt file, else use 'document_url'.
                
                doc_url_to_fetch = None
                form_type = filing_info.get("form_type", "N/A")

                if filing_info.get("text_summary_url") and filing_info["text_summary_url"].endswith(".txt"):
                    doc_url_to_fetch = filing_info["text_summary_url"]
                    print(f"Prioritizing text summary URL for {form_type}: {doc_url_to_fetch}")
                elif filing_info.get("document_url"):
                    doc_url_to_fetch = filing_info["document_url"]
                    print(f"Using primary document URL for {form_type}: {doc_url_to_fetch}")
                else:
                    print(f"No suitable document URL found for a filing for {ticker}. Form: {form_type}. Skipping.")
                    continue

                # Ensure the URL is absolute
                if not doc_url_to_fetch.startswith("http"):
                    doc_url_to_fetch = f"https://www.sec.gov{doc_url_to_fetch}"
                
                print(f"Processing {form_type} document: {doc_url_to_fetch}")
                content = fetch_document_content_from_url(doc_url_to_fetch)

                if content and len(content.strip()) > 100: # Basic check for meaningful content
                    print(f"Successfully fetched and parsed content. Length: {len(content)} characters.")
                    
                    # Add metadata to each chunk if desired, e.g., "Source: AAPL 10-K 2023-10-27, URL: ..."
                    # For now, just chunking the raw text.
                    text_chunks = chunk_text(content)
                    print(f"Split content into {len(text_chunks)} chunks.")
                    
                    if text_chunks:
                        add_texts_to_retriever_service(text_chunks)
                    else:
                        print("No chunks generated from content.")
                else:
                    print(f"Failed to fetch, parse, or content too short from {doc_url_to_fetch}")

                time.sleep(2) # Politeness delay between fetching individual documents

        except requests.RequestException as e:
            print(f"Error communicating with ScrapingService for {ticker}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred while processing {ticker}: {e}")
        
        print(f"--- Finished processing for {ticker} ---")
        time.sleep(10) # Politeness delay between processing different tickers

    print("\n--- SEC Filings Ingestion Process Finished ---")

if __name__ == "__main__":
    # Ensure .env is loaded correctly if this script is run directly
    # The load_dotenv call at the top should handle this.
    main_ingestion_loop()
