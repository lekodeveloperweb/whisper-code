import io
import sys
import time
import wave

import pyaudio
import requests

# Config
API_URL = "http://localhost:8080/v1/audio/transcriptions"
MODEL_NAME = "whisper-large-v3"
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK = 1024
RECORD_SECONDS = 5
HTTP_OK = 200


def _check_api_connection() -> None:
    """Verify API server is reachable."""
    print(f"\n[1/3] Checking connection to API: {API_URL}...")
    try:
        response = requests.get("http://localhost:8080", timeout=2)
        print(f"✓ Connected to local API server (Status Code: {response.status_code})")
    except Exception as e:
        print(f"⚠️ Warning: Could not connect to API server at http://localhost:8080: {e}")
        print("We will still attempt the request, but make sure your local server is running.")


def _record_audio(p: pyaudio.PyAudio) -> bytes:
    """Record audio from microphone and return WAV bytes."""
    print("\n[2/3] Preparing microphone (PyAudio)...")
    stream = p.open(
        format=pyaudio.paInt16,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK,
    )
    print(f"🎤 Speak now! Recording {RECORD_SECONDS} seconds...")
    frames = []
    for _i in range(0, int(SAMPLE_RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)
        sys.stdout.write(".")
        sys.stdout.flush()
    print("\nRecording complete. Processing...")
    stream.stop_stream()
    stream.close()
    audio_bytes = b"".join(frames)
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, "wb") as wav_file:
        wav_file.setnchannels(CHANNELS)
        wav_file.setsampwidth(p.get_sample_size(pyaudio.paInt16))
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(audio_bytes)
    return wav_buffer.getvalue()


def main():
    print("==================================================")
    print("   Whisper-Code: OpenAI API Whisper Prototype")
    print("==================================================")

    _check_api_connection()

    p = pyaudio.PyAudio()
    try:
        wav_data = _record_audio(p)
    except Exception as e:
        print(f"❌ Error opening microphone stream: {e}")
        print("Please verify that microphone permission is granted and a mic is available.")
        p.terminate()
        sys.exit(1)
    p.terminate()

    print("\n[3/3] Sending audio to local API for transcription...")
    start_time = time.time()

    files = {"file": ("audio.wav", wav_data, "audio/wav")}
    data = {"model": MODEL_NAME}

    try:
        response = requests.post(API_URL, files=files, data=data, timeout=120)
        inference_duration = time.time() - start_time

        if response.status_code == HTTP_OK:
            result = response.json()
            text = result.get("text", "").strip()

            print("\nResults:")
            print("--------------------------------------------------")
            print(f'🗣️ Transcribed Text:\n"{text}"')
            print("--------------------------------------------------")
            print(f"⏱️ Transcription Latency: {inference_duration:.2f} seconds")
            print(f"🔊 Audio Duration: {RECORD_SECONDS} seconds")
            print(f"⚡ Performance Ratio: {inference_duration / RECORD_SECONDS:.2f}x real-time")
            print("==================================================")
        else:
            print(f"❌ API Error (Status {response.status_code}): {response.text}")

    except Exception as e:
        print(f"❌ Connection/API error during transcription: {e}")


if __name__ == "__main__":
    main()
