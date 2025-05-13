\
import sys
import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import uvicorn
import io

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from agents.orchestrator_agent import OrchestratorAgent
from dotenv import load_dotenv

app = FastAPI(
    title="Orchestrator Service",
    description="Coordinates multiple AI agents to process financial queries.",
    version="1.0.0"
)

orchestrator_agent: OrchestratorAgent = None

class OrchestrationRequest(BaseModel):
    query: str
    output_format: str = "text" # "text" or "voice"

@app.on_event("startup")
async def startup_event():
    global orchestrator_agent
    # Load .env from project root before initializing agent
    # This ensures OrchestratorAgent gets its service URLs
    dotenv_path = os.path.join(PROJECT_ROOT, '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
        print(f"OrchestratorService: Loaded .env file from: {dotenv_path}")
    else:
        print(f"OrchestratorService: Warning: .env file not found at {dotenv_path}. OrchestratorAgent might not have service URLs.")
    
    try:
        orchestrator_agent = OrchestratorAgent()
        print("OrchestratorAgent initialized successfully within OrchestratorService.")
    except Exception as e:
        print(f"Error initializing OrchestratorAgent in service: {e}")
        # Potentially raise an error or prevent startup if critical

@app.post("/orchestrate/query/", 
            summary="Process a financial query through the orchestration pipeline",
            response_description="A text response, or an audio stream if voice output is requested.")
async def handle_orchestration_query(request: OrchestrationRequest):
    if not orchestrator_agent:
        raise HTTPException(status_code=503, detail="OrchestratorAgent not initialized")

    try:
        print(f"OrchestratorService: Received query: '{request.query}', output: '{request.output_format}'")
        result = await orchestrator_agent.process_query(request.query, request.output_format)

        if result.get("error"):
            # Pass through errors from the agent if they occurred
            raise HTTPException(status_code=result.get("status_code", 500), detail=result.get("error"))

        if request.output_format == "voice" and "voice_response_bytes" in result:
            audio_bytes = result["voice_response_bytes"]
            content_type = result.get("content_type", "audio/mpeg")
            if audio_bytes and isinstance(audio_bytes, bytes):
                print(f"OrchestratorService: Streaming voice response ({len(audio_bytes)} bytes).")
                return StreamingResponse(io.BytesIO(audio_bytes), media_type=content_type)
            else:
                # Fallback if voice generation failed but text might be available
                error_detail = "Voice synthesis failed or returned invalid data."
                if result.get("text_response"):
                    error_detail += f" Text response: {result['text_response']}"
                raise HTTPException(status_code=500, detail=error_detail)
        
        # Default to text response
        if "text_response" in result:
            print(f"OrchestratorService: Returning text response.")
            # We can return the text response along with analysis details for client-side use
            return {
                "text_response": result["text_response"],
                "analysis_details": result.get("analysis_details")
            }
        else:
            # Should not happen if agent logic is correct and no error was raised
            raise HTTPException(status_code=500, detail="Orchestration completed but no valid response generated.")
            
    except HTTPException as e:
        # Re-raise HTTPExceptions directly
        raise e
    except Exception as e:
        print(f"OrchestratorService: Unhandled error during orchestration: {e}")
        import traceback
        traceback.print_exc() # For server-side logging of the full error
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@app.get("/orchestrate/health", summary="Health Check")
async def health_check():
    if not orchestrator_agent:
        return {"status": "OrchestratorAgent not initialized"}
    # TODO: Add checks for connectivity to other services if desired
    return {"status": "Orchestrator Service is healthy and OrchestratorAgent is initialized"}

if __name__ == "__main__":
    # .env loading for direct run is handled in startup_event now
    # but for clarity if run directly without uvicorn managing startup:
    dotenv_path = os.path.join(PROJECT_ROOT, '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
        print(f"Loaded .env file from: {dotenv_path} for orchestrator_service.py direct run.")
    else:
        print(f"Warning: .env file not found at {dotenv_path} when running orchestrator_service.py directly.")

    port = int(os.getenv("ORCHESTRATOR_SERVICE_PORT", "8006")) # Default port 8006
    print(f"Attempting to start Orchestrator Service on port {port}")
    # Uvicorn will call the startup event where the agent is initialized
    uvicorn.run(app, host="0.0.0.0", port=port)
    print(f"Orchestrator Service running on http://0.0.0.0:{port}")

