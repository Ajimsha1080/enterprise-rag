# RAG System with LangSmith Integration

A sophisticated Retrieval-Augmented Generation (RAG) system with comprehensive LangSmith tracing, evaluation metrics, and advanced document processing capabilities.

## Features

### 🚀 Core Functionality
- **Document Processing**: Supports multiple file formats (PDF, text files)
- **Vector Store**: FAISS-based vector database for efficient similarity search
- **Semantic Search**: Advanced embeddings using Sentence Transformers
- **LLM Integration**: Groq API integration with powerful LLM models
- **Multi-format Support**: Process PDFs, text files, and uploaded documents

### 📊 LangSmith Integration
- **Comprehensive Tracing**: End-to-end tracing for RAG operations
- **Evaluation Metrics**: Advanced evaluation with multiple quality dimensions
- **Performance Monitoring**: Response time, token usage, and quality metrics
- **Guardrails**: Content safety and PII detection
- **Dataset Management**: Automatic dataset creation and example logging

### 🎯 Evaluation System
- **Retrieval Relevance**: Measures how well retrieved documents match the query
- **Answer Quality**: Assesses the overall quality of generated responses
- **Correctness**: Factual accuracy verification
- **Relevance**: Query-response relevance scoring
- **Groundedness**: Response groundedness in source documents
- **Coherence**: Response coherence and logical flow
- **Clarity**: Response clarity and readability
- **Completeness**: Response completeness and coverage

## Architecture

```
RAG System/
├── src/
│   ├── api.py              # FastAPI application endpoints
│   ├── search.py           # Core RAG search functionality
│   ├── vectorstore.py      # FAISS vector store implementation
│   ├── embedding.py        # Embedding pipeline and processing
│   ├── data_loader.py      # Document loading and preprocessing
│   ├── config.py           # Configuration management
│   ├── langsmith_client.py # LangSmith integration
│   ├── enhanced_evaluation.py # Advanced evaluation system
│   ├── guardrails.py       # Content safety and guardrails
│   ├── human_in_loop.py    # Human-in-the-loop capabilities
│   └── middleware.py       # API middleware and request handling
├── data/
│   ├── pdf/                # PDF documents
│   ├── text_files/         # Text documents
│   ├── uploads/            # Uploaded files
│   └── vector_store/       # FAISS vector storage
├── docs/                   # Documentation
├── examples/               # Example files
└── tests/                  # Test files
```

## Installation

### Prerequisites
- Python 3.8+
- Valid Groq API key
- LangSmith API key (for tracing)

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Rag
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   # Create .env file in the project root
   GROQ_API_KEY=your_groq_api_key_here
   LANGSMITH_API_KEY=your_langsmith_api_key_here
   RAG_DATA_DIR=C:\Users\91730\Downloads\Rag\data
   RAG_PERSIST_DIR=C:\Users\91730\Downloads\Rag\faiss_store
   ```

4. **Download models** (optional - models will be downloaded automatically)
   ```bash
   # The system will automatically download required models on first run
   ```

## Deployment

### Azure Deployment

Deploy to Azure Container Apps (recommended) or App Service:

```bash
# Deploy to Azure Container Apps
cd deploy/azure
./deploy.ps1 -ResourceGroupName "rag-api-rg" -Location "East US" -DeploymentType "container-apps" -GroqApiKey "your-groq-key" -LangSmithApiKey "your-langsmith-key"

# Deploy to Azure App Service
./deploy.ps1 -ResourceGroupName "rag-api-rg" -Location "West US" -DeploymentType "app-service" -AppServiceName "rag-api-app" -GroqApiKey "your-groq-key" -LangSmithApiKey "your-langsmith-key" -Sku "B2"
```

### Kubernetes Deployment

Deploy to Kubernetes using Helm charts:

```bash
# Deploy to Kubernetes
cd deploy/kubernetes
./deploy-kubernetes.sh -d -GROQ_API_KEY="your-groq-key" -LANGSMITH_API_KEY="your-langsmith-key"

