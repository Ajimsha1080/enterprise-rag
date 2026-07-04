# RAG System Deployment Guide

This guide provides step-by-step instructions for deploying your RAG system to Azure and Kubernetes platforms.

## 🚀 **Getting Started**

### Prerequisites
- **Azure CLI**: `az` (for Azure deployments)
- **Kubernetes CLI**: `kubectl` (for Kubernetes deployments)
- **Helm**: Package manager for Kubernetes
- **Docker**: For building and pushing images
- **Python 3.8+**: For local development

---

## ☁️ **Azure Deployment**

### Method 1: Azure Container Apps (Recommended)

#### 1. **Install Required Tools**
```bash
# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Login to Azure
az login
az account set --subscription "your-subscription-id"
```

#### 2. **Configure Environment Variables**
Create a `.env` file with your API keys:
```bash
# Copy your .env file to the deployment directory
cp .env deploy/azure/

# Or set environment variables
export GROQ_API_KEY="your-groq-api-key"
export LANGSMITH_API_KEY="your-langsmith-api-key"
export LANGSMITH_PROJECT="rag-system"
```

#### 3. **Build and Push Docker Image**
```bash
cd deploy/azure

# Build Docker image
docker build -t rag-api:latest ../..

# Push to Azure Container Registry (ACR)
az acr login --name your-acr-name
docker tag rag-api:latest your-acr-name.azurecr.io/rag-api:latest
docker push your-acr-name.azurecr.io/rag-api:latest
```

#### 4. **Deploy to Azure Container Apps**
```bash
# Run the deployment script
cd deploy/azure
.\deploy.ps1 -ResourceGroupName "rag-api-rg" -Location "East US" -DeploymentType "container-apps" -ContainerAppName "rag-api-prod" -GroqApiKey "your-groq-key" -LangSmithApiKey "your-langsmith-key" -ReplicaCount 2 -CpuCoreCount 0.5 -MemoryInGB 1.0
```

**Manual Deployment using Bicep:**
```bash
# Deploy infrastructure
az deployment group create -g rag-api-rg --template-file main.bicep --parameters containerImage="your-acr-name.azurecr.io/rag-api:latest" groqApiKey="your-groq-key" langsmithApiKey="your-langsmith-key" replicaCount=2 cpuCoreCount=0.5 memoryInGB=1.0

# Get deployment status
az deployment group show -g rag-api-rg --name main
```

#### 5. **Access the Application**
```bash
# Get the Container App URL
az containerapp show -g rag-api-rg -n rag-api-prod --query properties.configuration.ingress.fqdn -o tsv
```

### Method 2: Azure App Service (Simple)

#### 1. **Deploy to App Service**
```bash
cd deploy/azure

# Run the deployment script
.\deploy.ps1 -ResourceGroupName "rag-api-rg" -Location "East US" -DeploymentType "app-service" -AppServiceName "rag-api-service" -GroqApiKey "your-groq-key" -LangSmithApiKey "your-langsmith-key" -Sku "B1"
```

**Manual Deployment:**
```bash
# Create App Service plan
az appservice plan create -g rag-api-rg -n rag-api-plan --sku B1 --location "East US"

# Create Web App
az webapp create -g rag-api-rg -n rag-api-service --plan rag-api-plan --runtime "PYTHON:3.9" --deployment-local-git

# Configure environment variables
az webapp config appsettings set -g rag-api-rg -n rag-api-service --settings GROQ_API_KEY="your-groq-key" LANGSMITH_API_KEY="your-langsmith-key" LANGSMITH_PROJECT="rag-system"

# Deploy code
az webapp deploy -g rag-api-rg -n rag-api-service --src-path ../.. --target-path "site/wwwroot"
```

#### 2. **Access the Application**
```bash
# Get the Web App URL
az webapp show -g rag-api-rg -n rag-api-service --query defaultHostName -o tsv
```

---

## 🐳 **Kubernetes Deployment**

### Prerequisites
- **Azure Kubernetes Service (AKS)** or any other Kubernetes cluster
- **Helm 3+**
- **kubectl** configured to connect to your cluster

#### 1. **Install Required Tools**
```bash
# Install Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Install kubectl
az aks install-cli
```

#### 2. **Connect to Your Cluster**
```bash
# For Azure AKS
az aks get-credentials --resource-group aks-rg --name aks-cluster

# Verify connection
kubectl get nodes
```

#### 3. **Prepare Docker Image**
```bash
# Build Docker image
docker build -t rag-api:latest .

# Push to container registry
docker tag rag-api:latest your-registry/rag-api:latest
docker push your-registry/rag-api:latest
```

#### 4. **Deploy Using Helm**
```bash
cd deploy/kubernetes

# Create namespace
kubectl create namespace rag-system

# Deploy secrets
kubectl apply -f secrets.yaml

# Deploy using Helm
helm install rag-api ./helm/rag-chart -n rag-system \
  --set image.repository=your-registry/rag-api \
  --set image.tag=latest \
  --set env.GROQ_API_KEY="your-groq-key" \
  --set env.LANGSMITH_API_KEY="your-langsmith-key" \
  --set env.LANGSMITH_PROJECT="rag-system"
```

