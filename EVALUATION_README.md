# LangSmith Evaluation Suite for RAG Product

This suite provides comprehensive evaluation tools for your RAG (Retrieval-Augmented Generation) product using LangSmith.

## Files Overview

### 1. **`langsmith_evaluation.py`** - Comprehensive Evaluation Script
- Full-featured evaluation system with multiple metrics
- Includes RAG system integration
- Advanced evaluators for correctness, relevance, groundedness, and retrieval relevance
- Detailed reporting and analysis

### 2. **`simple_evaluation.py`** - Quick Evaluation Script
- Simple evaluation with minimal dependencies
- Basic correctness and relevance scoring
- Quick setup and execution
- Good for initial testing

### 3. **`setup_evaluation.py`** - Setup and Configuration
- Automated dependency installation
- Environment configuration
- API key setup
- README generation

### 4. **`evaluation_example.py`** - Integration Example
- Shows how to integrate evaluation into your RAG product
- Batch evaluation capabilities
- Report generation
- Error handling

## Quick Start

### Step 1: Setup Environment
```bash
python setup_evaluation.py
```

### Step 2: Configure API Keys
Edit the `.env` file:
```bash
LANGSMITH_API_KEY=your_actual_langsmith_api_key
GROQ_API_KEY=your_actual_groq_api_key
```

### Step 3: Run Evaluation
```bash
# Simple evaluation
python simple_evaluation.py

# Comprehensive evaluation  
python langsmith_evaluation.py

# Example integration
python evaluation_example.py
```

## Configuration Requirements

### Required API Keys
1. **LangSmith API Key**: Available from [LangSmith Dashboard](https://smith.langchain.com/)
2. **Groq API Key**: Available from [Groq Console](https://console.groq.com/)

### Environment Variables
```bash
# Required
LANGSMITH_API_KEY=your_api_key
GROQ_API_KEY=your_api_key
LANGSMITH_TRACING=true

# Optional
LANGSMITH_PROJECT=your-project-name
MODEL_NAME=groq:openai/gpt-oss-120b
```

## Evaluation Metrics

### 1. Correctness
- Evaluates factual accuracy of responses
- Compares against expected/ground truth answers
- Score: Boolean (True/False)

### 2. Relevance
- Measures how well the response addresses the question
- Ensures conciseness and helpfulness
- Score: Boolean (True/False)

### 3. Groundedness
- Checks if responses are based on retrieved documents
- Detects hallucinations
- Score: Boolean (True/False)

### 4. Retrieval Relevance
- Evaluates if retrieved documents are relevant to the question
- Ensures quality of information retrieval
- Score: Boolean (True/False)

## Usage Examples

### Basic Usage
```python
from langsmith_evaluation import LangSmithRAGEvaluator

# Initialize evaluator
evaluator = LangSmithRAGEvaluator()

# Create dataset
examples = [
    {
        "inputs": {"question": "What is LangChain?"},
        "outputs": {"answer": "A framework for building LLM applications"}
    }
]
evaluator.create_rag_dataset("My Dataset", examples)

# Run evaluation
results = evaluator.run_evaluation("My Dataset", "experiment-name")
```

### Advanced Integration
```python
from evaluation_example import RAGEvaluationIntegration

# Initialize integration
integration = RAGEvaluationIntegration()

# Run batch evaluation
test_cases = [
    {
        "inputs": {"question": "What is RAG?"},
        "outputs": {"answer": "Retrieval-Augmented Generation"}
    }
]
results = integration.batch_evaluate(test_cases, "My Dataset")

# Generate report
integration.generate_report(results)
```

## Project Structure

```
Rag/
├── langsmith_evaluation.py     # Comprehensive evaluation
├── simple_evaluation.py        # Simple evaluation
├── setup_evaluation.py        # Setup script
├── evaluation_example.py      # Integration example
├── EVALUATION_README.md       # This file
├── .env                       # Environment configuration
└── README_EVALUATION.md       # Detailed usage instructions
```

## Troubleshooting

### Common Issues

1. **API Key Errors**
   - Ensure `.env` file exists and contains valid keys
   - Check environment variables are properly set
   - Verify API keys have correct permissions

2. **Import Errors**
   - Run `python setup_evaluation.py` to install dependencies
   - Check Python version (requires 3.8+)
   - Verify virtual environment is activated

3. **Evaluation Failures**
   - Check internet connectivity for document loading
   - Verify LangSmith project access
   - Ensure sufficient quota/balance for API calls

4. **Performance Issues**
   - Reduce document chunk size for faster processing
   - Use smaller models for evaluation
   - Implement caching for repeated queries

### Debug Mode
Enable detailed logging by setting environment variables:
```bash
export LANGSMITH_TRACING=true
export LOG_LEVEL=DEBUG
```

## Integration Guide

### Adding Your Own RAG System
1. Replace the `rag_bot` method in `langsmith_evaluation.py`
2. Ensure the method returns the same format: `{"answer": str, "documents": list}`
3. Update your document loading and retrieval logic

### Custom Evaluators
Add your own evaluators by extending the `BaseEvaluator` class:
```python
class CustomEvaluator(BaseEvaluator):
    def evaluate(self, query: str, response: str, context: List[str], 
                expected_answer: Optional[str] = None) -> EvaluationMetrics:
        # Your custom evaluation logic
        pass
```

### Dataset Management
- Use LangSmith UI to manage datasets
- Export/import datasets for reproducibility
- Version control your test cases

## Best Practices

1. **Start Simple**: Use `simple_evaluation.py` for initial testing
2. **Gradual Complexity**: Move to comprehensive evaluation as needed
3. **Regular Testing**: Run evaluation after significant changes
4. **Monitor Performance**: Track metrics over time
5. **Iterative Improvement**: Use evaluation results to improve your RAG system

## Support

- LangSmith Documentation: https://docs.smith.langchain.com/
- LangSmith Community: https://discord.gg/6AdMQxvpQG
- GitHub Issues: Report issues in the project repository

## Next Steps

1. Run `python setup_evaluation.py` to configure your environment
2. Test with `python simple_evaluation.py`
3. Integrate evaluation into your development workflow
4. Monitor results and iterate on improvements