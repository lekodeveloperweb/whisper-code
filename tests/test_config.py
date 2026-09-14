from unittest.mock import patch

from src.utils.config_manager import ConfigManager

SAMPLE_RATE = 16000
SAMPLE_RATE_ALT = 8000


def test_config_defaults():
    cm = ConfigManager()
    assert cm.get("api_url") == "http://localhost:8080"
    assert cm.get("model_name") == "whisper-large-v3"
    assert cm.get("hotkey") == "Cmd+Ctrl+T"
    assert cm.get("auto_insert") is True
    assert cm.get("sample_rate") == SAMPLE_RATE
    assert cm.get("use_grammar_check") is True
    assert cm.get("grammar_model") == "gemma4-e4b-8b"


def test_config_save_load(tmp_path):
    cm = ConfigManager()
    test_file = tmp_path / "settings.json"
    cm.config_file = test_file
    cm.config_dir = tmp_path

    cm.save_config({"model_name": "mlx-community/parakeet-tdt-0.6b-v3"})

    cm2 = ConfigManager()
    cm2.config_file = test_file
    cm2.config = cm2.load_config()

    assert cm2.get("model_name") == "mlx-community/parakeet-tdt-0.6b-v3"
    assert cm2.get("api_url") == "http://localhost:8080"


def test_config_grammar_defaults():
    cm = ConfigManager()
    assert cm.get("use_grammar_check") is True
    assert cm.get("grammar_model") == "gemma4-e4b-8b"


def test_env_var_override_api_url():
    with patch.dict("os.environ", {"WHISPER_API_URL": "http://stt.example.com:9000"}):
        cm = ConfigManager()
        assert cm.get("api_url") == "http://stt.example.com:9000"


def test_env_var_override_model_name():
    with patch.dict(
        "os.environ", {"WHISPER_MODEL_NAME": "mlx-community/parakeet-tdt-0.6b-v3-turbo"}
    ):
        cm = ConfigManager()
        assert cm.get("model_name") == "mlx-community/parakeet-tdt-0.6b-v3-turbo"


def test_env_var_override_int():
    with patch.dict("os.environ", {"WHISPER_SAMPLE_RATE": "8000"}):
        cm = ConfigManager()
        assert cm.get("sample_rate") == SAMPLE_RATE_ALT
        assert isinstance(cm.get("sample_rate"), int)


def test_env_var_override_bool_true():
    with patch.dict("os.environ", {"WHISPER_GRAMMAR_CHECK": "true"}):
        cm = ConfigManager()
        assert cm.get("use_grammar_check") is True


def test_env_var_override_bool_false():
    with patch.dict("os.environ", {"WHISPER_GRAMMAR_CHECK": "false"}):
        cm = ConfigManager()
        assert cm.get("use_grammar_check") is False


def test_env_var_override_file_config(tmp_path):
    with patch.dict("os.environ", {"WHISPER_API_URL": "http://env-override.com"}):
        cm = ConfigManager()
        test_file = tmp_path / "settings.json"
        cm.config_file = test_file
        cm.config_dir = tmp_path
        cm.save_config({"api_url": "http://file-config.com"})
        # Env var should take precedence over file
        cm2 = ConfigManager()
        cm2.config_file = test_file
        cm2.config = cm2.load_config()
        assert cm2.get("api_url") == "http://env-override.com"


def test_config_load_config_file_not_readable(tmp_path):
    import os

    cm = ConfigManager()
    test_file = tmp_path / "settings.json"
    cm.config_file = test_file
    cm.config_dir = tmp_path

    cm.save_config({"api_url": "http://test.com"})

    os.chmod(test_file, 0o000)

    cm2 = ConfigManager()
    cm2.config_file = test_file
    cm2.config_dir = tmp_path

    try:
        loaded = cm2.load_config()
        assert loaded is not None
    finally:
        os.chmod(test_file, 0o644)
