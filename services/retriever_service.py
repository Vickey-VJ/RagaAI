from fastapi import FastAPI, HTTPException, Body
import uvicorn
import sys
import os
from typing import List, Dict, Any
from pydantic import BaseModel, Field

# Add the parent directory of 'agents' to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir) # Add parent of services to reach agents

from agents.retriever_agent import RetrieverAgent, MODEL_NAME, FAISS_INDEX_PATH, TEXT_DATA_PATH

# --- Pydantic Models for Request/Response --- 
class AddTextsRequest(BaseModel):
    texts: List[str] = Field(..., description="A list of texts to add to the vector store.", min_items=1)

class SearchQueryRequest(BaseModel):
    query: str = Field(..., description="The search query string.")
    top_k: int = Field(default=5, description="The number of top results to return.", gt=0)

class SearchResultItem(BaseModel):
    text: str
    distance: float
    id: int

class SearchResponse(BaseModel):
    query: str
    results: List[SearchResultItem]

class StatusResponse(BaseModel):
    model_name: str
    index_status: str
    text_count: int
    faiss_index_path: str
    text_data_path: str

# --- FastAPI Application --- 
app = FastAPI(
    title="Retriever Service",
    description="Provides access to a FAISS-based vector store for text retrieval.",
    version="0.1.0"
)

# --- Global Retriever Agent Instance ---
# This instance will be created once when the FastAPI app starts.
# All print statements from RetrieverAgent.__init__ will appear in the service console on startup.
retriever_agent_instance = RetrieverAgent()

# --- API Endpoints --- 
@app.post("/retriever/add", summary="Add texts to the vector store")
async def add_texts_to_store(payload: AddTextsRequest):
    """
    Adds a list of new texts to the FAISS vector store.
    The texts will be embedded and indexed.
    """
    if not payload.texts:
        raise HTTPException(status_code=400, detail="No texts provided to add.")
    try:
        # The add_texts method in RetrieverAgent handles print statements for progress
        retriever_agent_instance.add_texts(payload.texts)
        return {"message": f"Successfully added {len(payload.texts)} text(s) to the vector store."}
    except Exception as e:
        # Log the exception e for debugging on the server side
        print(f"Error in /retriever/add: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred while adding texts: {str(e)}")

@app.post("/retriever/search", response_model=SearchResponse, summary="Search the vector store")
async def search_store(payload: SearchQueryRequest):
    """
    Searches the vector store for texts similar to the provided query.
    """
    if not payload.query:
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")
    try:
        # The search method in RetrieverAgent handles print statements for progress
        search_results = retriever_agent_instance.search(query=payload.query, top_k=payload.top_k)
        return SearchResponse(query=payload.query, results=search_results)
    except Exception as e:
        # Log the exception e for debugging on the server side
        print(f"Error in /retriever/search: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred during search: {str(e)}")

@app.get("/retriever/status", response_model=StatusResponse, summary="Get retriever status")
async def get_retriever_status():
    """
    Returns the current status of the Retriever Agent, including model info and index statistics.
    """
    try:
        status_str = retriever_agent_instance.get_status() # This returns a formatted string
        # We parse it here or ideally, RetrieverAgent.get_status() would return a dict
        lines = status_str.split('\n')
        model_name_line = lines[0].split(': ')[1] if len(lines) > 0 and ': ' in lines[0] else MODEL_NAME
        index_status_line = lines[1] if len(lines) > 1 else "FAISS Index: Unknown"
        text_count_line = lines[2].split(': ')[1].split(' ')[0] if len(lines) > 2 and ': ' in lines[2] else "0"
        
        return StatusResponse(
            model_name=model_name_line,
            index_status=index_status_line,
            text_count=int(text_count_line),
            faiss_index_path=FAISS_INDEX_PATH,
            text_data_path=TEXT_DATA_PATH
        )
    except Exception as e:
        print(f"Error in /retriever/status: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred while fetching status: {str(e)}")

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Retriever Service. See /docs for API details."}

# --- Main Execution Block --- 
if __name__ == "__main__":
    api_host = os.getenv("API_HOST", "0.0.0.0")
    # Using port 8003 for this service
    api_port = int(os.getenv("RETRIEVER_SERVICE_PORT", 8002))

    print(f"Starting Retriever Service on {api_host}:{api_port}")
    # The RetrieverAgent will be initialized here when uvicorn loads the app
    uvicorn.run(app, host=api_host, port=api_port)
