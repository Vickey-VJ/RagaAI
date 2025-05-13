# filepath: /Users/kartik/Desktop/Raga_Assignemnt/services/language_service.py
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
import sys
import os

# Add the parent directory to the Python path to allow importing from 'agents'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.language_agent import LanguageAgent

app = FastAPI(
    title="Language Agent Service",
    description="Provides access to a language model for text generation and RAG.",
    version="0.1.0"
)

try:
    language_agent_instance = LanguageAgent()
    print("LanguageAgent loaded successfully in service.")
except Exception as e:
    print(f"Error loading LanguageAgent in service: {e}")
    # Depending on the desired behavior, you might want to prevent the app from starting
    # or have the endpoints return an error if the agent isn't loaded.
    language_agent_instance = None

class GenerationRequest(BaseModel):
    prompt: str
    system_prompt: str | None = None

# Updated RAGRequest model
class RAGRequest(BaseModel):
    prompt: str
    use_rag: bool = True  # Default to True
    top_k_retrieval: int = 3 # Default top_k
    system_prompt: str | None = None

@app.on_event("startup")
async def startup_event():
    global language_agent_instance
    if language_agent_instance is None:
        try:
            language_agent_instance = LanguageAgent()
            print("LanguageAgent re-initialized successfully during startup.")
        except Exception as e:
            print(f"Failed to initialize LanguageAgent during startup: {e}")
            # This will make endpoints fail if the agent is critical
            # Consider a more robust way to handle this, e.g., a health check endpoint

@app.post("/language/generate", tags=["Language Model"])
async def generate_text(request: GenerationRequest = Body(...)):
    """
    Generates text using the language model based on a given prompt.
    """
    if not language_agent_instance:
        raise HTTPException(status_code=503, detail="LanguageAgent not initialized. Please check service logs.")
    try:
        response = language_agent_instance.generate_response(
            prompt=request.prompt,
            system_prompt=request.system_prompt
        )
        return {"response": response}
    except Exception as e:
        print(f"Error in /language/generate: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/language/generate_with_context", tags=["Language Model"])
async def generate_text_with_context(request: RAGRequest = Body(...)):
    """
    Generates text using the language model. If use_rag is True (default),
    it first fetches context internally and incorporates it into the prompt.
    """
    if not language_agent_instance:
        raise HTTPException(status_code=503, detail="LanguageAgent not initialized. Please check service logs.")
    try:
        # Call the updated generate_rag_response method
        response = language_agent_instance.generate_rag_response(
            prompt=request.prompt,
            use_rag=request.use_rag,
            top_k_retrieval=request.top_k_retrieval,
            system_prompt=request.system_prompt
        )
        return {"response": response}
    except Exception as e:
        print(f"Error in /language/generate_with_context: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/language/health", tags=["Service Health"])
async def health_check():
    """
    Checks the health of the Language Agent Service.
    """
    if language_agent_instance and hasattr(language_agent_instance, 'llm'):
        # Basic check: is the agent instance and its llm attribute initialized?
        # More sophisticated checks could involve a dummy call to the LLM.
        return {"status": "healthy", "message": "LanguageAgent is initialized."}
    return {"status": "unhealthy", "message": "LanguageAgent not initialized or LLM not available."}

if __name__ == "__main__":
    import uvicorn
    print("Starting Language Agent Service with Uvicorn on http://localhost:8003")
    # Note: When running directly, ensure the .env file is accessible from this script's location
    # or that environment variables are already set.
    # The LanguageAgent itself loads dotenv, which should work if .env is in the project root.
    uvicorn.run(app, host="0.0.0.0", port=8003)
