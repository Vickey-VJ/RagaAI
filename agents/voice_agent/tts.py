from TTS.api import TTS

tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC")

def synthesize(text, output_path="output.wav"):
    tts.tts_to_file(text=text, file_path=output_path)
    return output_path