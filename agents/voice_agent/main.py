from fastapi import FastAPI, UploadFile, Form
from stt import transcribe
from tts import synthesize

app = FastAPI()

@app.post("/stt")
def handle_stt(file: UploadFile):
    path = f"temp.wav"
    with open(path, "wb") as f:
        f.write(file.file.read())
    text = transcribe(path)
    return {"text": text}

@app.post("/tts")
def handle_tts(text: str = Form(...)):
    output_path = synthesize(text)
    return {"audio_path": output_path}
