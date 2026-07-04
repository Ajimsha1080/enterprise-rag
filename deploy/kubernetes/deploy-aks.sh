#!/bin/bash

# Azure Kubernetes Service Deployment Script
# Deploy RAG system to Azure Kubernetes Service

set -e

# Configuration
NAMESPACE="rag-system"
REGISTRY_NAME="yourregistry"  # Change to your Azure Container Registry name
RESOURCE_GROUP="aks-rg"
CLUSTER_NAME="rag-cluster"
IMAGE_TAG="latest"

echo "🚀 Starting Azure Kubernetes Service deployment..."

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI not found. Please install Azure CLI first."
    exit 1
fi

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl not found. Please install kubectl first."
    exit 1
fi

# Login to Azure if not already logged in
echo "🔐 Checking Azure login..."
az account show > /dev/null || az login

# Get cluster credentials
echo "🔗 Getting AKS cluster credentials..."
az aks get-credentials --resource-group $RESOURCE_GROUP --name $CLUSTER_NAME

# Create namespace if it doesn't exist
echo "📦 Creating namespace..."
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Build and push Docker image (if needed)
echo "🐳 Building Docker image..."
docker build -t $REGISTRY_NAME/rag-api:$IMAGE_TAG ../..

# Push to Azure Container Registry
echo "📤 Pushing image to Azure Container Registry..."
docker push $REGISTRY_NAME/rag-api:$IMAGE_TAG

# Update deployment with correct image
echo "⚙️ Updating deployment..."
sed -i "s|YOUR_REGISTRY/rag-api:latest|$REGISTRY_NAME/rag-api:$IMAGE_TAG|g" deployment.yaml

# Apply deployment
kubectl apply -f deployment.yaml

# Apply service
kubectl apply -f service.yaml

# Wait for deployment to be ready
echo "⏳ Waiting for deployment to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/rag-api -n $NAMESPACE

# Get service details
echo "🌐 Getting service details..."
kubectl get service rag-api-service -n $NAMESPACE

echo "✅ Deployment completed!"
echo "🎉 Your RAG system is being deployed to Azure Kubernetes Service!"
echo ""
echo "To get the external IP, run:"
echo "kubectl get service rag-api-service -n $NAMESPACE --watch"
echo ""
echo "To check pod status, run:"
echo "kubectl get pods -n $NAMESPACE"
echo ""
echo "To access the application, wait for the external IP to be assigned and then visit:"
echo "http://<EXTERNAL-IP>"