# Or using PowerShell
.\deploy-kubernetes.ps1 -Action deploy -GroqApiKey "your-groq-key" -LangSmithApiKey "your-langsmith-key"
```

### Docker Deployment

Run locally with Docker:

```bash
# Build and run container
docker build -t rag-api:latest .
docker run -p 8001:8000 -v $(pwd)/data:/app/data -v $(pwd)/faiss_store:/app/faiss_store --env-file .env rag-api:latest
```

### Deployment Options

| Platform | Best For | Features |
|----------|----------|----------|
| **Azure Container Apps** | Production, scaling | Serverless, auto-scaling, built-in monitoring |
| **Azure App Service** | Small deployments | Fixed resources, easy management |
| **Kubernetes** | Enterprise | Advanced orchestration, full control |
| **Docker** | Development, testing | Local testing, quick deployment |

## Usage

### Starting the Server

```bash
# Start the RAG API server
python src/api.py

# Server will be available at:
# API Documentation: http://127.0.0.1:8001/docs
# Health Check: http://127.0.0.1:8001/health
```

### API Endpoints

#### 1. Health Check
```bash
GET http://127.0.0.1:8001/health
```

#### 2. Query Endpoint
```bash
POST http://127.0.0.1:8001/query
Content-Type: application/json

{
  "query": "What is machine learning?",
  "top_k": 5,
  "temperature": 0.7,
  "max_tokens": 1000
}
```

### Example Usage

```python
import requests

# Basic query
response = requests.post(
    "http://127.0.0.1:8001/query",
    json={"query": "What is Python programming language?"}
)
print(response.json())

# Query with custom parameters
response = requests.post(
    "http://127.0.0.1:8001/query",
    json={
        "query": "Explain the basics of neural networks",
        "top_k": 3,
        "temperature": 0.5,
        "max_tokens": 1500
    }
)
```

## Configuration

### Environment Variables

| Variable | Description | Default Value |
|----------|-------------|---------------|
| `GROQ_API_KEY` | Groq API key for LLM access | Required |
| `LANGSMITH_API_KEY` | LangSmith API key for tracing | Required |
| `RAG_DATA_DIR` | Directory containing source documents | `./data` |
| `RAG_PERSIST_DIR` | Directory for FAISS vector store | `./faiss_store` |
| `RAG_EMBEDDING_MODEL` | Embedding model name | `all-MiniLM-L6-v2` |
| `RAG_LLM_MODEL` | LLM model name | `llama-3.3-70b-versatile` |
| `RAG_DEFAULT_TOP_K` | Default number of results | `5` |
| `RAG_AUTO_BUILD_INDEX` | Auto-build vector index | `true` |

## LangSmith Integration

### Dashboard Features

The LangSmith dashboard provides comprehensive monitoring and evaluation:

1. **Trace Visualization**: End-to-end traces of RAG operations
2. **Performance Metrics**: Response times, token usage, throughput
3. **Quality Scores**: Evaluation metrics for response quality
4. **Error Tracking**: Debug information and error logs
5. **Dataset Management**: Query-example pairs for evaluation

### Custom Traces

Custom traces are automatically generated for:
- Document retrieval operations
- LLM inference calls
- Evaluation scoring
- Vector search operations
- Guardrail checks

## Evaluation Metrics

### Quality Dimensions

| Metric | Description | Range |
|--------|-------------|-------|
| **Retrieval Relevance** | How well retrieved documents match the query | 0.0 - 1.0 |
| **Answer Quality** | Overall response quality | 0.0 - 1.0 |
| **Correctness** | Factual accuracy | 0.0 - 1.0 |
| **Relevance** | Query-response relevance | 0.0 - 1.0 |
| **Groundedness** | Response groundedness in sources | 0.0 - 1.0 |
| **Coherence** | Response logical flow | 0.0 - 1.0 |
| **Clarity** | Response readability | 0.0 - 1.0 |
| **Completeness** | Response coverage | 0.0 - 1.0 |

### Performance Metrics

- **Response Time**: Query processing duration
- **Token Usage**: Input and output token counts
- **Document Count**: Number of retrieved documents
- **Vector Search Time**: Similarity search duration

## Troubleshooting

### Common Issues

1. **Server won't start**
   - Check port availability
   - Verify API keys are correctly configured
   - Ensure all dependencies are installed

2. **LangSmith traces not appearing**
   - Verify LangSmith API key is correct
   - Check network connectivity to LangSmith servers
   - Ensure tracing is enabled in configuration

3. **Poor response quality**
   - Check document quality and relevance
   - Verify embedding model is appropriate
   - Adjust LLM parameters (temperature, max_tokens)

4. **Slow performance**
   - Monitor response times and token usage
   - Consider using lighter models
   - Optimize document preprocessing

### Debug Mode

Enable debug logging for troubleshooting:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the LangSmith dashboard for error traces
3. Check the logs for detailed error information
4. Submit an issue on the repository

## Changelog

### Version 1.0.0
- Initial release with core RAG functionality
- LangSmith integration and tracing
- Advanced evaluation system
- Guardrails and safety features
- Multi-document support
- Performance optimization

---

## Deployment

For detailed deployment instructions, monitoring, and maintenance procedures, see [DEPLOYMENT.md](deploy/DEPLOYMENT.md).

**Note**: This README will be updated as the project evolves. For the latest documentation, please check the repository.

- **Response Time**: Query processing duration
- **Token Usage**: Input and output token counts
- **Document Count**: Number of retrieved documents
- **Vector Search Time**: Similarity search duration

## Guardrails and Safety

### Content Safety Features

- **PII Detection**: Automatically detects and redacts personally identifiable information
- **Content Moderation**: Ensures appropriate content generation
- **Query Filtering**: Filters inappropriate or sensitive queries
- **Output Validation**: Validates generated responses for safety

## Development

### Project Structure

```
src/
├── api.py              # FastAPI application
├── search.py           # Core search functionality
├── vectorstore.py      # Vector store operations
├── embedding.py        # Embedding processing
├── data_loader.py      # Document loading
├── config.py           # Configuration management
├── langsmith_client.py # LangSmith integration
├── enhanced_evaluation.py # Advanced evaluation
├── guardrails.py       # Content safety
├── human_in_loop.py    # Human review
└── middleware.py       # API middleware

