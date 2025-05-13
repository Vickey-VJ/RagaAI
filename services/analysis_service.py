from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
import sys
import os
from typing import List, Dict

# Add the parent directory to the Python path to allow importing from 'agents'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.analysis_agent import AnalysisAgent

app = FastAPI(
    title="Analysis Agent Service",
    description="Provides access to data analysis capabilities.",
    version="0.1.0"
)

try:
    analysis_agent_instance = AnalysisAgent()
    print("AnalysisAgent loaded successfully in service.")
except Exception as e:
    print(f"Error loading AnalysisAgent in service: {e}")
    analysis_agent_instance = None # Allow app to start but endpoints will fail

class MarketAnalysisRequest(BaseModel):
    market_info: Dict | None = None # e.g., stock data
    news_articles: List[str] | None = None
    company_filings: List[str] | None = None
    company_ticker: str | None = None # ADDED

class EarningsSurpriseRequest(BaseModel):
    text_snippets: List[str]
    company_ticker: str

@app.on_event("startup")
async def startup_event():
    global analysis_agent_instance
    if analysis_agent_instance is None:
        try:
            analysis_agent_instance = AnalysisAgent()
            print("AnalysisAgent re-initialized successfully during startup.")
        except Exception as e:
            print(f"Failed to initialize AnalysisAgent during startup: {e}")

@app.post("/analysis/market_data", tags=["Analysis"])
async def analyze_market_data_endpoint(request: MarketAnalysisRequest = Body(...)):
    if not analysis_agent_instance:
        raise HTTPException(status_code=503, detail="AnalysisAgent not initialized.")
    try:
        result = analysis_agent_instance.analyze_market_data(
            market_info=request.market_info,
            news_articles=request.news_articles,
            company_filings=request.company_filings,
            company_ticker=request.company_ticker # ADDED
        )
        return result
    except Exception as e:
        print(f"Error in /analysis/market_data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analysis/earnings_surprises", tags=["Analysis"])
async def find_earnings_surprises_endpoint(request: EarningsSurpriseRequest = Body(...)):
    if not analysis_agent_instance:
        raise HTTPException(status_code=503, detail="AnalysisAgent not initialized.")
    try:
        result = analysis_agent_instance.find_earnings_surprises(
            text_snippets=request.text_snippets,
            company_ticker=request.company_ticker
        )
        return result
    except Exception as e:
        print(f"Error in /analysis/earnings_surprises: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analysis/health", tags=["Service Health"])
async def health_check():
    if analysis_agent_instance:
        return {"status": "healthy", "message": "AnalysisAgent is initialized."}
    return {"status": "unhealthy", "message": "AnalysisAgent not initialized."}

if __name__ == "__main__":
    import uvicorn
    # Ensure .env is loaded if AnalysisAgent relies on it, though current placeholder doesn't
    # load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
    print("Starting Analysis Agent Service with Uvicorn on http://localhost:8004")
    uvicorn.run(app, host="0.0.0.0", port=8004) # Using port 8004 for this service
