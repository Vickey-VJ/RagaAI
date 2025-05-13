import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/orchestrate")
def run_orchestration(ticker: str = "TSM"):
    api_data = requests.get("http://localhost:8001/market_data", params={"ticker": ticker}).json()
    earnings_data = requests.get("http://localhost:8002/earnings", params={"ticker": ticker}).json()
    retriever_data = requests.get("http://localhost:8003/search", params={"query": f"{ticker} earnings"}).json()

    inputs = {
        "market_data": api_data,
        "earnings_data": earnings_data,
        "retriever_context": retriever_data["results"]
    }

    llm_output = requests.post("http://localhost:8004/generate", json=inputs).json()
    return {"brief": llm_output["brief"]}