tests/                  # Test suites
docs/                  # Documentation
examples/              # Example files
```
cd rag-ab-testing

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys and configuration
```

### 2. Configuration

Edit `.env` file with your settings:

```env
# LangSmith Configuration
LANGSMITH_API_KEY="your-langsmith-api-key"
LANGSMITH_PROJECT="rag-ab-testing"

# RAG Configuration
RAG_MODEL_NAME="sentence-transformers/all-MiniLM-L6-v2"
RAG_VECTOR_STORE_PATH="./data/vector_store"
RAG_TOP_K=5

# Analytics Configuration
ANALYTICS_ENABLED=true
DASHBOARD_ENABLED=true
```

### 3. Initialize Data

```bash
# Build vector store
python -m src.data_loader --build-index

# Start the application
python app.py
```

### 4. Access Dashboard

Open your browser and navigate to:
- **Main Application**: http://localhost:8000
- **Dashboard**: http://localhost:8001/dashboard

## API Usage

### Query with A/B Testing

```python
import requests

# Query with experiment context
response = requests.post("http://localhost:8000/api/query", json={
    "query": "What is machine learning?",
    "user_id": "user123",
    "experiment_context": "prompt_optimization"
})

print(response.json())
```

### Collect Feedback

```python
response = requests.post("http://localhost:8000/api/feedback", json={
    "user_id": "user123",
    "query": "What is machine learning?",
    "response": "Machine learning is a subset of AI...",
    "rating": 4,
    "thumbs_up": True,
    "comment": "Good response!"
})
```

### Evaluate Responses

```python
response = requests.post("http://localhost:8000/api/evaluate", json={
    "query": "What is machine learning?",
    "response": "Machine learning is a subset of AI...",
    "expected_response": "Machine learning algorithms learn from data...",
    "user_id": "user123"
})
```

## Experiment Management

### Creating Experiments

```python
from src.experiment_router import ExperimentRouter, ExperimentConfig

# Create experiment router
router = ExperimentRouter()

# Configure experiment
config = ExperimentConfig(
    name="prompt_optimization",
    type=ExperimentType.TRAFFIC_SPLIT,
    variant_a="standard_prompt",
    variant_b="enhanced_prompt",
    traffic_split=TrafficSplit.FIFTY_FIFTY,
    enabled=True,
    sample_rate=0.1
)

# Add experiment
router.add_experiment(config)
```

### Enable/Disable Experiments

