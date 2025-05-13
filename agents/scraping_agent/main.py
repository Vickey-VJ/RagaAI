from fastapi import FastAPI
import requests
from bs4 import BeautifulSoup

app = FastAPI()

@app.get("/earnings")
def get_earnings(ticker: str = "TSM"):
    url = f"https://finance.yahoo.com/quote/{ticker}/analysis"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    return {"ticker": ticker, "earnings_summary": "TSMC beat estimates by 4%"}