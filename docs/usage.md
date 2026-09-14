# Usage Guide

Learn how to use Whisper-Code effectively.

## Hotkeys

| Hotkey | Action |
|--------|--------|
| `Cmd + Ctrl + T` | Toggle listening mode on/off |
| `Enter` | Stop recording and send transcription |

## The HUD

When you press `Cmd+Ctrl+T`, a "Ghost HUD" appears at the bottom of your screen:

- **Listening...**: Shows when recording is active
- **Processing...**: Shows while audio is being transcribed
- **Sent**: Shows briefly after successful injection

The HUD uses a "Ghost" strategy — it's a Qt.ToolTip with 0.0 opacity that toggles to 1.0 to bypass macOS focus-switching. Your cursor never leaves your editor.

## Text Injection

Whisper-Code injects text using two methods:

1. **Primary**: macOS Accessibility API — pastes directly at your cursor position
2. **Fallback**: Clipboard backup + simulated `Cmd+V` — used when accessibility permission is denied

The original clipboard content is preserved and restored after injection.

## Workflow

1. Press `Cmd+Ctrl+T` to start recording
2. Speak naturally — the HUD shows "Listening..."
3. Press `Enter` to stop and send
4. The HUD shows "Processing..." while transcribing
5. Text appears at your cursor — HUD shows "Sent"

## Grammar Checking

If `use_grammar_check` is enabled (default), transcribed text is sent to a chat/completions endpoint for cleanup before injection. This can improve readability but adds latency.

Disable in settings:

```json
{
    "use_grammar_check": false
}
```

## Troubleshooting

| Issue | Solution |
|-------| :--- |
| Hotkey not working | Verify Accessibility permissions for your terminal |
| No text injected | Ensure the target app is focused before/during dictation |
| HUD not appearing | Check that PySide6 is properly installed |
| API errors | Verify your oMLX server is running at the configured URL |
