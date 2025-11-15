# tests/conftest.py
import os
import sys
from pathlib import Path

# 1) Гасим автоподхват сторонних плагинов (pytest-twisted и пр.)
os.environ.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")

# 2) Добавляем src в sys.path, чтобы работал импорт "app.…"
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))