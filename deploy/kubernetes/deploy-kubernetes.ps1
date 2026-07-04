<#
.SYNOPSIS
    Deploys the RAG API to Kubernetes using Helm
.DESCRIPTION
    This script deploys the RAG API to a Kubernetes cluster using Helm charts.
    It can build and push Docker images, install the Helm chart, and verify the deployment.
.PARAMETER Action
    The action to perform: deploy, cleanup, status, verify
.PARAMETER Namespace
    The Kubernetes namespace to use (default: rag-system)
.PARAMETER ReleaseName
    The Helm release name (default: rag-api)
.PARAMETER ChartPath
    The path to the Helm chart (default: ./deploy/kubernetes/helm/rag-chart)
.PARAM RegistryUrl
    The Docker registry URL (optional)
.PARAM GroqApiKey
    The Groq API key (required for deployment)
.PARAM LangSmithApiKey
    The LangSmith API key (required for deployment)
.EXAMPLE
    .\deploy-kubernetes.ps1 -Action deploy -GroqApiKey "your-groq-key" -LangSmithApiKey "your-langsmith-key"
.EXAMPLE
    .\deploy-kubernetes.ps1 -Action status
.EXAMPLE
    .\deploy-kubernetes.ps1 -Action cleanup
#>

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("deploy", "cleanup", "status", "verify")]
    [string]$Action = "deploy",
    
    [Parameter(Mandatory=$false)]
    [string]$Namespace = "rag-system",
    
    [Parameter(Mandatory=$false)]
    [string]$ReleaseName = "rag-api",
    
    [Parameter(Mandatory=$false)]
    [string]$ChartPath = "./deploy/kubernetes/helm/rag-chart",
    
    [Parameter(Mandatory=$false)]
    [string]$RegistryUrl = "",
    
    [Parameter(Mandatory=$true)]
    [string]$GroqApiKey,
    
    [Parameter(Mandatory=$true)]
    [string]$LangSmithApiKey
)

# Configuration
$Kubectl = "kubectl"
$Helm = "helm"

# Functions
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $color = switch ($Level) {
        "INFO" { "Green" }
        "WARN" { "Yellow" }
        "ERROR" { "Red" }
        default { "White" }
    }
    
    Write-Host "[$timestamp] [$Level] $Message" -ForegroundColor $color
}

function Test-Prerequisites {
    Write-Log "Checking prerequisites..."
    
    # Check kubectl
    if (-not (Get-Command $Kubectl -ErrorAction SilentlyContinue)) {
        Write-Log "kubectl is not installed. Please install kubectl first." -Level "ERROR"
        exit 1
    }
    
    # Check helm
    if (-not (Get-Command $Helm -ErrorAction SilentlyContinue)) {
        Write-Log "helm is not installed. Please install helm first." -Level "ERROR"
        exit 1
    }
    
    # Check cluster connectivity
    try {
        & $Kubectl cluster-info | Out-Null
    } catch {
        Write-Log "Cannot connect to Kubernetes cluster. Please check your kubeconfig." -Level "ERROR"
        exit 1
    }
    
    Write-Log "All prerequisites satisfied."
}

function New-Namespace {
    param([string]$NamespaceName)
    
    Write-Log "Creating namespace: $NamespaceName"
    try {
        & $Kubectl create namespace $NamespaceName --dry-run=client -o json | & $Kubectl apply -f - | Out-Null
        Write-Log "Namespace created successfully."
    } catch {
        Write-Log "Failed to create namespace: $($_.Exception.Message)" -Level "ERROR"
        exit 1
    }
}

