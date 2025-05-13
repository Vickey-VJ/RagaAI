import requests
from bs4 import BeautifulSoup
import lxml # Ensure lxml is imported if used as a parser
import json
import os # Added for environment variable
from dotenv import load_dotenv # Added for environment variable

# Load environment variables, specifically for SEC_USER_AGENT
# Assuming .env is in the project root, one level up from 'agents'
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOTENV_PATH = os.path.join(PROJECT_ROOT, '.env')
if os.path.exists(DOTENV_PATH):
    load_dotenv(dotenv_path=DOTENV_PATH)

# SEC requires a User-Agent in the format: Sample Company Name AdminContact@example.com
# It's good practice to make this configurable, e.g., via an environment variable
SEC_USER_AGENT = os.getenv("SEC_USER_AGENT", "Financial Assistant Project your_email@example.com")

_cik_lookup = None

def _get_cik_lookup():
    """
    Fetches and caches the ticker to CIK mapping from SEC.
    """
    global _cik_lookup
    if _cik_lookup is None:
        try:
            headers = {"User-Agent": SEC_USER_AGENT}
            response = requests.get("https://www.sec.gov/files/company_tickers.json", headers=headers)
            response.raise_for_status()
            company_data = response.json()
            # The JSON is a dictionary where keys are indices and values are dicts with cik_str, ticker, title
            _cik_lookup = {item['ticker']: str(item['cik_str']).zfill(10) for item in company_data.values() if 'ticker' in item and 'cik_str' in item}
            print(f"Successfully loaded CIK lookup: {len(_cik_lookup)} tickers found.")
        except requests.exceptions.RequestException as e:
            print(f"Error fetching company_tickers.json: {e}")
            _cik_lookup = {} # Avoid retrying on every call if it fails
        except json.JSONDecodeError as e:
            print(f"Error decoding company_tickers.json: {e}")
            _cik_lookup = {}
    return _cik_lookup

def get_cik_by_ticker(ticker: str) -> str | None:
    """
    Retrieves the CIK for a given ticker symbol.
    """
    lookup = _get_cik_lookup()
    return lookup.get(ticker.upper())

