"""
Central configuration for the RAG application.
All tunable values live here so experimenting is easy —
no hardcoded numbers should exist elsewhere; everything should
be imported from this file.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ---------- Paths ----------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
VECTORSTORE_DIR = os.path.join(BASE_DIR, "vectorstore")
DATABASE_DIR = os.path.join(BASE_DIR, "database")

# ---------- File handling ----------
ALLOWED_EXTENSIONS = {"pdf"}
MAX_FILE_SIZE_MB = 25

# ---------- Chunking ----------
# Character-based chunking (not token-based, because it's easier to debug)
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150

# ---------- Embeddings ----------
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"  # Sentence Transformers, local, free

# ---------- Retrieval ----------
TOP_K = 6  # how many relevant chunks to pass to the LLM as context

# ---------- LLM ----------
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_MODEL_NAME = "openai/gpt-oss-20b"  # Groq's fast free-tier model
LLM_TEMPERATURE = 0.2  # lower temperature = more factual, less creative

# ---------------- Flask ----------------
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "True") == "True"
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-this-in-production")

# ---------- Logging ----------
LOG_LEVEL = "INFO"