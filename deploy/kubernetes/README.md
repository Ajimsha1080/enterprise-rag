# Azure Kubernetes Service Deployment Guide

This guide explains how to deploy your RAG system to Azure Kubernetes Service (AKS).

## Prerequisites

Before starting the deployment, make sure you have:

### Azure CLI Installation
```bash
# Install Azure CLI (Windows)
winget install Microsoft.AzureCLI

# Or download from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli
```

### kubectl Installation
```bash
# Install kubectl (Windows)
winget install kubernetes.kubectl
```

### Azure Container Registry
```bash
# Create Azure Container Registry
az acr create --resource-group aks-rg --name yourregistry --sku Basic
```

### Azure Kubernetes Service Cluster
```bash
# Create AKS cluster
az aks create --resource-group aks-rg --name rag-cluster --node-count 2 --node-vm-size Standard_DS2_v2 --enable-addons monitoring --generate-ssh-keys
```

## Deployment Steps

### 1. Update Configuration
Edit the `deploy-aks.sh` script with your Azure Container Registry name:
```bash
REGISTRY_NAME="yourregistry"  # Change to your Azure Container Registry name
```

### 2. Run Deployment Script
```bash
# Make script executable
chmod +x deploy-aks.sh

# Run deployment
./deploy-aks.sh
```

### 3. Monitor Deployment
```bash
# Check pod status
kubectl get pods -n rag-system

# Check service status
kubectl get service rag-api-service -n rag-system

# Wait for external IP
kubectl get service rag-api-service -n rag-system --watch
```

### 4. Access the Application
Once the deployment is complete, you can access your RAG system at:
```
http://<EXTERNAL-IP>
```

## Configuration Files

### deployment.yaml
- Kubernetes deployment configuration
- 2 replicas for high availability
- Resource limits: 1GB RAM, 500m CPU
- Health checks configured
- Environment variables for API keys

### service.yaml
- LoadBalancer service type
- External traffic policy: Cluster
- Port mapping: 80 → 8001
- Session affinity disabled

## Monitoring and Management

### View Pod Logs
```bash
kubectl logs -f deployment/rag-api -n rag-system
```

### Describe Service
```bash
kubectl describe service rag-api-service -n rag-system
```

### Scale Deployment
```bash
kubectl scale deployment rag-api --replicas=3 -n rag-system
```

### Update Deployment
```bash
# Make changes to deployment.yaml and reapply
kubectl apply -f deployment.yaml
```

## Troubleshooting

### Common Issues

1. **Image Pull Error**
   ```bash
   # Check image registry access
   az acr login --name yourregistry
   ```

2. **Pod Crash**
   ```bash
   # Check pod logs
   kubectl logs <pod-name> -n rag-system
   
   # Describe pod for details
   kubectl describe pod <pod-name> -n rag-system
   ```

3. **Service Not Available**
   ```bash
   # Check service status
   kubectl get service rag-api-service -n rag-system
   
   # Check external IP allocation
   kubectl describe service rag-api-service -n rag-system
   ```

### Commands for Debugging

```bash
# Get all resources in namespace
kubectl get all -n rag-system

# Check cluster status
kubectl cluster-info

# Get node information
kubectl get nodes -o wide

# Check deployment events
kubectl get events --sort-by=.metadata.creationTimestamp -n rag-system
```

## Cost Considerations

- **AKS Cluster**: ~$100-200/month for 2 nodes (Standard_DS2_v2)
- **ACR**: ~$10-20/month for basic tier
- **Additional Services**: Monitoring, Load Balancer (~$20-40/month)

**Total estimated cost**: $130-260/month

## Backup and Restore

### Backup Configuration
```bash
# Export deployment configuration
kubectl get deployment rag-api -n rag-system -o yaml > backup-deployment.yaml
kubectl get service rag-api-service -n rag-system -o yaml > backup-service.yaml
```

### Restore Configuration
```bash
# Restore from backup
kubectl apply -f backup-deployment.yaml
kubectl apply -f backup-service.yaml
```

## Scaling

### Horizontal Scaling
```bash
# Scale to 3 replicas
kubectl scale deployment rag-api --replicas=3 -n rag-system
```

### Vertical Scaling (requires edit)
Edit `deployment.yaml` and change resource limits:
```yaml
resources:
  limits:
    memory: "2Gi"    # Increase memory
    cpu: "1000m"     # Increase CPU
```

## Security Considerations

### Network Security
- Use Network Policies to restrict traffic
- Configure Ingress instead of LoadBalancer for better control
- Use TLS certificates for HTTPS

### Access Control
- Use Kubernetes RBAC
- Configure service accounts
- Use Azure Active Directory integration

### Monitoring
- Enable Azure Monitor for containers
- Configure logging and metrics
- Set up alerts for critical issues