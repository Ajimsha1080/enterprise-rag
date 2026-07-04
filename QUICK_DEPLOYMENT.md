# Quick Deployment Guide for RAG System

## Current Status
- Azure CLI: ❌ Not installed
- Docker: ❌ Not running
- RAG API: ✅ Can run locally

## Alternative Deployment Options

### Option 1: Local Development (Working)
```bash
cd "C:\Users\91730\Downloads\Rag"
python src/api.py
```
- Access at: http://127.0.0.1:8001
- API docs: http://127.0.0.1:8001/docs

### Option 2: Install Required Tools First

#### Install Azure CLI
```bash
# Method 1: Using winget
winget install Microsoft.AzureCLI

# Method 2: Download from web
# 1. Go to https://aka.ms/InstallAzureCLIDeb
# 2. Download the installer
# 3. Run the installer

# Method 3: Install via Chocolatey
choco install azure-cli
```

#### Start Docker Desktop
1. Open Docker Desktop application
2. Wait for Docker to start
3. Verify with: `docker --version`

#### Then Run Azure Deployment
```bash
cd deploy/azure
.\deploy.ps1 -ResourceGroupName "rag-api-rg" -Location "East US" -DeploymentType "container-apps" -ContainerAppName "rag-api-prod" -GroqApiKey "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" -LangSmithApiKey "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" -ReplicaCount 2 -CpuCoreCount 0.5 -MemoryInGB 1.0
```

### Option 3: Manual Kubernetes Deployment
```bash
# Install kubectl
az aks install-cli

# Login to Azure
az login

# Create AKS cluster
az aks create --resource-group aks-rg --name rag-cluster --node-count 2 --node-vm-size Standard_DS2_v2

# Get credentials
az aks get-credentials --resource-group aks-rg --name rag-cluster

# Deploy your app
kubectl apply -f deploy/kubernetes/deployment.yaml
kubectl apply -f deploy/kubernetes/service.yaml
```

### Option 4: Use Azure Portal (Web Interface)
1. Go to portal.azure.com
2. Create "Container App" manually
3. Use the Docker image from your local build
4. Configure environment variables
5. Deploy and get URL

## Current API Status
- Local server: Can run on localhost:8001
- LangSmith: Configured and working
- API keys: Already configured in .env
- Vector store: Has 61 documents loaded

## Next Steps
1. Choose deployment option above
2. Install required tools if needed
3. Deploy to Azure or Kubernetes
4. Access your RAG system via the provided URL

The RAG system is ready for production deployment once the tools are installed!