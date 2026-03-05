"""
Vercel 서버리스 엔트리포인트 — FastAPI 앱을 import.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "web-admin" / "backend"))

from main import app  # noqa: F401, E402