def scrape_page_title(url: str):
    """
    Scrapes the title of a given URL.
    """
    try:
        headers = {
            # Using a generic user-agent for non-SEC sites
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
        
        soup = BeautifulSoup(response.content, 'lxml') # Using lxml parser
        
        title_tag = soup.find('title')
        if title_tag and title_tag.string:
            return title_tag.string.strip()
        else:
            return "No title found"
            
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {url}: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while scraping {url}: {e}")
        return None

def get_latest_filings(ticker: str, num_filings: int = 5, filing_types: list[str] | None = None):
    """
    Fetches the latest filings for a given company ticker from the SEC EDGAR API.
    Args:
        ticker: The company ticker symbol (e.g., "AAPL").
        num_filings: The maximum number of recent filings to return.
        filing_types: Optional list of filing types to filter for (e.g., ["10-K", "10-Q"]).
                      If None, returns all types.
    """
    print(f"Fetching latest filings for {ticker} from SEC EDGAR...")
    
    cik = get_cik_by_ticker(ticker)
    if not cik:
        print(f"CIK not found for ticker: {ticker}")
        return {"ticker": ticker.upper(), "cik": None, "filings": [], "error": "CIK not found"}

    headers = {"User-Agent": SEC_USER_AGENT}
    try:
        # Construct the URL for the company's submissions
        # The CIK needs to be padded with leading zeros to 10 digits for this specific API endpoint
        submissions_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        
        print(f"Fetching submissions from: {submissions_url}")
        response = requests.get(submissions_url, headers=headers)
        response.raise_for_status()
        data = response.json()

        filings_data = []
        # The filings are in data['filings']['recent']
        recent_filings = data.get('filings', {}).get('recent', {})
        
        # Extracting and formatting filing information
        # The keys we are interested in are 'accessionNumber', 'filingDate', 'reportDate', 'form', 'primaryDocument', 'primaryDocDescription'
        
        count = 0
        # Iterate through accession numbers, which seem to be the primary way to access individual filing details
        # The API provides 'form' (e.g., "10-K"), 'filingDate', 'reportDate', 'primaryDocument' (e.g., "aapl-20230930.htm")
        
        # The structure of recent_filings is a dictionary where keys are arrays:
        # 'accessionNumber', 'filingDate', 'reportDate', 'form', 'primaryDocument', 'primaryDocDescription', etc.
        # We need to iterate based on the length of these arrays.
        
        num_available_filings = len(recent_filings.get('accessionNumber', []))
        
        for i in range(num_available_filings):
            form_type = recent_filings.get('form', [])[i]
            
            if filing_types and form_type not in filing_types:
                continue

            filing_date = recent_filings.get('filingDate', [])[i]
            report_date = recent_filings.get('reportDate', [])[i] # Date the report is for
            primary_document_name = recent_filings.get('primaryDocument', [])[i]
            accession_number_no_dashes = recent_filings.get('accessionNumber', [])[i].replace('-','')
            
            # Construct the link to the primary document
            # https://www.sec.gov/Archives/edgar/data/{CIK}/{ACCESSION_NUMBER_NO_DASHES}/{PRIMARY_DOCUMENT_NAME}
            filing_link = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_number_no_dashes}/{primary_document_name}"
            
            filings_data.append({
                "form_type": form_type, # Changed from "type" to "form_type" for clarity
                "filing_date": filing_date,
                "report_date": report_date,
                "document_url": filing_link, # Changed from "link" to "document_url"
                "description": recent_filings.get('primaryDocDescription', [])[i]
            })
            count += 1
            if count >= num_filings:
                break
        
        return {
            "ticker": ticker.upper(),
            "cik": cik,
            "filings": filings_data
        }

    except requests.exceptions.RequestException as e:
        print(f"Error fetching SEC data for CIK {cik}: {e}")
        return {"ticker": ticker.upper(), "cik": cik, "filings": [], "error": str(e)}
    except KeyError as e:
        print(f"Could not find expected key in SEC response: {e}. Data structure might have changed.")
        return {"ticker": ticker.upper(), "cik": cik, "filings": [], "error": f"KeyError: {e}"}
    except Exception as e:
        print(f"An unexpected error occurred while fetching filings for {ticker}: {e}")
        return {"ticker": ticker.upper(), "cik": cik, "filings": [], "error": f"Unexpected error: {e}"}


if __name__ == '__main__':
    # Example for scrape_page_title
    example_url = "https://finance.yahoo.com/"
    print(f"Scraping title from {example_url}...")
    title = scrape_page_title(example_url)
    
    if title:
        print(f"Successfully scraped title: {title}\n")
    else:
        print(f"Failed to scrape title from {example_url}\n")

    # Example for get_latest_filings
    sample_ticker_aapl = "AAPL"
    print(f"\nGetting filings for {sample_ticker_aapl}...")
    filings_aapl = get_latest_filings(sample_ticker_aapl, num_filings=3, filing_types=["10-K", "10-Q"])
    if filings_aapl:
        print(json.dumps(filings_aapl, indent=2))
    else:
        print(f"Could not retrieve filings for {sample_ticker_aapl}")

    sample_ticker_msft = "MSFT"
    print(f"\nGetting filings for {sample_ticker_msft}...")
    filings_msft = get_latest_filings(sample_ticker_msft, num_filings=2) # Get any 2 recent
    if filings_msft:
        print(json.dumps(filings_msft, indent=2))
    else:
        print(f"Could not retrieve filings for {sample_ticker_msft}")
        
    sample_ticker_unknown = "NONEXISTENTTICKER"
    print(f"\nGetting filings for {sample_ticker_unknown}...")
    filings_unknown = get_latest_filings(sample_ticker_unknown)
    if filings_unknown:
        print(json.dumps(filings_unknown, indent=2))
    else:
        print(f"Could not retrieve filings for {sample_ticker_unknown}")

    # Test with a ticker that might not have CIK in our initial small map (if it were small)
    # For this test, it should work if company_tickers.json is fetched correctly.
    sample_ticker_goog = "GOOG" 
    print(f"\nGetting filings for {sample_ticker_goog}...")
    filings_goog = get_latest_filings(sample_ticker_goog, num_filings=3)
    if filings_goog:
        print(json.dumps(filings_goog, indent=2))
    else:
        print(f"Could not retrieve filings for {sample_ticker_goog}")
