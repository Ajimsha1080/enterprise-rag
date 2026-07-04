"""
LangSmith integration module for RAG system
Provides comprehensive tracing and evaluation capabilities
"""

import logging
from typing import Optional, Dict, Any
from langsmith_client import get_langsmith_client
from enhanced_evaluation import EvaluationMetrics, send_enhanced_langsmith_evaluation

logger = logging.getLogger(__name__)

class LangSmithManager:
    """LangSmith manager for RAG operations"""
    
    def __init__(self, config=None):
        self._config = config or {}
        self._client = get_langsmith_client()
        self._config = self._client.config
    
    def create_dataset(self, name: str, description: str = "") -> str:
        """Create a dataset in LangSmith"""
        return self._client.create_dataset(name, description)
    
    def add_evaluation_to_dataset(self, dataset_id: str, evaluation: Dict[str, Any], query: str, answer: str):
        """Add evaluation to dataset"""
        inputs = {"query": query, "answer": answer}
        outputs = {"evaluation": evaluation}
        self._client.add_example_to_dataset(dataset_id, inputs, outputs)
        return True
    
    def create_run(self, name: str, inputs: Dict[str, Any], outputs: Dict[str, Any], 
                   project_name: str) -> str:
        """Create a run - placeholder implementation"""
        logger.info(f"Creating run: {name} in project {project_name}")
        return f"run-{name}-{id(self)}"
    
    def update_run(self, run_id: str, outputs: Dict[str, Any]):
        """Update a run - placeholder implementation"""
        logger.info(f"Updating run {run_id}")
        return True
    
    def is_connected(self) -> bool:
        """Check if LangSmith client is connected"""
        return self._client.is_connected()
    
    def get_client(self):
        """Get the underlying LangSmith client"""
        return self._client

# Global instances
langsmith_manager = LangSmithManager()

def send_langsmith_evaluation(run_id: Optional[str], evaluation: Dict[str, Any], 
                            guardrails: Dict[str, Any], message: str) -> Dict[str, Any]:
    """Send evaluation to LangSmith"""
    logger.info(f"Sending LangSmith evaluation (run_id: {run_id}): {message}")
    
    # Use enhanced evaluation if available
    if isinstance(evaluation, EvaluationMetrics):
        result = send_enhanced_langsmith_evaluation(run_id, evaluation, guardrails, message)
    else:
        # Fallback for simple evaluations
        result = {
            "status": "success",
            "run_id": run_id,
            "evaluation": evaluation,
            "guardrails": guardrails,
            "message": message,
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }
    
    # Log to LangSmith if available
    if langsmith_manager.is_connected():
        try:
            if isinstance(evaluation, EvaluationMetrics):
                langsmith_manager._client.log_evaluation(
                    evaluation.query, 
                    "",  # Answer would be available in real implementation
                    evaluation, 
                    guardrails
                )
        except Exception as e:
            logger.error(f"Failed to log evaluation to LangSmith: {e}")
    
    return result

def initialize_langsmith() -> bool:
    """Initialize LangSmith integration"""
    logger.info("Initializing LangSmith integration")
    return langsmith_manager.is_connected()