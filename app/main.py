"""
Main module alias to support:
    uvicorn app.main:app --reload
"""
import sys
import os

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

try:
    from ..main import app
except (ImportError, ValueError):
    from main import app

__all__ = ["app"]
