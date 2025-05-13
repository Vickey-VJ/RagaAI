import sys
import os
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import StreamingResponse
import io
import uvicorn
import time # Added import time

# Add project root to sys.path to allow importing 'agents'
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from agents.voice_agent import VoiceAgent

app = FastAPI(
    title="Voice Service",
    description="Provides text-to-speech and speech-to-text functionalities.",
    version="1.0.0"
)

voice_agent = None

@app.on_event("startup")
async def startup_event():
    global voice_agent
    try:
        voice_agent = VoiceAgent()
        print("VoiceAgent initialized successfully.")
    except Exception as e:
        print(f"Error initializing VoiceAgent: {e}")
        # Depending on the severity, you might want to prevent startup
        # For now, we'll let it start and endpoints will fail if voice_agent is None

@app.post("/voice/transcribe/", summary="Transcribe Audio to Text")
async def transcribe_audio(audio_file: UploadFile = File(...)):
    """
    Receives an audio file and returns the transcribed text.
    """
    if not voice_agent:
        raise HTTPException(status_code=503, detail="VoiceAgent not initialized")
    if not audio_file:
        raise HTTPException(status_code=400, detail="No audio file provided.")

    try:
        audio_bytes = await audio_file.read()
        # Whisper might need a file path. Create a temporary file.
        # Ensure the temporary file has an extension if Whisper relies on it, though it's often robust.
        temp_audio_filename = f"temp_upload_{int(time.time())}_{audio_file.filename}"
        temp_audio_path = os.path.join(PROJECT_ROOT, temp_audio_filename) # Save in project root or a dedicated temp dir
        
        with open(temp_audio_path, "wb") as f:
            f.write(audio_bytes)
        
        # Corrected argument name here
        transcription = voice_agent.transcribe_audio(audio_file_path=temp_audio_path) 
        
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path) # Clean up temporary file
        
        if transcription is not None: # Check for None, as empty string can be a valid transcription
            return {"transcription": transcription}
        else:
            # More specific error if transcription is None vs. an exception occurring
            detail_msg = "Failed to transcribe audio. The model may have returned no text or an error occurred."
            if not voice_agent.whisper_model: # Check if model failed to load initially
                 detail_msg = "Whisper model not loaded in VoiceAgent. Transcription unavailable."
            raise HTTPException(status_code=500, detail=detail_msg)
    except Exception as e:
        # Log the exception e
        if os.path.exists("temp_audio_file"):
            os.remove("temp_audio_file")
        raise HTTPException(status_code=500, detail=f"Error during transcription: {str(e)}")

@app.post("/voice/synthesize/", summary="Synthesize Text to Speech")
async def synthesize_speech(text: str = Form(...)):
    """
    Receives text and returns synthesized speech as an audio stream (MP3).
    """
    if not voice_agent:
        raise HTTPException(status_code=503, detail="VoiceAgent not initialized")
    if not text:
        raise HTTPException(status_code=400, detail="No text provided for synthesis.")

    try:
        audio_bytes = voice_agent.synthesize_speech(text)
        if audio_bytes:
            return StreamingResponse(io.BytesIO(audio_bytes), media_type="audio/mpeg")
        else:
            raise HTTPException(status_code=500, detail="Failed to synthesize speech.")
    except Exception as e:
        # Log the exception e
        raise HTTPException(status_code=500, detail=f"Error during speech synthesis: {str(e)}")

@app.get("/voice/health", summary="Health Check")
async def health_check():
    """
    Simple health check endpoint.
    """
    if not voice_agent:
        return {"status": "VoiceAgent not initialized"}
    return {"status": "Voice Service is healthy and VoiceAgent is initialized"}

if __name__ == "__main__":
    # Load .env file from the project root for consistency if this service is run directly
    from dotenv import load_dotenv
    DOTENV_PATH = os.path.join(PROJECT_ROOT, '.env')
    if os.path.exists(DOTENV_PATH):
        load_dotenv(dotenv_path=DOTENV_PATH)
        print(f"Loaded .env file from: {DOTENV_PATH} for voice_service.py")
    else:
        print(f"Warning: .env file not found at {DOTENV_PATH} when running voice_service.py directly.")

    port = int(os.getenv("VOICE_SERVICE_PORT", "8005"))
    print(f"Attempting to start Voice Service on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
    print(f"Voice Service running on http://0.0.0.0:{port}")
