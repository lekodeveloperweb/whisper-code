from __future__ import annotations

import contextlib
import io
import logging
import threading
import time
import wave
from typing import Any

import numpy as np
import pyaudio

logger = logging.getLogger("whisper")

SAMPLE_RATE: int = 16000
CHANNELS: int = 1
CHUNK: int = 1024
RMS_SILENCE_THRESHOLD: float = 200.0
MIN_PEAK_RMS: float = 500.0


class AudioRecorder:
    """Capture audio from the default microphone via PyAudio.

    Records to an in-memory buffer (no disk writes). Detects silence
    using RMS threshold and auto-stops after the configured silence
    duration. Tracks peak RMS for HUD visualization.
    """

    def __init__(
        self,
        sample_rate: int = SAMPLE_RATE,
        channels: int = CHANNELS,
        chunk: int = CHUNK,
    ) -> None:
        """Initialize audio recorder with default PyAudio stream settings.

        Args:
            sample_rate: Audio sample rate in Hz (default 16000).
            channels: Number of audio channels (default 1 = mono).
            chunk: Frames per buffer read (default 1024).
        """
        self.sample_rate: int = sample_rate
        self.channels: int = channels
        self.chunk: int = chunk
        self.p: pyaudio.PyAudio = pyaudio.PyAudio()
        self.frames: list[bytes] = []
        self.is_recording: bool = False
        self.stream: Any = None
        self._rms: float = 0.0
        self.thread: threading.Thread | None = None
        self.silence_threshold_ms: int = 800
        self.silence_start: float | None = None
        self.peak_rms: float = 0.0

    def start_recording(self) -> None:
        """Open the audio stream and start the capture thread.

        Raises:
            Exception: If the audio stream cannot be opened.
        """
        if self.is_recording:
            return

        self.frames = []
        self.is_recording = True
        self.silence_start = None
        self.peak_rms = 0.0
        self._rms = 0.0
        try:
            self.stream = self.p.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk,
            )
        except Exception as e:
            self.is_recording = False
            raise e

        self.thread = threading.Thread(target=self._record_loop, daemon=True)
        self.thread.start()

    def _record_loop(self) -> None:
        """Continuously read audio frames and detect silence.

        Computes RMS for each frame, updates peak RMS, and checks
        for silence. Stops recording when silence exceeds the
        configured threshold duration.
        """
        while self.is_recording:
            try:
                data = self.stream.read(self.chunk, exception_on_overflow=False)
                self.frames.append(data)

                audio_data = np.frombuffer(data, dtype=np.int16)
                if len(audio_data) > 0:
                    rms = float(np.sqrt(np.mean(audio_data.astype(np.float64) ** 2)))
                    self._rms = rms
                    self.peak_rms = max(self.peak_rms, rms)
                    if self._is_silent(rms):
                        if self.silence_start is None:
                            self.silence_start = time.monotonic()
                        else:
                            elapsed_ms = (time.monotonic() - self.silence_start) * 1000
                            if elapsed_ms >= self.silence_threshold_ms:
                                self.is_recording = False
                                break
                    else:
                        self.silence_start = None
            except Exception:
                break

    def stop_recording(self) -> bytes:
        """Stop recording and return in-memory WAV bytes.

        Returns empty bytes if no audio data is available or if peak
        RMS is below the minimum threshold (no meaningful audio).
        """
        if self.is_recording:
            self.is_recording = False
            if self.thread:
                self.thread.join(timeout=1.0)
            if self.stream:
                with contextlib.suppress(Exception):
                    self.stream.stop_stream()
                    self.stream.close()

        if not self.frames:
            return b""

        if self.peak_rms < MIN_PEAK_RMS:
            self.frames = []
            return b""

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.p.get_sample_size(pyaudio.paInt16))
            wf.setframerate(self.sample_rate)
            wf.writeframes(b"".join(self.frames))

        self.frames = []
        return buffer.getvalue()

    def get_rms(self) -> float:
        """Return the most recent RMS level for HUD visualization."""
        return self._rms

    def _is_silent(self, rms: float) -> bool:
        """Check if the given RMS level is below the silence threshold."""
        return rms < RMS_SILENCE_THRESHOLD

    def close(self) -> None:
        """Stop recording and clean up PyAudio resources.

        Stops the capture thread, closes the stream, and terminates
        the PyAudio instance. Safe to call multiple times.
        """
        self.is_recording = False
        if self.thread:
            self.thread.join(timeout=1.0)
        if self.stream:
            with contextlib.suppress(Exception):
                self.stream.stop_stream()
                self.stream.close()
        with contextlib.suppress(Exception):
            self.p.terminate()

    def __del__(self) -> None:
        """Terminate the PyAudio instance."""
        self.close()