#### 5. **Deploy Using YAML Manifests**
```bash
cd deploy/kubernetes

# Apply all manifests
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f pvcs.yaml
kubectl apply -f secrets.yaml
```

### Method 3: Quick Kubernetes Script
```bash
cd deploy/kubernetes

# Use the deployment script
chmod +x deploy-kubernetes.sh
./deploy-kubernetes.sh

# For PowerShell
.\deploy-kubernetes.ps1
```

#### 6. **Access the Application**
```bash
# Get service URL
kubectl get service rag-api-service -n rag-system

# Port forward for testing
kubectl port-forward svc/rag-api-service 8001:8001 -n rag-system
```

---

## 🔧 **Configuration Options**

### Environment Variables
```bash
# Required
GROQ_API_KEY=your_groq_api_key_here
LANGSMITH_API_KEY=your_langsmith_api_key_here
LANGSMITH_PROJECT=rag-system

# Optional
RAG_DATA_DIR=/data
RAG_PERSIST_DIR=/data/faiss_store
RAG_EMBEDDING_MODEL=all-MiniLM-L6-v2
RAG_LLM_MODEL=llama-3.3-70b-versatile
RAG_DEFAULT_TOP_K=5
RAG_TEMPERATURE=0.7
RAG_MAX_TOKENS=2000
RAG_AUTO_BUILD_INDEX=true
```

### Azure Container Apps Configuration
```json
{
  "replicaCount": 2,
  "cpuCoreCount": 0.5,
  "memoryInGB": 1.0,
  "secrets": {
    "GROQ_API_KEY": "your-groq-key",
    "LANGSMITH_API_KEY": "your-langsmith-key"
  }
}
```

### Kubernetes Configuration
```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
  limits:
    memory: "1Gi"
    cpu: "500m"
```

---

## 📊 **Monitoring and Logging**

### Azure Container Apps
```bash
# View Container App logs
az containerapp logs -g rag-api-rg -n rag-api-prod --follow

# Monitor Container App metrics
az monitor metrics list --resource rag-api-prod --metrics "CPU Usage", "Memory Usage"
```

### Kubernetes
```bash
# View pod logs
kubectl logs -f deployment/rag-api -n rag-system

# View pod metrics
kubectl top pods -n rag-system

# Set up monitoring with Helm
helm install monitoring prometheus-community/kube-prometheus-stack -n monitoring
```

---

## 🔒 **Security Configuration**

### Azure
```bash
# Configure Application Gateway for Container Apps
az network application-gateway create -g rag-api-rg -n rag-gw --sku WAF_v2 --location "East US"

# Set up WAF rules
az network application-gateway waf-config set -g rag-api-rg --name rag-gw --enabled true --firewall-mode Prevention
```

### Kubernetes
```bash
# Configure Network Policies
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: rag-api-policy
  namespace: rag-system
spec:
  podSelector:
    matchLabels:
      app: rag-api
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
EOF
```

---

## 🚀 **Deployment Checklist**

### Azure Container Apps
- [ ] Azure CLI installed and logged in
- [ ] Resource group created
- [ ] Docker image built and pushed to ACR
- [ ] Bicep template deployed
- [ ] Environment variables configured
- [ ] Health checks passing
- [ ] Application accessible via URL

### Kubernetes
- [ ] Kubernetes cluster configured
- [ ] Helm installed and configured
- [ ] Docker image built and pushed
- [ ] Namespace created
- [ ] Secrets deployed
- [ ] PVCs created
- [ ] Services configured
- [ ] Application accessible via service

### General
- [ ] All API keys configured
- [ ] Environment variables set correctly
- [ ] Health endpoints responding
- [ ] LangSmith integration working
- [ ] RAG functionality operational

---

## 🔧 **Troubleshooting**

### Common Issues

**Azure Container Apps**
```bash
# Check deployment status
az deployment group show -g rag-api-rg --name main

# View Container App status
az containerapp show -g rag-api-rg -n rag-api-prod

# Debug Container App
az containerapp revision list -g rag-api-rg -n rag-api-prod --show-events
```

**Kubernetes**
```bash
# Check pod status
kubectl get pods -n rag-system

# Describe pod for debugging
kubectl describe pod rag-api-xxx -n rag-system

# Check pod logs
kubectl logs rag-api-xxx -n rag-system --tail=100
```

### Performance Issues
- Increase CPU/memory resources
- Scale replica count
- Optimize RAG queries
- Cache frequently accessed data

### Connection Issues
- Verify API keys are correct
- Check network connectivity
- Validate DNS resolution
- Test service endpoints

---

## 📞 **Support**

For deployment support:
1. Check the troubleshooting section above
2. Review Azure/Kubernetes documentation
3. Open an issue in the GitHub repository
4. Contact the development team for enterprise support

---

**Happy Deploying!** 🚀

Your RAG system is now ready for production deployment on Azure and Kubernetes platforms.