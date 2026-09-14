from __future__ import annotations

import platform
import subprocess


def _is_macos() -> bool:
    return platform.system() == "Darwin"


class ToastNotifier:
    def error(self, message: str) -> None:
        """Show a native macOS error toast (red, persistent)."""
        if not _is_macos():
            return
        cmd: str = (
            f'osascript -e \'display notification "{message}" '
            f'with title "Whisper-Code Error" '
            f'with name "whisper.error" '
            f'with color "FF0000"\''
        )
        subprocess.run(cmd, shell=True, capture_output=True, check=False)

    def info(self, message: str) -> None:
        """Show a native macOS info toast (white, auto-dismiss)."""
        if not _is_macos():
            return
        cmd: str = (
            f'osascript -e \'display notification "{message}" '
            f'with title "Whisper-Code" '
            f'with name "whisper.info" '
            f'with color "FFFFFF"\''
        )
        subprocess.run(cmd, shell=True, capture_output=True, check=False)

    def notify(self, message: str, app_name: str = "Whisper-Code", subtitle: str = "") -> None:
        """Full control notification via osascript."""
        if not _is_macos():
            return
        parts: list[str] = [f'display notification "{message}"']
        parts.append(f'with title "{app_name}"')
        if subtitle:
            parts.append(f'with name "{subtitle}"')
        cmd: str = "osascript -e '" + "' + '".join(parts) + "'"
        subprocess.run(cmd, shell=True, capture_output=True, check=False)