function Build-Push-Image {
    param([string]$RegistryUrl)
    
    Write-Log "Building Docker image..."
    try {
        docker build -t rag-api:latest .
        
        if ($RegistryUrl) {
            Write-Log "Tagging and pushing image to registry..."
            docker tag rag-api:latest "$RegistryUrl/rag-api:latest"
            docker push "$RegistryUrl/rag-api:latest"
            
            Write-Log "Updating Helm chart values..."
            $chartValues = Get-Content "$ChartPath/values.yaml" -Raw
            $chartValues = $chartValues -replace 'repository: rag-api', "repository: $RegistryUrl/rag-api"
            $chartValues = $chartValues -replace 'registry: ""', "registry: `"$RegistryUrl`""
            $chartValues | Set-Content "$ChartPath/values.yaml" -Force
        }
    } catch {
        Write-Log "Failed to build/push image: $($_.Exception.Message)" -Level "ERROR"
        exit 1
    }
}

function Install-Upgrade-HelmChart {
    param([string]$NamespaceName, [string]$ReleaseName, [string]$GroqApiKey, [string]$LangSmithApiKey)
    
    Write-Log "Installing/upgrading Helm chart..."
    
    if (& $Helm list -n $NamespaceName | Where-Object { $_ -like "*$ReleaseName*" }) {
        Write-Log "Upgrading existing release..."
        & $Helm upgrade $ReleaseName $ChartPath `
            --namespace $NamespaceName `
            --wait `
            --timeout 300s `
            --set secrets.groqApiKey="$GroqApiKey" `
            --set secrets.langsmithApiKey="$LangSmithApiKey"
    } else {
        Write-Log "Installing new release..."
        & $Helm install $ReleaseName $ChartPath `
            --namespace $NamespaceName `
            --wait `
            --timeout 300s `
            --set secrets.groqApiKey="$GroqApiKey" `
            --set secrets.langsmithApiKey="$LangSmithApiKey"
    }
}

function Test-Deployment {
    param([string]$NamespaceName)
    
    Write-Log "Testing deployment..."
    
    # Check pods
    Write-Log "Checking pods..."
    & $Kubectl get pods -n $NamespaceName -l app=rag-api
    
    # Check services
    Write-Log "Checking services..."
    & $Kubectl get svc -n $NamespaceName
    
    # Get external IP
    $serviceType = & $Kubectl get svc rag-api-service -n $NamespaceName -o jsonpath='{.spec.type}'
    if ($serviceType -eq "LoadBalancer") {
        Write-Log "Waiting for external IP..."
        $externalIp = ""
        $maxAttempts = 24
        $attempts = 0
        
        while ([string]::IsNullOrEmpty($externalIp) -and $attempts -lt $maxAttempts) {
            Start-Sleep -Seconds 5
            $externalIp = & $Kubectl get svc rag-api-service -n $NamespaceName -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
            $attempts++
            Write-Log "Waiting for external IP... attempt $attempts/$maxAttempts"
        }
        
        if ($externalIp) {
            Write-Log "RAG API is available at: http://$externalIp"
            
            # Test the API
            Write-Log "Testing API..."
            Start-Sleep -Seconds 10
            
            try {
                $response = Invoke-RestMethod -Uri "http://$externalIp/query" `
                    -Method Post `
                    -ContentType "application/json" `
                    -Body '{"query": "test"}' `
                    -TimeoutSec 30 `
                    -MaximumRedirection 3
                
                Write-Log "API test successful!"
                Write-Log "Response: $($response | ConvertTo-Json -Depth 2)"
            } catch {
                Write-Log "API test failed or timed out: $($_.Exception.Message)" -Level "WARN"
            }
        } else {
            Write-Log "Failed to get external IP after $maxAttempts attempts." -Level "WARN"
        }
    } else {
        Write-Log "Service type is not LoadBalancer. Check service manually:"
        & $Kubectl get svc rag-api-service -n $NamespaceName
    }
}

function Show-Status {
    param([string]$NamespaceName)
    
    Write-Log "Deployment status:"
    & $Kubectl get pods -n $NamespaceName -l app=rag-api
    & $Kubectl get svc -n $NamespaceName
    & $Kubectl get pvc -n $NamespaceName
    & $Kubectl get secrets -n $NamespaceName
}

function Remove-Deployment {
    param([string]$NamespaceName, [string]$ReleaseName)
    
    Write-Log "Removing deployment..."
    try {
        & $Helm uninstall $ReleaseName -n $NamespaceName -ErrorAction SilentlyContinue | Out-Null
        & $Kubectl delete namespace $NamespaceName --grace-period=0 --force -ErrorAction SilentlyContinue | Out-Null
        Write-Log "Deployment removed successfully."
    } catch {
        Write-Log "Error during cleanup: $($_.Exception.Message)" -Level "WARN"
    }
}

# Main script execution
switch ($Action) {
    "deploy" {
        Write-Log "Starting RAG API deployment to Kubernetes..."
        Test-Prerequisites
        New-Namespace $Namespace
        
        if ($RegistryUrl) {
            Build-Push-Image $RegistryUrl
        }
        
        Install-Upgrade-HelmChart $Namespace $ReleaseName $GroqApiKey $LangSmithApiKey
        Test-Deployment $Namespace
        Show-Status $Namespace
        
        Write-Log "Deployment completed successfully!"
    }
    
    "cleanup" {
        Write-Log "Cleaning up deployment..."
        Remove-Deployment $Namespace $ReleaseName
    }
    
    "status" {
        Show-Status $Namespace
    }
    
    "verify" {
        Test-Deployment $Namespace
    }
    
    default {
        Write-Log "Unknown action: $Action" -Level "ERROR"
        exit 1
    }
}