```python
# Disable experiment
router.disable_experiment("prompt_optimization")

# Enable experiment
router.enable_experiment("prompt_optimization")
```

## Configuration Options

### Core Configuration

| Setting | Description | Default |
|---------|-------------|---------|
| `ANALYTICS_ENABLED` | Enable analytics collection | `true` |
| `DASHBOARD_ENABLED` | Enable dashboard server | `true` |
| `TRACING_ENABLED` | Enable LangSmith tracing | `true` |
| `FEEDBACK_ENABLED` | Enable feedback collection | `true` |
| `EVALUATION_ENABLED` | Enable response evaluation | `true` |

### Performance Configuration

| Setting | Description | Default |
|---------|-------------|---------|
| `ANALYTICS_REFRESH_INTERVAL` | Metrics refresh interval (seconds) | `5` |
| `DASHBOARD_REFRESH_INTERVAL` | Dashboard refresh interval (seconds) | `5` |
| `TRACING_SAMPLE_RATE` | Tracing sample rate | `0.1` |
| `EVALUATION_SAMPLE_RATE` | Evaluation sample rate | `0.1` |

### Experiment Configuration

| Setting | Description | Default |
|---------|-------------|---------|
| `EXPERIMENT_ENABLED` | Enable A/B testing | `true` |
| `EXPERIMENT_SAMPLE_RATE` | Default experiment sample rate | `0.1` |
| `EXPERIMENT_DEFAULT_TRAFFIC_SPLIT` | Default traffic split percentage | `50` |

## Dashboard Features

### Real-time Metrics
- Request latency and throughput
- Success rates and error monitoring
- User engagement metrics
- Cost tracking and optimization

### Experiment Analysis
- Variant performance comparison
- Statistical significance testing
- Confidence interval calculations
- Traffic distribution visualization

### User Feedback
- Satisfaction score tracking
- Thumbs up/down metrics
- Comment analysis and trends
- Sentiment analysis over time

### Performance Monitoring
- Response time trends
- Error rate tracking
- Resource utilization monitoring
- Cost optimization recommendations

## Integration Examples

### Python Client

```python
import requests

class RAGClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    def query(self, query, user_id=None, experiment=None):
        data = {"query": query}
        if user_id:
            data["user_id"] = user_id
        if experiment:
            data["experiment_context"] = experiment
        
        response = requests.post(f"{self.base_url}/api/query", json=data)
        return response.json()
    
    def get_experiment_metrics(self, experiment_name):
        response = requests.get(f"{self.base_url}/api/analytics/experiments/{experiment_name}/metrics")
        return response.json()
```

### JavaScript Client

```javascript
class RAGClient {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
    }
    
    async query(query, userId, experiment) {
        const response = await fetch(`${this.baseUrl}/api/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query,
                user_id: userId,
                experiment_context: experiment
            })
        });
        return response.json();
    }
    
    async getDashboardData() {
        const response = await fetch(`${this.baseUrl}/api/analytics/dashboard`);
        return response.json();
    }
}
```

## Monitoring and Logging

### Application Logs

Logs are written to `./logs/app.log` with the following structure:

```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "message": "Query processed successfully",
  "user_id": "user123",
  "experiment": "prompt_optimization",
  "variant": "variant_a",
  "latency": 1.5,
  "tokens_used": 150
}
```

### Metrics Export

Metrics can be exported in multiple formats:

```bash
# Export as JSON
curl -X POST http://localhost:8000/api/analytics/export -d '{"format": "json"}'

# Export as CSV
curl -X POST http://localhost:8000/api/analytics/export -d '{"format": "csv"}'
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_experiment_router.py
```

### Development Setup

```bash
# Install development dependencies
pip install -r requirements.txt

# Run with auto-reload
python app.py --reload

# Run dashboard separately
python dashboard.py
```

### Code Structure

```
src/
├── __init__.py
├── config.py           # Configuration management
├── api.py             # API endpoints
├── middleware.py      # HTTP middleware
├── experiment_router.py  # A/B testing routing
├── tracing.py         # LangSmith integration
├── analytics.py       # Analytics and metrics
├── rag_pipeline.py    # RAG processing pipeline
├── evaluators.py      # Response evaluation
├── feedback.py        # Feedback collection
├── data_loader.py     # Data loading and indexing
├── embedding.py       # Embedding management
├── vectorstore.py     # Vector store operations
├── search.py          # Search functionality
└── guardrails.py      # Content safety

