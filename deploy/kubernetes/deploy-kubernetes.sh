#!/bin/bash

# Kubernetes Deployment Script for RAG API
# This script deploys the RAG API to a Kubernetes cluster

set -e

# Configuration
NAMESPACE="rag-system"
CHART_NAME="rag-chart"
RELEASE_NAME="rag-api"
CHART_PATH="./deploy/kubernetes/helm/rag-chart"
KUBECTL="kubectl"
HELM="helm"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if kubectl is installed
    if ! command -v $KUBECTL &> /dev/null; then
        log_error "kubectl is not installed. Please install kubectl first."
        exit 1
    fi
    
    # Check if helm is installed
    if ! command -v $HELM &> /dev/null; then
        log_error "helm is not installed. Please install helm first."
        exit 1
    fi
    
    # Check if cluster is accessible
    if ! $KUBECTL cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster. Please check your kubeconfig."
        exit 1
    fi
    
    log_info "All prerequisites satisfied."
}

# Create namespace
create_namespace() {
    log_info "Creating namespace: $NAMESPACE"
    $KUBECTL create namespace $NAMESPACE --dry-run=client -o yaml | $KUBECTL apply -f -
}

# Build and push Docker image
build_and_push_image() {
    log_info "Building Docker image..."
    docker build -t rag-api:latest .
    
    if [ -n "$REGISTRY_URL" ]; then
        log_info "Tagging and pushing image to registry..."
        docker tag rag-api:latest $REGISTRY_URL/rag-api:latest
        docker push $REGISTRY_URL/rag-api:latest
        
        log_info "Updating Helm chart values..."
        sed -i "s|repository: rag-api|repository: $REGISTRY_URL/rag-api|" $CHART_PATH/values.yaml
        sed -i "s|tag: latest|tag: latest|" $CHART_PATH/values.yaml
        sed -i "s|registry: \"\"|registry: \"$REGISTRY_URL\"|" $CHART_PATH/values.yaml
    fi
}

# Install or upgrade Helm chart
install_or_upgrade_chart() {
    log_info "Installing/upgrading Helm chart..."
    
    if helm list -n $NAMESPACE | grep -q $RELEASE_NAME; then
        log_info "Upgrading existing release..."
        $HELM upgrade $RELEASE_NAME $CHART_PATH \
            --namespace $NAMESPACE \
            --wait \
            --timeout 300s \
            --set secrets.groqApiKey="$GROQ_API_KEY" \
            --set secrets.langsmithApiKey="$LANGSMITH_API_KEY"
    else
        log_info "Installing new release..."
        $HELM install $RELEASE_NAME $CHART_PATH \
            --namespace $NAMESPACE \
            --wait \
            --timeout 300s \
            --set secrets.groqApiKey="$GROQ_API_KEY" \
            --set secrets.langsmithApiKey="$LANGSMITH_API_KEY"
    fi
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."
    
    # Check pods
    log_info "Checking pods..."
    $KUBECTL get pods -n $NAMESPACE -l app=rag-api
    
    # Check services
    log_info "Checking services..."
    $KUBECTL get svc -n $NAMESPACE
    
    # Get external IP
    if [ "$($KUBECTL get svc rag-api-service -n $NAMESPACE -o jsonpath='{.spec.type}')" = "LoadBalancer" ]; then
        log_info "Waiting for external IP..."
        while [ -z "$($KUBECTL get svc rag-api-service -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].ip}')" ]; do
            sleep 5
            log_info "Waiting for external IP..."
        done
        
        EXTERNAL_IP=$($KUBECTL get svc rag-api-service -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
        log_info "RAG API is available at: http://$EXTERNAL_IP"
        
        # Test the API
        log_info "Testing API..."
        sleep 10
        curl -X POST http://$EXTERNAL_IP/query \
            -H "Content-Type: application/json" \
            -d '{"query": "test"}' \
            --connect-timeout 30 \
            --max-time 60 \
            || log_warn "API test failed or timed out"
    else
        log_info "Service type is not LoadBalancer. Check service manually:"
        $KUBECTL get svc rag-api-service -n $NAMESPACE
    fi
}

# Show deployment status
show_status() {
    log_info "Deployment status:"
    $KUBECTL get pods -n $NAMESPACE -l app=rag-api
    $KUBECTL get svc -n $NAMESPACE
    $KUBECTL get pvc -n $NAMESPACE
    $KUBECTL get secrets -n $NAMESPACE
}

# Main deployment function
deploy() {
    log_info "Starting RAG API deployment to Kubernetes..."
    
    # Check prerequisites
    check_prerequisites
    
    # Create namespace
    create_namespace
    
    # Build and push image if registry is provided
    if [ -n "$REGISTRY_URL" ]; then
        build_and_push_image
    fi
    
    # Install or upgrade Helm chart
    install_or_upgrade_chart
    
    # Verify deployment
    verify_deployment
    
    # Show status
    show_status
    
    log_info "Deployment completed successfully!"
}

# Cleanup function
cleanup() {
    log_warn "Cleaning up deployment..."
    $HELM uninstall $RELEASE_NAME -n $NAMESPACE || true
    $KUBECTL delete namespace $NAMESPACE --grace-period=0 --force || true
    log_info "Cleanup completed."
}

# Main script execution
case "${1:-deploy}" in
    deploy)
        deploy
        ;;
    cleanup)
        cleanup
        ;;
    status)
        show_status
        ;;
    verify)
        verify_deployment
        ;;
    *)
        echo "Usage: $0 {deploy|cleanup|status|verify}"
        echo ""
        echo "deploy   - Deploy the RAG API (default)"
        echo "cleanup  - Remove the deployment"
        echo "status   - Show deployment status"
        echo "verify   - Verify the deployment"
        exit 1
        ;;
esac