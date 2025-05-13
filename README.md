
# Raga AI - Multi-Agent Finance Assistant

A sophisticated multi-source, multi-agent finance assistant that delivers spoken market briefs via a Streamlit app. This system combines real-time market data, document analysis, and voice interaction to provide comprehensive financial insights.

## Architecture

### Agent Components

- **API Agent**: Real-time market data integration via AlphaVantage/Yahoo Finance
- **Scraping Agent**: Document processing and filing analysis
- **Retriever Agent**: Vector store integration for RAG (FAISS/Pinecone)
- **Analysis Agent**: Quantitative analysis and risk assessment
- **Language Agent**: Natural language synthesis using LLMs
- **Voice Agent**: Speech-to-text and text-to-speech pipelines

### Technical Stack

- **Frontend**: Streamlit
- **Backend**: FastAPI microservices
- **AI/ML**: LangChain, CrewAI, Whisper
- **Data Storage**: FAISS/Pinecone
- **Containerization**: Docker

## Setup Instructions

1. Clone the repository

   ```bash
   git clone https://github.com/Vickey-VJ/RagaAI.git
   cd raga-ai
   ```
2. Create a virtual environment

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies

   ```bash
   pip install -r requirements.txt
   ```
4. Set up API keys

   - Create a `.env` file with:
     ```
     GEMINI_API_KEY=your_gemini_api_key
     ALPHA_VANTAGE_API_KEY=your_alpha_vantage_api_key
     ```
5. Run the Streamlit app

   ```bash
   streamlit run streamlit_app/main.py
   ```

## Contributing

- Fork the repository
- Create a new branch
- Make your changes
- Submit a pull request

## License

[Specify your project's license]

## Setup Instructions

1. Clone the repository:

```bash
git clone https://github.com/yourusername/raga_ai.git
cd raga_ai
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set up environment variables:

```bash
cp .env.example .env
# Edit .env with your API keys
```

4. Run the application:

```bash
streamlit run streamlit_app/main.py
```

## Project Structure

```
aga_ai/
├── data_ingestion/     # Data pipeline components
├── agents/            # Individual agent implementations
├── orchestrator/      # Service orchestration
├── streamlit_app/     # Frontend application
├── tests/            # Test suite
├── docs/             # Documentation
└── docker/           # Docker configuration
```

## Features

- Real-time market data integration
- Document analysis and filing processing
- Voice interaction capabilities
- RAG-based information retrieval
- Quantitative analysis and risk assessment
- Natural language synthesis

## Output

![1747148523798](image/README/1747148523798.png)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- AlphaVantage for market data
- OpenAI for LLM capabilities
- Hugging Face for open-source models
