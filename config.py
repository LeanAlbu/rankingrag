import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Directories
DOCS_DIRS = ["./docs"]
CACHE_DIR = "./cache_md"
FAISS_DB_PATH = "./faiss_index"

# Models
# Multilingual embedding model suitable for Portuguese
EMBEDDING_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
# Cross-encoder model optimized for Portuguese
RERANK_MODEL_NAME = "nreimers/mmarco-mMiniLMv2-L6-H384-v1"
# LLM Model (OpenRouter model)
LLM_MODEL = os.getenv("LLM_MODEL", "google/gemini-2.5-flash")

# OpenRouter Settings
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
