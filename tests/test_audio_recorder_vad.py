import time
from unittest.mock import MagicMock, Mock, patch

import pytest

MIN_PEAK_RMS: float = 500.0
DEFAULT_SILENCE_THRESHOLD_MS: int = 800


@pytest.fixture
def mock_pyaudio():
    with patch("src.core.audio_recorder.pyaudio.PyAudio") as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        mock_instance.get_sample_size.return_value = 2
        yield mock_instance


@pytest.fixture
def mock_stream(mock_pyaudio):
    stream = MagicMock()
    mock_pyaudio.open.return_value = stream
    return stream


@pytest.fixture
def recorder(mock_pyaudio, mock_stream):
    from src.core.audio_recorder import AudioRecorder

    return AudioRecorder(sample_rate=16000, channels=1)


def test_is_silent_returns_true_for_low_rms(recorder):
    assert recorder._is_silent(100.0) is True
    assert recorder._is_silent(199.0) is True
    assert recorder._is_silent(0.0) is True


def test_is_silent_returns_false_for_high_rms(recorder):
    assert recorder._is_silent(201.0) is False
    assert recorder._is_silent(500.0) is False
    assert recorder._is_silent(10000.0) is False


def test_is_silent_edge_at_200_returns_false(recorder):
    assert recorder._is_silent(200.0) is False


def test_vad_auto_stops_after_silence_threshold(mock_pyaudio, mock_stream):
    from src.core.audio_recorder import AudioRecorder

    call_count = 0

    def mock_read(data, exception_on_overflow=False):
        nonlocal call_count
        call_count += 1
        return b"\x00" * 2048

    mock_stream.read.side_effect = mock_read

    recorder = AudioRecorder(sample_rate=16000, channels=1)
    recorder.silence_threshold_ms = 200

    recorder.start_recording()
    time.sleep(0.5)
    recorder.stop_recording()

    assert not recorder.is_recording


def test_vad_resets_silence_on_speech(mock_pyaudio, mock_stream):
    from src.core.audio_recorder import AudioRecorder

    call_count = 0

    def mock_read(data, exception_on_overflow=False):
        nonlocal call_count
        call_count += 1
        if call_count in {1, 2}:
            return b"\x00" * 2048
        return b"\x00\x7f" * 1024

    mock_stream.read.side_effect = mock_read

    recorder = AudioRecorder(sample_rate=16000, channels=1)
    recorder.silence_threshold_ms = 100

    recorder.start_recording()
    time.sleep(0.3)
    recorder.stop_recording()

    assert not recorder.is_recording


def test_stop_recording_returns_empty_when_no_speech(mock_pyaudio, mock_stream):
    from src.core.audio_recorder import AudioRecorder

    mock_stream.read.return_value = b"\x00" * 2048

    recorder = AudioRecorder(sample_rate=16000, channels=1)
    recorder.start_recording()
    time.sleep(0.1)
    wav_bytes = recorder.stop_recording()

    assert wav_bytes == b""


def test_stop_recording_returns_wav_when_speech_detected(mock_pyaudio, mock_stream):
    from src.core.audio_recorder import AudioRecorder

    call_count = 0

    def mock_read(data, exception_on_overflow=False):
        nonlocal call_count
        call_count += 1
        return b"\x00\x7f" * 1024

    mock_stream.read.side_effect = mock_read

    recorder = AudioRecorder(sample_rate=16000, channels=1)
    recorder.start_recording()
    time.sleep(0.1)
    wav_bytes = recorder.stop_recording()

    assert wav_bytes != b""


def test_peak_rms_tracks_max_rms(mock_pyaudio, mock_stream):
    from src.core.audio_recorder import AudioRecorder

    call_count = 0

    def mock_read(data, exception_on_overflow=False):
        nonlocal call_count
        call_count += 1
        if call_count in {1, 2}:
            return b"\x00" * 2048
        return b"\x00\x7f" * 1024

    mock_stream.read.side_effect = mock_read

    recorder = AudioRecorder(sample_rate=16000, channels=1)
    recorder.start_recording()
    time.sleep(0.1)
    recorder.stop_recording()

    assert recorder.peak_rms > MIN_PEAK_RMS


def test_silence_threshold_default_value(mock_pyaudio, mock_stream):
    from src.core.audio_recorder import AudioRecorder

    recorder = AudioRecorder(sample_rate=16000, channels=1)
    assert recorder.silence_threshold_ms == DEFAULT_SILENCE_THRESHOLD_MS


def test_vad_with_custom_threshold(mock_pyaudio, mock_stream):
    from src.core.audio_recorder import AudioRecorder

    mock_stream.read.return_value = b"\x00" * 2048

    recorder = AudioRecorder(sample_rate=16000, channels=1)
    recorder.silence_threshold_ms = 300

    recorder.start_recording()
    time.sleep(0.1)
    recorder.stop_recording()

    assert not recorder.is_recording


def test_stop_recording_preserves_frames_with_speech(mock_pyaudio, mock_stream):
    from src.core.audio_recorder import AudioRecorder

    call_count = 0

    def mock_read(data, exception_on_overflow=False):
        nonlocal call_count
        call_count += 1
        return b"\x00\x7f" * 1024

    mock_stream.read.side_effect = mock_read

    recorder = AudioRecorder(sample_rate=16000, channels=1)
    recorder.start_recording()
    time.sleep(0.1)
    wav_bytes = recorder.stop_recording()

    assert wav_bytes != b""
    assert len(recorder.frames) == 0


def test_start_recording_resets_peak_rms(mock_pyaudio, mock_stream):
    from src.core.audio_recorder import AudioRecorder

    mock_stream.read.return_value = b"\x00\x7f" * 1024
    recorder = AudioRecorder(sample_rate=16000, channels=1)

    # First run sets peak_rms
    recorder.start_recording()
    time.sleep(0.1)
    recorder.stop_recording()
    assert recorder.peak_rms > MIN_PEAK_RMS

    # Second run should reset it
    mock_stream.read.return_value = b"\x00" * 2048
    recorder.start_recording()
    assert recorder.peak_rms == 0.0
    recorder.stop_recording()


def test_start_recording_resets_silence_start(mock_pyaudio, mock_stream):
    from src.core.audio_recorder import AudioRecorder

    mock_stream.read.return_value = b"\x00" * 2048
    recorder = AudioRecorder(sample_rate=16000, channels=1)
    recorder.silence_threshold_ms = 100

    # First run triggers VAD, setting silence_start
    recorder.start_recording()
    time.sleep(0.2)
    assert not recorder.is_recording
    assert recorder.silence_start is not None

    # Second run should reset silence_start
    recorder.start_recording()
    # Verify it doesn't immediately stop (which it would if silence_start was still old)
    time.sleep(0.05)
    assert recorder.is_recording, "Should still be recording (silence_start was reset)"
    recorder.stop_recording()
