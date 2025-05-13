import os
from alpha_vantage.timeseries import TimeSeries
from dotenv import load_dotenv

load_dotenv()

ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

if not ALPHA_VANTAGE_API_KEY:
    raise ValueError("ALPHA_VANTAGE_API_KEY not found in environment variables. Please set it in your .env file.")

def get_daily_stock_data(symbol: str):
    """
    Fetches daily time series data for a given stock symbol from Alpha Vantage.
    """
    ts = TimeSeries(key=ALPHA_VANTAGE_API_KEY, output_format='json')
    try:
        data, meta_data = ts.get_daily(symbol=symbol, outputsize='compact')
        return data, meta_data
    except Exception as e:
        print(f"Error fetching data for {symbol} from Alpha Vantage: {e}")
        return None, None

if __name__ == '__main__':
    # Example usage:
    # Make sure your .env file has ALPHA_VANTAGE_API_KEY set
    sample_symbol = "IBM"
    print(f"Fetching daily data for {sample_symbol}...")
    stock_data, meta_data = get_daily_stock_data(sample_symbol)

    if stock_data:
        print(f"Successfully fetched data for {meta_data['2. Symbol']}")
        # Print the last 5 data points
        count = 0
        for date, daily_data in stock_data.items():
            print(f"{date}: {daily_data}")
            count += 1
            if count >= 5:
                break
    else:
        print(f"Failed to fetch data for {sample_symbol}")

