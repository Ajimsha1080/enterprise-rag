"""
LangSmith client wrapper for RAG tracing and evaluation
"""

import os
import logging
import traceback
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
from datetime import datetime
import json

try:
    from langsmith import Client
    from langsmith.run_helpers import trace
    from langsmith.evaluation import evaluate
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    Client = None
    trace = None
    evaluate = None

from langsmith_config import get_langsmith_config, create_trace_metadata, create_evaluation_metrics
from enhanced_evaluation import EvaluationMetrics, send_enhanced_langsmith_evaluation

logger = logging.getLogger(__name__)

class LangSmithClient:
    """LangSmith client wrapper for RAG operations"""
    
    def __init__(self, config=None):
        self.config = config or get_langsmith_config()
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize LangSmith client if available and configured"""
        if not LANGSMITH_AVAILABLE:
            logger.warning("LangSmith not available - using placeholder mode")
            return
            
        # Re-read config to ensure environment variables are loaded
        self.config = get_langsmith_config()
        
        if not self.config.api_key:
            logger.warning("LangSmith API key not configured - using placeholder mode")
            logger.info(f"Available env vars: LANGSMITH_API_KEY={os.getenv('LANGSMITH_API_KEY')}")
            return
            
        try:
            self.client = Client(
                api_url=self.config.api_url,
                api_key=self.config.api_key
            )
            logger.info("LangSmith client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize LangSmith client: {e}")
            self.client = None
    
    @contextmanager
    def trace_rag_operation(self, query: str, top_k: int = 5, model: str = "default"):
        """Context manager for tracing RAG operations"""
        if not self.client or not self.config.trace_enabled:
            # Create dummy context for compatibility
            yield DummyTraceContext()
            return
            
        # Create trace metadata
        metadata = create_trace_metadata(query, top_k, model)
        
        try:
            with trace(
                self.client,
                inputs={"query": query, "top_k": top_k, "model": model},
                outputs={},
                project_name=self.config.project_name,
                run_type="chain"
            ) as run:
                yield LangSmithTraceContext(run, self)
        except Exception as e:
            logger.error(f"Failed to create LangSmith trace: {e}")
            yield DummyTraceContext()
    
    def log_evaluation(self, query: str, answer: str, evaluation: EvaluationMetrics, 
                      guardrails: Dict[str, Any] = None):
        """Log evaluation results to LangSmith"""
        if not self.client or not self.config.trace_evaluations:
            logger.info("Evaluation logging skipped - LangSmith not available or disabled")
            return
            
        try:
            # Create evaluation record
            eval_data = create_evaluation_metrics(evaluation.to_dict(), query, answer)
            
            # Send to LangSmith using the correct method
            self.client.create_run(
                name="evaluation",
                inputs={"query": query, "answer": answer},
                outputs=eval_data,
                project_name=self.config.project_name,
                run_type="chain"
            )
            
            logger.info(f"Evaluation logged to LangSmith for query: {query[:50]}...")
            
        except Exception as e:
            logger.error(f"Failed to log evaluation to LangSmith: {e}")
    
    def create_dataset(self, name: str, description: str = "") -> str:
        """Create dataset in LangSmith"""
        if not self.client:
            return "placeholder-dataset-id"
            
        try:
            dataset = self.client.create_dataset(
                name=name,
                description=description or f"RAG evaluation dataset - {datetime.now().isoformat()}"
            )
            return dataset.id
        except Exception as e:
            logger.error(f"Failed to create dataset: {e}")
            return "placeholder-dataset-id"
    
    def add_example_to_dataset(self, dataset_id: str, inputs: Dict[str, Any], 
                              outputs: Dict[str, Any]):
        """Add example to dataset"""
        if not self.client:
            return
            
        try:
            self.client.create_example(
                inputs=inputs,
                outputs=outputs,
                dataset_id=dataset_id
            )
        except Exception as e:
            logger.error(f"Failed to add example to dataset: {e}")
    
    def is_connected(self) -> bool:
        """Check if LangSmith client is connected"""
        try:
            return self.client is not None and self.config.trace_enabled and hasattr(self.client, 'create_run')
        except:
            return False

class LangSmithTraceContext:
    """Context manager for LangSmith traces"""
    
    def __init__(self, run, client):
        self.run = run
        self.client = client
        self.start_time = datetime.now()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Log completion time
        if self.run:
            duration = (datetime.now() - self.start_time).total_seconds()
            self.run.outputs = {
                **getattr(self.run, 'outputs', {}),
                "duration_seconds": duration,
                "status": "completed" if not exc_type else "error"
            }

class DummyTraceContext:
    """Dummy trace context for compatibility when LangSmith is unavailable"""
    
    def __init__(self):
        self.run = None
        self.start_time = datetime.now()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

# Global client instance
langsmith_client = LangSmithClient()

def get_langsmith_client() -> LangSmithClient:
    """Get global LangSmith client instance"""
    return langsmith_client