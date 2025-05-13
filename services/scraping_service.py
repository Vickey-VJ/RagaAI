from fastapi import FastAPI, HTTPException, Query
import uvicorn
import sys
import os
from typing import Optional

# Add the parent directory of 'agents' to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir) # Add parent of services to reach agents

from agents.scraping_agent import scrape_page_title, get_latest_filings

app = FastAPI(
    title="Scraping Service",
    description="Provides web scraping functionalities like fetching page titles and company filings (mock data for now).",
    version="0.1.0"
)

@app.get("/scrape/title")
async def read_scrape_title(url: str = Query(..., description="The URL to scrape the title from")):
    """
    Endpoint to scrape the title of a given URL.
    Example: `?url=https://finance.yahoo.com`
    """
    if not url:
        raise HTTPException(status_code=400, detail="URL parameter is required.")
    
    title = scrape_page_title(url)
    if title is None:
        raise HTTPException(status_code=500, detail=f"Failed to scrape title from {url}. Check service logs for details.")
    if title == "No title found":
        raise HTTPException(status_code=404, detail=f"No title found at {url}")
    return {"url": url, "title": title}

@app.get("/scrape/filings/{ticker}")
async def read_scrape_filings(ticker: str):
    """
    Endpoint to get the latest filings for a given company ticker.
    Currently returns mock data.
    """
    filings_data = get_latest_filings(ticker)
    if not filings_data:
        # This case might not be hit with current mock data but good for future
        raise HTTPException(status_code=404, detail=f"Filings not found for ticker {ticker}")
    return filings_data

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Scraping Service. Use /scrape/title?url=... or /scrape/filings/{ticker}"}

if __name__ == "__main__":
    api_host = os.getenv("API_HOST", "0.0.0.0")
    # Using port 8002 for this service to avoid conflict
    api_port = int(os.getenv("SCRAPING_SERVICE_PORT", 8001)) 

    print(f"Starting Scraping Service on {api_host}:{api_port}")
    uvicorn.run(app, host=api_host, port=api_port)
