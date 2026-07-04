import os
from dataclasses import dataclass

from dotenv import load_dotenv


# Load .env from parent directory
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(env_path)

# Calculate project root and data directory paths
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data_dir_path = os.path.join(project_root, "data")


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    groq_api_key: str | None = os.getenv("GROQ_API_KEY")
    data_dir: str = os.getenv("RAG_DATA_DIR", "C:\\Users\\91730\\Downloads\\Rag\\data")
    persist_dir: str = os.getenv("RAG_PERSIST_DIR", os.path.join(project_root, "faiss_store"))
    embedding_model: str = os.getenv("RAG_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    llm_model: str = os.getenv("RAG_LLM_MODEL", "llama-3.3-70b-versatile")
    default_top_k: int = _get_int("RAG_DEFAULT_TOP_K", 5)
    auto_build_index: bool = _get_bool("RAG_AUTO_BUILD_INDEX", True)



settings = Settings()
