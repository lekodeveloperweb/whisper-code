# Configuration Guide

Whisper-Code configuration lives in `~/.config/whisper-code/settings.json`.

## settings.json Schema

```json
{
  "stt_api_url": "http://localhost:8080",
  "stt_api_key": null,
  "llm_api_url": null,
  "llm_api_key": null,
  "model_name": "whisper-large-v3",
  "hotkey": "Cmd+Ctrl+T",
  "auto_insert": true,
  "sample_rate": 16000,
  "use_grammar_check": true,
  "grammar_model": "gemma4-e4b-8b"
}
```

| Key                 | Type   | Default                 | Description                                                                                           |
| ------------------- | ------ | ----------------------- | ----------------------------------------------------------------------------------------------------- |
| `stt_api_url`       | string | `http://localhost:8080` | Base URL of your local OpenAI-compatible STT API                                                      |
| `stt_api_key`       | string | `null`                  | Bearer token sent with transcription requests; empty or null sends no Authorization header            |
| `llm_api_url`       | string | `null`                  | Base URL of the chat/completions API for grammar checking; unset or empty falls back to `stt_api_url` |
| `llm_api_key`       | string | `null`                  | Bearer token sent with grammar-check requests; empty or null sends no Authorization header            |
| `model_name`        | string | `whisper-large-v3`      | Model identifier for transcription                                                                    |
| `hotkey`            | string | `Cmd+Ctrl+T`            | Global hotkey to toggle dictation                                                                     |
| `auto_insert`       | bool   | `true`                  | Automatically inject text after transcription                                                         |
| `sample_rate`       | int    | `16000`                 | Audio sample rate in Hz                                                                               |
| `use_grammar_check` | bool   | `true`                  | Enable grammar correction via chat/completions API                                                    |
| `grammar_model`     | string | `gemma4-e4b-8b`         | Model used for grammar checking                                                                       |

## Environment Variable Overrides

Environment variables take precedence over file config. Prefix with `WHISPER_`:

| Env Variable            | Config Key          | Default                                |
| ----------------------- | ------------------- | -------------------------------------- |
| `WHISPER_STT_API_URL`   | `stt_api_url`       | `http://localhost:8080`                |
| `WHISPER_STT_API_KEY`   | `stt_api_key`       | _(none)_                               |
| `WHISPER_LLM_API_URL`   | `llm_api_url`       | _(none — falls back to `stt_api_url`)_ |
| `WHISPER_LLM_API_KEY`   | `llm_api_key`       | _(none)_                               |
| `WHISPER_MODEL_NAME`    | `model_name`        | `whisper-large-v3`                     |
| `WHISPER_HOTKEY`        | `hotkey`            | `Cmd+Ctrl+T`                           |
| `WHISPER_AUTO_INSERT`   | `auto_insert`       | `true`                                 |
| `WHISPER_SAMPLE_RATE`   | `sample_rate`       | `16000`                                |
| `WHISPER_GRAMMAR_CHECK` | `use_grammar_check` | `true`                                 |
| `WHISPER_GRAMMAR_MODEL` | `grammar_model`     | `gemma4-e4b-8b`                        |

Boolean values: `true`/`1` → `True`, `false`/`0` → `False`.

## Config Priority

1. Environment variables (highest)
2. `~/.config/whisper-code/settings.json`
3. Built-in defaults (lowest)

## Runtime Behavior

Config is reloaded on each load call, so you can modify `settings.json` while the app is running and changes take effect immediately.
