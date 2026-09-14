# Packaging Guide

Build and distribute Whisper-Code as a standalone macOS application.

---

## Prerequisites

```bash
pip install pyinstaller
```

---

## Build a Standalone App

### 1. Create the PyInstaller Spec File

Create `whisper-code.spec`:

```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets/icons/*.png', 'assets/icons'),
        ('assets/sounds/*.wav', 'assets/sounds'),
    ],
    hiddenimports=[
        'mlx',
        'mlx.nn',
        'mlx.utils',
        'pyaudio',
        'pynput',
        'pyperclip',
        'PyQt5',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'setuptools',
        'pytest',
    ],
    win_no_prefer_redirect=False,
    exclude_modules=[],
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='Whisper-Code',
    debug=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,
    icon='assets/icons/icon.icns',
)
```

### 2. Build the App

```bash
pyinstaller whisper-code.spec
```

This produces `dist/Whisper-Code/` with the bundled application.

### 3. Create a .dmg Installer

```bash
# Create a disk image
hdiutil create -volname "Whisper-Code" -fs APFS -imagesize 2048M -format UDZO Whisper-Code.dmg -srcfolder dist/Whisper-Code

# Optionally add a .app alias for convenience
ln -s /Applications dist/Whisper-Code/Applications
```

---

## Alternative: pip Package

### 1. Create pyproject.toml

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "whisper-code"
version = "1.0.0"
description = "Voice dictation for macOS using Whisper + MLX"
requires-python = ">=3.10"
license = {text = "MIT"}
dependencies = [
    "PyQt5>=5.15.0",
    "PyAudio>=0.2.13",
    "mlx>=0.0.14",
    "pynput>=1.7.6",
    "pyperclip>=1.8.0",
]

[project.scripts]
whisper = "main:main"

[tool.setuptools.packages.find]
where = ["."]
include = ["src*"]
```

### 2. Build the Package

```bash
pip install build
python -m build
```

Produces `dist/whisper_code-1.0.0-py3-none-any.whl`.

### 3. Install the Package

```bash
pip install dist/whisper_code-1.0.0-py3-none-any.whl
```

---

## Code Signing (Optional but Recommended)

```bash
# Sign the app
codesign --deep --sign "Developer ID Application: Your Name (TEAM ID)" --force dist/Whisper-Code

# Notarize with Apple
xcrun notary submit dist/Whisper-Code.dmg --wait --provider "TEAM ID" --apple-id "your@email.com" --password "@env:NOTARIZE_PASSWORD"

# Staple the notarization ticket
xcrun stapler staple dist/Whisper-Code.dmg
```

---

## Distribution Checklist

- [ ] App builds without errors
- [ ] App launches and runs on target macOS version
- [ ] Microphone permission works
- [ ] Accessibility permission works
- [ ] Hotkey activates from any app
- [ ] Text injects into active text field
- [ ] Error toasts display correctly
- [ ] Model downloads on first run
- [ ] App is code-signed (optional)
- [ ] DMG is notarized (optional)
