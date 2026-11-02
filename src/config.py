"""Centralized environment configuration."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(ROOT / "data" / "enterprise.db")))
if not DATABASE_PATH.is_absolute():
    DATABASE_PATH = ROOT / DATABASE_PATH
LLM_MODE = os.getenv("LLM_MODE", "mock").strip().lower()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
MAX_RESULT_ROWS = max(1, min(int(os.getenv("MAX_RESULT_ROWS", "500")), 5000))
MAX_CORRECTION_ATTEMPTS = max(1, min(int(os.getenv("MAX_CORRECTION_ATTEMPTS", "3")), 3))
