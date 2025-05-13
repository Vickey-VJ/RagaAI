from fastapi import FastAPI
import yfinance as yf

app = FastAPI()

@app.get("/market_data")
def get_market_data(ticker: str = "TSM"):
    stock = yf.Ticker(ticker)
    hist = stock.history(period="2d")
    return {
        "ticker": ticker,
        "yesterday_close": hist['Close'].iloc[-2],
        "today_open": hist['Open'].iloc[-1]
    }