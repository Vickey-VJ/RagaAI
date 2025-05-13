from fastapi import FastAPI, HTTPException
import uvicorn
import sys
import os

# Add the parent directory of 'agents' to the Python path
# This allows us to import from the agents module
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
agent_dir = os.path.join(parent_dir, 'agents')
sys.path.append(parent_dir) # Add parent of services to reach agents

from agents.api_agent import get_daily_stock_data, ALPHA_VANTAGE_API_KEY

app = FastAPI(
    title="Market Data API Service",
    description="Provides access to stock market data via Alpha Vantage.",
    version="0.1.0"
    # Ensure no root_path is set here
)

if not ALPHA_VANTAGE_API_KEY:
    print("CRITICAL: ALPHA_VANTAGE_API_KEY not found. The service will not be able to fetch data.")
    # You might want to raise an exception here or handle it more gracefully
    # For now, it will allow the server to start but endpoints will fail.

@app.get("/{symbol}") # MODIFIED: Path changed to /{symbol}
async def read_stock_data(symbol: str):
    """
    Endpoint to get daily stock data for a given symbol.
    """
    print(f"APIService: Received request for symbol: {symbol}") # ADDED_LINE: Log received symbol
    if not ALPHA_VANTAGE_API_KEY:
        raise HTTPException(status_code=500, detail="API key for Alpha Vantage is not configured on the server.")
    
    data, meta_data = get_daily_stock_data(symbol)
    if not data:
        print(f"APIService: No data returned from get_daily_stock_data for symbol: {symbol}") # ADDED_LINE
        raise HTTPException(status_code=404, detail=f"Data not found for symbol {symbol}")
    print(f"APIService: Successfully fetched data for symbol: {symbol}") # ADDED_LINE
    return {"symbol": meta_data['2. Symbol'] if meta_data else symbol, "data": data}

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Market Data API Service. Use /{symbol} to get data."} # MODIFIED: Updated message

if __name__ == "__main__":
    # Get host and port from environment variables or use defaults
    api_host = os.getenv("API_HOST", "0.0.0.0")
    api_port = int(os.getenv("API_PORT", 8000)) # Using 8001 to avoid conflict if main app runs on 8000

    print(f"Starting Market Data API Service on {api_host}:{api_port}")
    uvicorn.run(app, host=api_host, port=api_port)
