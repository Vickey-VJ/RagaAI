import os

structure = [
    "agents/api_agent",
    "agents/scraping_agent",
    "agents/retriever_agent",
    "agents/language_agent",
    "agents/voice_agent",
    "data_ingestion",
    "orchestrator",
    "streamlit_app",
    "docs"
]

for path in structure:
    os.makedirs(path, exist_ok=True)