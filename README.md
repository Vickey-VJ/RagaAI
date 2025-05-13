# Multi-Agent Finance Assistant

This project is a multi-source, multi-agent finance assistant that delivers spoken market briefs via a Streamlit app.

## Architecture

The application uses a microservices architecture with the following components:

- Orchestrator Service: Coordinates all other services
- API Service: Handles external API calls
- Scraping Service: Retrieves web data
- Retriever Service: Manages document retrieval from the vector store
- Language Service: Provides NLP capabilities
- Analysis Service: Analyzes financial data
- Voice Service: Converts text to speech

## Setup & Deployment

### Local Deployment

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the main application:
   ```
   python app/main.py
   ```
4. Open the Streamlit app in your browser at http://localhost:8501

### Streamlit Cloud Deployment

The application is configured to run on Streamlit Cloud with limited functionality. To deploy:

1. Fork this repository to your GitHub account
2. Log in to [Streamlit Cloud](https://streamlit.io/cloud)
3. Create a new app, selecting your repository and using `streamlit_app.py` as the main file
4. Deploy the app

Note: The Streamlit Cloud deployment provides a demo version with simulated responses as the backend services cannot run in the Streamlit Cloud environment.
