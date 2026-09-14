import os
import sys

# Ensure the project root is on sys.path so absolute imports work
# when bundled by PyInstaller (which strips package context).
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(os.path.dirname(_script_dir))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.whisper_code.cli import main  # noqa: E402

if __name__ == "__main__":
    main()
