import whisper
from gtts import gTTS
import os
import time
import io # Added for in-memory byte stream

# Define a directory for temporary audio files if needed by the agent,
# though the service will primarily manage file paths.
TEMP_AUDIO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_temp_voice_files')
os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)

class VoiceAgent:
    def __init__(self, whisper_model_name="base"):
        print(f"Initializing VoiceAgent with Whisper model: {whisper_model_name}...")
        try:
            self.whisper_model = whisper.load_model(whisper_model_name)
            print(f"Whisper model '{whisper_model_name}' loaded successfully.")
        except Exception as e:
            print(f"Error loading Whisper model '{whisper_model_name}': {e}")
            # Depending on desired behavior, could raise error or set model to None
            self.whisper_model = None 
            # Consider adding a retry mechanism or instructions for manual download if it's a download issue.

    def transcribe_audio(self, audio_file_path: str) -> str | None:
        """
        Transcribes audio from the given file path using Whisper.

        Args:
            audio_file_path (str): The path to the audio file.

        Returns:
            str | None: The transcribed text, or None if an error occurred or model not loaded.
        """
        if not self.whisper_model:
            print("Whisper model not loaded. Cannot transcribe.")
            return None
        
        if not os.path.exists(audio_file_path):
            print(f"Audio file not found at: {audio_file_path}")
            return None

        print(f"Transcribing audio from: {audio_file_path}")
        try:
            result = self.whisper_model.transcribe(audio_file_path)
            transcribed_text = result["text"]
            print(f"Transcription successful. Text: '{transcribed_text[:100]}...'")
            return transcribed_text
        except Exception as e:
            print(f"Error during audio transcription: {e}")
            return None

    def synthesize_speech(self, text: str, lang='en') -> bytes | None:
        """
        Synthesizes speech from the given text using gTTS and returns audio bytes.

        Args:
            text (str): The text to synthesize.
            lang (str): The language for TTS (default is 'en').

        Returns:
            bytes | None: The synthesized MP3 audio data as bytes, or None if an error occurred.
        """
        if not text:
            print("No text provided for speech synthesis.")
            return None
        
        print(f"Synthesizing speech for text: '{text[:100]}...'")
        try:
            tts = gTTS(text=text, lang=lang)
            audio_fp = io.BytesIO()
            tts.write_to_fp(audio_fp)
            audio_fp.seek(0) # Rewind the buffer to the beginning
            audio_bytes = audio_fp.read()
            print(f"Speech synthesized successfully. Returning {len(audio_bytes)} bytes.")
            return audio_bytes
        except Exception as e:
            print(f"Error during speech synthesis: {e}")
            return None

if __name__ == '__main__':
    print("--- Testing VoiceAgent --- ")
    # Create a dummy audio file for testing STT (requires ffmpeg to be installed for whisper to process many formats)
    # For this test, we'll assume a simple .mp3 or .wav might work, but Whisper is robust.
    # Since creating a real audio file here is complex, we'll primarily test TTS
    # and expect STT to be tested with actual audio files when the service is running.

    agent = VoiceAgent(whisper_model_name="tiny") # Using "tiny" for faster test loading

    # Test 1: TTS
    text_to_speak = "Hello, this is a test of the text to speech synthesis system."
    
    print(f"\n--- Test 1: Synthesizing Speech ---")
    audio_data = agent.synthesize_speech(text_to_speak)
    
    if audio_data:
        print(f"TTS Test successful. Received {len(audio_data)} bytes of audio data.")
        # For local testing, save the bytes to a file to verify
        tts_output_filename = f"test_tts_output_agent_{int(time.time())}.mp3"
        tts_output_path = os.path.join(TEMP_AUDIO_DIR, tts_output_filename)
        try:
            with open(tts_output_path, 'wb') as f:
                f.write(audio_data)
            print(f"Test audio saved to: {tts_output_path}")
        except Exception as e:
            print(f"Error saving test audio: {e}")
    else:
        print("TTS Test failed.")

    # Test 2: STT (Placeholder for manual testing with a real audio file)
    # To test STT properly:
    # 1. Place an audio file (e.g., test_audio.mp3) in the TEMP_AUDIO_DIR or provide a full path.
    # 2. Uncomment and run the STT part.
    print(f"\n--- Test 2: Transcribing Speech (Manual Setup Required) ---")
    # Create a dummy file path for demonstration; replace with a real audio file path to test.
    sample_audio_file_for_stt = os.path.join(TEMP_AUDIO_DIR, "your_sample_audio.mp3") 
    
    if os.path.exists(sample_audio_file_for_stt): # Check if user actually placed a file
        print(f"Attempting STT on: {sample_audio_file_for_stt}")
        transcribed_text = agent.transcribe_audio(sample_audio_file_for_stt)
        if transcribed_text:
            print(f"STT Test - Transcribed Text: {transcribed_text}")
        else:
            print("STT Test failed or no text returned.")
    else:
        print(f"STT Test skipped: Place an audio file at '{sample_audio_file_for_stt}' to test transcription.")
        print("Ensure ffmpeg is installed on your system for Whisper to process various audio formats.")
        print("You can install ffmpeg via: sudo apt update && sudo apt install ffmpeg (Linux) or brew install ffmpeg (macOS)")

    # Clean up the generated TTS file if it exists and test was successful
    # if success_tts and os.path.exists(tts_output_path):
    #     try:
    #         # os.remove(tts_output_path)
    #         # print(f"Cleaned up test TTS file: {tts_output_path}")
    #         print(f"Note: Test TTS file '{tts_output_path}' was not automatically deleted for manual verification.")
    #     except Exception as e:
    #         print(f"Error cleaning up test TTS file: {e}")
    print("\n--- VoiceAgent Test Complete ---")
