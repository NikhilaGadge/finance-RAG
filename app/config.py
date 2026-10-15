"""Central settings for the finance-RAG project."""

from pathlib import Path         # to build file paths
import os                        # to read environment variables

from dotenv import load_dotenv   # reads the .env file

# Project root = the folder above app/ (i.e. ~/finance-rag)
BASE_DIR = Path(__file__).resolve().parent.parent

# Load the variables from finance-rag/.env
load_dotenv(BASE_DIR / ".env")

# --- Secrets (from .env) -------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:                                   # stop early with a clear message
    raise RuntimeError("OPENAI_API_KEY missing - add it to your .env file")

# --- Models --------------------------------------------------------------
EMBEDDING_MODEL = "text-embedding-3-small"   # turns text into vectors
CHAT_MODEL = "gpt-4o-mini"                   # writes the answers (later step)

# --- Storage -------------------------------------------------------------
CHROMA_DIR = str(BASE_DIR / "chroma_db")     # folder where Chroma saves the database