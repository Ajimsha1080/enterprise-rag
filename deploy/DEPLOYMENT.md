# RAG API Deployment Guide

This guide provides comprehensive instructions for deploying the RAG API to Azure and Kubernetes platforms.

## Table of Contents

- [Azure Deployment](#azure-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Configuration](#configuration)
- [Monitoring and Logging](#monitoring-and-logging)
- [Troubleshooting](#troubleshooting)

## Azure Deployment

### Prerequisites

- Azure CLI installed
- Azure subscription
- Docker installed (for Container Apps)
- Groq API key
- LangSmith API key

### Deployment Options

#### 1. Azure Container Apps (Recommended)

Container Apps is the recommended option for RAG API as it provides:
- Serverless scaling
- Built-in networking
- Integration with Azure Monitor
- Cost-effective resource usage

```bash
# Deploy using PowerShell
.\deploy\azure\deploy.ps1 -ResourceGroupName "rag-api-rg" -Location "East US" -DeploymentType "container-apps" -GroqApiKey "your-groq-key" -LangSmithApiKey "your-langsmith-key"

# Or using Azure CLI directly
az deployment group create --resource-group "rag-api-rg" --template-file deploy/azure/main.bicep --parameters deploy/azure/parameters.json
```

#### 2. Azure App Service

App Service is suitable for smaller deployments with fixed resource requirements:

```bash
# Deploy using PowerShell
.\deploy\azure\deploy.ps1 -ResourceGroupName "rag-api-rg" -Location "West US" -DeploymentType "app-service" -AppServiceName "rag-api-app" -GroqApiKey "your-groq-key" -LangSmithApiKey "your-langsmith-key" -Sku "B2"
```

#### 3. Bicep Template Parameters

| Parameter | Description | Default | Required |
|-----------|-------------|---------|----------|
| `containerAppName` | Name of Container App | rag-api-<unique> | No |
| `groqApiKey` | Groq API key | - | Yes |
| `langsmithApiKey` | LangSmith API key | - | Yes |
| `replicaCount` | Number of replicas | 1 | No |
| `cpuCoreCount` | CPU cores | 0.25 | No |
| `memoryInGB` | Memory in GB | 0.5 | No |
| `environment` | Environment | Development | No |

#### 4. Azure Environment Variables

| Variable | Value |
|----------|-------|
| `GROQ_API_KEY` | Your Groq API key |
| `LANGSMITH_API_KEY` | Your LangSmith API key |
| `RAG_DATA_DIR` | /app/data |
| `RAG_PERSIST_DIR` | /app/faiss_store |
| `RAG_EMBEDDING_MODEL` | all-MiniLM-L6-v2 |
| `RAG_LLM_MODEL` | llama-3.3-70b-versatile |
| `RAG_DEFAULT_TOP_K` | 5 |
| `RAG_AUTO_BUILD_INDEX` | true |

## Kubernetes Deployment

### Prerequisites

- Kubernetes cluster (AKS, EKS, GKE, or local)
- Helm 3 installed
- kubectl installed
- Docker installed
- Groq API key
- LangSmith API key

### Deployment Options

#### 1. Using Helm Chart (Recommended)

The Helm chart provides a complete deployment configuration with persistent storage, services, and monitoring.

```bash
# Deploy using shell script
./deploy/kubernetes/deploy-kubernetes.sh -d -GROQ_API_KEY="your-groq-key" -LANGSMITH_API_KEY="your-langsmith-key"

# Or using PowerShell
.\deploy\kubernetes\deploy-kubernetes.ps1 -Action deploy -GroqApiKey "your-groq-key" -LangSmithApiKey "your-langsmith-key"

# Optional: Specify Docker registry
export REGISTRY_URL="your-registry.azurecr.io"
export GROQ_API_KEY="your-groq-key"
export LANGSMITH_API_KEY="your-langsmith-key"
./deploy/kubernetes/deploy-kubernetes.sh
```

#### 2. Using YAML Manifests

For direct Kubernetes deployment:

```bash
# Apply all manifests
kubectl apply -f deploy/kubernetes/deployment.yaml
kubectl apply -f deploy/kubernetes/service.yaml
kubectl apply -f deploy/kubernetes/pvcs.yaml
kubectl apply -f deploy/kubernetes/secrets.yaml
```

#### 3. Helm Chart Configuration

Override default values during deployment:

```bash
helm install rag-api ./deploy/kubernetes/helm/rag-chart \
  --namespace rag-system \
  --set replicaCount=2 \
  --set resources.requests.cpu=500m \
  --set resources.requests.memory=1Gi \
  --set persistence.data.size=10Gi \
  --set persistence.faiss.size=20Gi \
  --set secrets.groqApiKey="your-groq-key" \
  --set secrets.langsmithApiKey="your-langsmith-key"
```

#### 4. Kubernetes Resources

| Resource | Description |
|----------|-------------|
| `Deployment` | Manages application replicas |
| `Service` | Exports application via LoadBalancer |
| `PersistentVolumeClaim` | Persistent storage for data and FAISS index |
| `Secret` | Securely stores API keys |
| `ConfigMap` | Configuration data |

### Environment Variables

| Variable | Value |
|----------|-------|
| `GROQ_API_KEY` | Your Groq API key |
| `LANGSMITH_API_KEY` | Your LangSmith API key |
| `RAG_DATA_DIR` | /app/data |
| `RAG_PERSIST_DIR` | /app/faiss_store |
| `RAG_EMBEDDING_MODEL` | all-MiniLM-L6-v2 |
| `RAG_LLM_MODEL` | llama-3.3-70b-versatile |
| `RAG_DEFAULT_TOP_K` | 5 |
| `RAG_AUTO_BUILD_INDEX` | true |
| `ENVIRONMENT` | Production |

## Configuration

### Configuration Files

#### 1. Azure Configuration

- `deploy/azure/main.bicep` - Main Bicep template
- `deploy/azure/azuredeploy.json` - Alternative ARM template
- `deploy/azure/parameters.json` - Template parameters
- `deploy/azure/deploy.ps1` - Deployment script

#### 2. Kubernetes Configuration

- `deploy/kubernetes/deployment.yaml` - Kubernetes deployment
- `deploy/kubernetes/service.yaml` - Kubernetes service
- `deploy/kubernetes/pvcs.yaml` - Persistent volume claims
- `deploy/kubernetes/secrets.yaml` - Secrets configuration
- `deploy/kubernetes/helm/rag-chart/` - Helm chart directory

#### 3. Configuration Parameters

| Parameter | Environment Variable | Description |
|-----------|---------------------|-------------|
| `RAG_DATA_DIR` | RAG_DATA_DIR | Directory containing source documents |
| `RAG_PERSIST_DIR` | RAG_PERSIST_DIR | Directory for FAISS vector store |
| `RAG_EMBEDDING_MODEL` | RAG_EMBEDDING_MODEL | Embedding model name |
| `RAG_LLM_MODEL` | RAG_LLM_MODEL | LLM model name |
| `RAG_DEFAULT_TOP_K` | RAG_DEFAULT_TOP_K | Default number of results |
| `RAG_AUTO_BUILD_INDEX` | RAG_AUTO_BUILD_INDEX | Auto-build vector index |

## Monitoring and Logging

### Azure Monitoring

#### 1. Azure Container Apps

- **Application Insights**: Built-in monitoring
- **Log Analytics**: Centralized logging
- **Container Apps Metrics**: CPU, memory, throughput
- **Azure Monitor**: Unified monitoring

#### 2. Azure App Service

- **Application Insights**: Application monitoring
- **Log Analytics**: Centralized logging
- **App Service Metrics**: CPU, memory, response times
- **Azure Monitor**: Unified monitoring

### Kubernetes Monitoring

#### 1. Built-in Monitoring

- **Metrics Server**: Resource metrics
- **Kube-state-metrics**: Kubernetes object metrics
- **Prometheus**: Container metrics
- **Grafana**: Visualization dashboard

#### 2. Custom Metrics

- **Response Time**: Query processing duration
- **Token Usage**: Input and output token counts
- **Document Count**: Number of retrieved documents
- **Error Rate**: Error and failure counts

### Logging

#### 1. Azure Logging

- **Log Analytics**: Centralized log aggregation
- **Application Insights**: Application logs
- **Container Apps Logs**: Container log streaming
- **Azure Monitor**: Log search and analytics

#### 2. Kubernetes Logging

- **Cluster Logging**: EFK stack or managed logging
- **Container Logs**: Individual container logs
- **Structured Logging**: JSON-formatted logs
- **Log Aggregation**: Centralized log management

## Troubleshooting

### Common Issues

#### 1. Azure Deployment Issues

**Problem**: Container App fails to start
- Check resource limits and requests
- Verify API keys in secrets
- Check environment variables
- Review container logs

**Problem**: App Service returns 500 errors
- Check application logs
- Verify environment variables
- Check container registry access
- Review resource allocation

#### 2. Kubernetes Deployment Issues

**Problem**: Pod fails to start
- Check image registry access
- Verify secrets and environment variables
- Check resource limits
- Review pod events

**Problem**: Service not accessible
- Check service type and configuration
- Verify pod status
- Check network policies
- Review ingress configuration

#### 3. Configuration Issues

**Problem**: API keys not working
- Verify key format and validity
- Check secret configuration
- Ensure proper environment variables
- Test API connectivity

**Problem**: Data directory not accessible
- Verify directory permissions
- Check volume mounts
- Ensure persistent storage configuration
- Review backup and recovery

### Debug Commands

#### 1. Azure Debug Commands

```bash
# Check container app status
az containerapp show --name rag-api --resource-group rag-api-rg

# View container logs
az containerapp logs --name rag-api --resource-group rag-api-rg

# Check resource status
az resource list --resource-group rag-api-rg

# Check application insights
az monitor app-insights component show --app rag-api --resource-group rag-api-rg
```

#### 2. Kubernetes Debug Commands

```bash
# Check pod status
kubectl get pods -n rag-system

# View pod logs
kubectl logs -f rag-api-<pod-id> -n rag-system

# Check service status
kubectl get svc -n rag-system

# Check PVC status
kubectl get pvc -n rag-system

# Check events
kubectl get events -n rag-system --sort-by='.metadata.creationTimestamp'
```

### Performance Optimization

#### 1. Azure Optimization

- **Container Apps**: Use auto-scaling for variable workloads
- **App Service**: Choose appropriate SKU for your workload
- **Storage**: Use premium SSDs for better performance
- **Networking**: Use VNet integration for enhanced security

#### 2. Kubernetes Optimization

- **Resource Limits**: Configure appropriate CPU and memory limits
- **Auto-scaling**: Use HPA for horizontal scaling
- **Storage**: Use appropriate storage class for performance
- **Networking**: Use service mesh for advanced networking

### Backup and Recovery

#### 1. Azure Backup

- **Container Apps**: Backup environment configuration
- **App Service**: Backup site and configuration
- **Storage**: Enable blob storage backup
- **Database**: Enable SQL backup if applicable

#### 2. Kubernetes Backup

- **Persistent Volumes**: Use Velero for PV backup
- **Configuration**: GitOps for configuration management
- **Secrets**: Use external secret management
- **ETCD**: Regular etcd backup

## Maintenance

### 1. Regular Updates

- **Application**: Regularly update dependencies and code
- **Infrastructure**: Keep Azure/Kubernetes components updated
- **Security**: Apply security patches and updates
- **Monitoring**: Update monitoring and alerting configurations

### 2. Health Checks

- **Application Health**: Implement comprehensive health checks
- **Resource Health**: Monitor resource utilization
- **Performance Health**: Track response times and throughput
- **Security Health**: Regular security assessments

### 3. Cost Optimization

- **Resource Monitoring**: Regular review of resource usage
- **Right-sizing**: Adjust resource allocation based on usage
- **Auto-scaling**: Implement appropriate scaling policies
- **Cleanup**: Remove unused resources regularly

This deployment guide provides comprehensive instructions for deploying and maintaining the RAG API in Azure and Kubernetes environments. For specific issues, refer to the troubleshooting section or check the logs for detailed error information.