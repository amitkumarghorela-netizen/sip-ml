"""HuggingFace Spaces entry point for FastAPI backend."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from api.main import app  # noqa: F401 — uvicorn loads this
