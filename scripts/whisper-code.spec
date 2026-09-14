# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

import os
import re

# Read version from pyproject.toml
def get_version():
    pyproject_path = os.path.join(os.path.dirname(os.path.abspath(SPEC)), '..', 'pyproject.toml')
    with open(pyproject_path, 'r') as f:
        content = f.read()
    match = re.search(r'^version = "(.*)"', content, re.M)
    return match.group(1) if match else '0.1.0'

version = get_version()

a = Analysis(
    ['../src/whisper_code/__main__.py'],
    pathex=[],
    binaries=[
        ('/opt/homebrew/opt/portaudio/lib/libportaudio.2.dylib', '.'),
    ],
    datas=[
        ('../src/gui/icon.png', 'src/gui'),
    ],
    hiddenimports=[
        'PySide6',
        'PySide6.QtWidgets',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'pyaudio',
        'pynput',
        'pyperclip',
        'requests',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'setuptools',
        'pytest',
        'matplotlib',
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
    icon='../src/gui/icon.png',
)

app = BUNDLE(
    exe,
    name='Whisper-Code.app',
    icon='../src/gui/icon.icns',
    bundle_identifier='com.whisper.code',
    entitlements_file=None,
    info_plist={
        'NSPrincipalClass': 'NSApplication',
        'NSAppleScriptEnabled': False,
        'CFBundleShortVersionString': version,
        'CFBundleVersion': version,
        'CFBundleIdentifier': 'com.whisper.code',
        'NSMicrophoneUsageDescription': 'Whisper-Code needs microphone access to transcribe your voice into text.',
    },
)