tests/
├── test_experiment_router.py
├── test_analytics.py
├── test_rag_pipeline.py
└── test_feedback.py

data/
├── pdf/              # PDF documents
├── text_files/       # Text documents
├── vector_store/     # Vector database
└── feedback/         # User feedback

logs/                # Application logs
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed
   ```bash
   pip install -r requirements.txt
   ```

2. **Port Conflicts**: Change ports in .env if needed
   ```env
   PORT=8000
   DASHBOARD_PORT=8001
   ```

3. **LangSmith Connection**: Verify API key and network access
   ```env
   LANGSMITH_API_KEY="your-api-key"
   ```

4. **Vector Store Issues**: Rebuild index if needed
   ```bash
   python -m src.data_loader --build-index
   ```

### Debug Mode

Enable debug logging:

```env
LOG_LEVEL=DEBUG
```

### Performance Tuning

- Adjust `ANALYTICS_REFRESH_INTERVAL` for optimal performance
- Configure `EVALUATION_SAMPLE_RATE` to balance accuracy and performance
- Use appropriate `RAG_TOP_K` values for your use case

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the GitHub repository
- Check the documentation
- Review the troubleshooting section

---

Built with ❤️ for production-grade A/B testing of RAG applications.

```powershell
pip install -r requirement.txt
```

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key_here
```

Do not commit real API keys. `.env` is ignored by git; use `.env.example` as the
template for deployments.

## Usage

Place documents under `data/`. The loader searches recursively, so files can be
organized in subfolders such as `data/pdf/` or `data/text_files/`.

The web UI also supports PDF upload from `/`. Uploaded PDFs are saved under
`data/uploads/` and the FAISS index is rebuilt automatically.

## RAG Flow

```text
Documents in data/
        |
        v
load_all_documents()
        |
        v
Chunk documents with EmbeddingPipeline
        |
        v
Create embeddings with SentenceTransformer
        |
        v
Store vectors and metadata in FAISS
        |
        v
Search top matching chunks for a user query
        |
        v
Send retrieved context to Groq
        |
        v
Return summarized answer
```

Build or rebuild the FAISS index:

```powershell
python -m src.vectorstore
```

Run the production API locally:

```powershell
uvicorn src.api:app --host 0.0.0.0 --port 8000
```

Or with Python:

```powershell
python main.py
```

Health and readiness endpoints:

```powershell
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

Ask a question:

```powershell
curl -X POST http://localhost:8000/query `
  -H "Content-Type: application/json" `
  -d "{\"query\":\"What is NLP?\",\"top_k\":3}"
```

Run the old example RAG query:

```powershell
python app.py
```

The default example asks:

```text
What is NLP and Explain it
```

You can change the query in `app.py`, or use the classes directly:

```python
from src.search import RAGSearch

rag = RAGSearch()
answer = rag.search_and_summarize("What is attention mechanism?", top_k=3)
print(answer)
```

## Supported Documents

`src.data_loader.load_all_documents()` currently supports:

- PDF (`.pdf`)
- Text (`.txt`)
- CSV (`.csv`)
- Excel (`.xlsx`)
- Word (`.docx`)
- JSON (`.json`)

## Notes

- The FAISS index is stored in `faiss_store/faiss.index`.
- Metadata for retrieved chunks is stored in `faiss_store/metadata.pkl`.
- If the FAISS files are missing, `RAGSearch` attempts to build the index from
  documents in `data/`.
- The default embedding model is `all-MiniLM-L6-v2`.
- The default LLM model is `llama-3.3-70b-versatile`.

## Docker Deployment

Build and run with Docker Compose:

```powershell
docker compose up --build
```

The API is exposed on `http://localhost:8000`.

Runtime configuration:

```env
GROQ_API_KEY=your_groq_api_key_here
RAG_DATA_DIR=data
RAG_PERSIST_DIR=faiss_store
RAG_EMBEDDING_MODEL=all-MiniLM-L6-v2
RAG_LLM_MODEL=llama-3.3-70b-versatile
RAG_DEFAULT_TOP_K=5
RAG_AUTO_BUILD_INDEX=true
```
