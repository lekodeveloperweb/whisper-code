# 🎙️ Whisper-Code

**Whisper-powered, hands-free voice dictation for macOS.**

A lightweight background utility that converts your spoken words into text and seamlessly inserts them into your active application — no keyboard required.

## Key Features

- 🚀 **Focus-Stable HUD**: "Ghost HUD" keeps your cursor in place
- 🎤 **Local API**: Works with oMLX and any OpenAI-compatible server
- 📋 **Smart Injection**: Pastes text directly at your cursor position
- 💎 **Glassmorphic Design**: Modern translucent visual feedback
- ⚙️ **Settings Dialog**: Configure from the tray menu
- ⚡ **Native Performance**: Optimized for Apple Silicon via MLX

## Quick Install

```bash
pip install whisper-code
```

Or with uv:

```bash
uv sync && uv run whisper
```

## Quick Start

1. Press **`Cmd + Ctrl + T`** to start dictating
2. Speak into your microphone
3. Press **ENTER** to send
4. Text appears at your cursor

## Links

- 📖 [Documentation](https://github.com/lekodeveloperweb/whisper-code/blob/main/docs/index.md)
- 🐛 [Issues](https://github.com/lekodeveloperweb/whisper-code/issues)
- 📄 [License](LICENSE)

---

## Privacy

- **100% Local**: No audio data ever leaves your machine
- **In-Memory**: Audio chunks are processed and discarded; nothing saved to disk

## License

MIT License. Created by LekoDeveloperWeb.
