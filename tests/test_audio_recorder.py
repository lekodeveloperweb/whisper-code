import time
from unittest.mock import MagicMock, patch

import pytest

AUDIO_SAMPLE_RATE = 16000
AUDIO_CHANNELS = 2


@pytest.fixture
def mock_pyaudio():
    with patch("pyaudio.PyAudio") as mock:
        mock_instance = MagicMock()
        mock_instance.get_sample_size.return_value = 2
        mock.return_value = mock_instance
        yield mock_instance


def test_stop_not_recording_returns_empty(mock_pyaudio):
    from src.core.audio_recorder import AudioRecorder

    recorder = AudioRecorder(sample_rate=16000)
    result = recorder.stop_recording()
    assert result == b""


def test_get_rms_returns_float(mock_pyaudio):
    from src.core.audio_recorder import AudioRecorder

    recorder = AudioRecorder(sample_rate=16000)
    assert isinstance(recorder.get_rms(), (int, float))


def test_stop_closes_stream(mock_pyaudio):
    from src.core.audio_recorder import AudioRecorder

    stream = MagicMock()
    stream.read.return_value = b""
    mock_pyaudio.open.return_value = stream

    recorder = AudioRecorder(sample_rate=16000)
    recorder.start_recording()
    recorder.stop_recording()

    stream.stop_stream.assert_called_once()
    stream.close.assert_called_once()


def test_start_recording_creates_stream(mock_pyaudio):
    from src.core.audio_recorder import AudioRecorder

    stream = MagicMock()
    stream.read.return_value = b""
    mock_pyaudio.open.return_value = stream

    recorder = AudioRecorder(sample_rate=16000)
    recorder.start_recording()

    mock_pyaudio.open.assert_called_once()
    assert recorder.is_recording is True


def test_rms_calculated_from_audio_data(mock_pyaudio):
    import numpy as np

    from src.core.audio_recorder import AudioRecorder

    stream = MagicMock()
    mock_pyaudio.open.return_value = stream

    chunk = 1024
    t = np.linspace(0, 1, chunk)
    audio = (np.sin(2 * np.pi * 440 * t / 16000) * 10000).astype(np.int16)
    audio_bytes = audio.tobytes()

    stream.read.return_value = audio_bytes

    recorder = AudioRecorder(sample_rate=16000)
    recorder.start_recording()

    # Let the background thread read one frame
    import time

    time.sleep(0.05)

    recorder.stop_recording()

    rms = recorder.get_rms()
    assert isinstance(rms, (int, float))


def test_stop_recording_sets_is_recording_false(mock_pyaudio):
    from src.core.audio_recorder import AudioRecorder

    stream = MagicMock()
    stream.read.return_value = b""
    mock_pyaudio.open.return_value = stream

    recorder = AudioRecorder(sample_rate=16000)
    recorder.start_recording()
    assert recorder.is_recording is True

    recorder.stop_recording()
    assert recorder.is_recording is False


def test_stop_recording_returns_valid_wav_bytes(mock_pyaudio):
    from src.core.audio_recorder import AudioRecorder

    stream = MagicMock()
    stream.read.return_value = b"\x00" * 2048  # 1024 samples × 2 bytes/sample
    mock_pyaudio.open.return_value = stream

    recorder = AudioRecorder(sample_rate=16000, channels=1)
    recorder.start_recording()
    time.sleep(0.1)  # let thread collect frames
    recorder.stop_recording()

    wav_bytes = recorder.stop_recording()
    assert wav_bytes == b""  # second stop returns empty (already stopped)

    # First stop should return valid WAV with loud audio data
    recorder2 = AudioRecorder(sample_rate=16000, channels=1)
    stream2 = MagicMock()
    stream2.read.return_value = b"\x00\x7f" * 1024  # loud audio data
    mock_pyaudio.open.return_value = stream2
    recorder2.start_recording()
    time.sleep(0.1)  # let thread collect frames
    wav_bytes2 = recorder2.stop_recording()

    # Verify it's a valid WAV by trying to read it
    import io
    import wave

    buf = io.BytesIO(wav_bytes2)
    with wave.open(buf, "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == AUDIO_CHANNELS
        assert wf.getframerate() == AUDIO_SAMPLE_RATE


def test_start_recording_ignores_double_start(mock_pyaudio):
    from src.core.audio_recorder import AudioRecorder

    stream = MagicMock()
    mock_pyaudio.open.return_value = stream

    recorder = AudioRecorder(sample_rate=16000)
    recorder.start_recording()
    call_count = mock_pyaudio.open.call_count

    recorder.start_recording()
    assert mock_pyaudio.open.call_count == call_count  # no second open


def test_get_rms_initially_zero(mock_pyaudio):
    from src.core.audio_recorder import AudioRecorder

    recorder = AudioRecorder(sample_rate=16000)
    assert recorder.get_rms() == 0.0


def test_start_recording_raises_on_device_error(mock_pyaudio):
    from src.core.audio_recorder import AudioRecorder

    mock_pyaudio.open.side_effect = OSError("device unavailable")

    recorder = AudioRecorder(sample_rate=16000)
    with pytest.raises(OSError, match="device unavailable"):
        recorder.start_recording()


def test_start_recording_sets_is_recording_true(mock_pyaudio):
    from src.core.audio_recorder import AudioRecorder

    stream = MagicMock()
    mock_pyaudio.open.return_value = stream

    recorder = AudioRecorder(sample_rate=16000)
    recorder.start_recording()

    assert recorder.is_recording is True
