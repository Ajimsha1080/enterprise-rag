"""
LangSmith configuration and utilities for RAG tracing
"""

import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class LangSmithConfig:
    """LangSmith configuration settings"""
    
    # LangSmith API settings
    api_url: str = "https://api.smith.langchain.com"
    api_key: Optional[str] = None
    project_name: str = "rag-system"
    
    # Tracing settings
    trace_enabled: bool = True
    trace_queries: bool = True
    trace_evaluations: bool = True
    
    # Evaluation settings
    evaluation_dataset: str = "rag-evaluations"
    evaluation_model: str = "groq/llama-3.3-70b-versatile"
    
    # Performance settings
    max_concurrent_traces: int = 10
    trace_sampling_rate: float = 1.0  # 100% sampling
    
    # Metadata
    environment: str = "development"
    version: str = "1.0.0"
    
    def __post_init__(self):
        """Initialize configuration from environment variables"""
        # Ensure environment variables are loaded
        import dotenv
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
        dotenv.load_dotenv(env_path)
        
        self.api_key = os.getenv("LANGSMITH_API_KEY", self.api_key)
        self.project_name = os.getenv("LANGSMITH_PROJECT", self.project_name)
        self.trace_enabled = os.getenv("LANGSMITH_TRACE_ENABLED", "true").lower() == "true"
        
        # Set environment-specific settings
        if self.environment == "production":
            self.trace_sampling_rate = 0.1  # 10% sampling in production
            self.max_concurrent_traces = 5

def get_langsmith_config() -> LangSmithConfig:
    """Get LangSmith configuration"""
    return LangSmithConfig()

def create_trace_metadata(query: str, top_k: int = 5, model: str = "default") -> Dict[str, Any]:
    """Create standard trace metadata for RAG operations"""
    return {
        "operation": "rag-query",
        "query_length": len(query),
        "top_k": top_k,
        "model": model,
        "timestamp": __import__('datetime').datetime.now().isoformat(),
        "environment": os.getenv("ENVIRONMENT", "development")
    }

def create_evaluation_metrics(evaluation: Dict[str, Any], query: str, answer: str) -> Dict[str, Any]:
    """Create standardized evaluation metrics for LangSmith"""
    return {
        "query": query,
        "answer": answer,
        "metrics": evaluation,
        "timestamp": __import__('datetime').datetime.now().isoformat(),
        "evaluation_type": "comprehensive_rag"
    }