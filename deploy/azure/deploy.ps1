<#
.SYNOPSIS
    Deploys the RAG API to Azure Container Apps or App Service
.DESCRIPTION
    This script deploys the RAG API to Azure Container Apps using Bicep templates
    or Azure App Service using ARM templates.
.PARAMETER ResourceGroupName
    The name of the resource group to deploy to
.PARAMETER Location
    The Azure location to deploy to
.PARAMETER DeploymentType
    The deployment type - 'container-apps' or 'app-service'
.PARAMETER ContainerAppName
    The name for the Container App
.PARAMETER AppServiceName
    The name for the App Service
.PARAMETER GroqApiKey
    The Groq API key
.PARAMETER LangSmithApiKey
    The LangSmith API key
.PARAMETER Sku
    The SKU for App Service (only used when deployment type is 'app-service')
.PARAMETER ReplicaCount
    The number of replicas for Container App (only used when deployment type is 'container-apps')
.PARAMETER CpuCoreCount
    The CPU core count for Container App (only used when deployment type is 'container-apps')
.PARAMETER MemoryInGB
    The memory in GB for Container App (only used when deployment type is 'container-apps')
.EXAMPLE
    .\deploy.ps1 -ResourceGroupName "rag-api-rg" -Location "East US" -DeploymentType "container-apps" -GroqApiKey "your-groq-key" -LangSmithApiKey "your-langsmith-key"
.EXAMPLE
    .\deploy.ps1 -ResourceGroupName "rag-api-rg" -Location "West US" -DeploymentType "app-service" -AppServiceName "rag-api-app" -GroqApiKey "your-groq-key" -LangSmithApiKey "your-langsmith-key" -Sku "B2"
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroupName,
    
    [Parameter(Mandatory=$true)]
    [string]$Location,
    
    [Parameter(Mandatory=$true)]
    [ValidateSet("container-apps", "app-service")]
    [string]$DeploymentType,
    
    [Parameter(Mandatory=$false)]
    [string]$ContainerAppName,
    
    [Parameter(Mandatory=$false)]
    [string]$AppServiceName,
    
    [Parameter(Mandatory=$true)]
    [string]$GroqApiKey,
    
    [Parameter(Mandatory=$true)]
    [string]$LangSmithApiKey,
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("B1", "B2", "B3", "S1", "S2", "S3", "P1V2", "P2V2", "P3V2")]
    [string]$Sku = "B1",
    
    [Parameter(Mandatory=$false)]
    [int]$ReplicaCount = 1,
    
    [Parameter(Mandatory=$false)]
    [double]$CpuCoreCount = 0.25,
    
    [Parameter(Mandatory=$false)]
    [double]$MemoryInGB = 0.5
)

# Check if Azure CLI is installed
if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Error "Azure CLI is not installed. Please install Azure CLI first."
    exit 1
}

# Check if logged in to Azure
try {
    az account show --output json | ConvertFrom-Json
} catch {
    Write-Host "Not logged in to Azure. Please run 'az login' first."
    exit 1
}

# Create resource group if it doesn't exist
Write-Host "Creating resource group: $ResourceGroupName"
az group create --name $ResourceGroupName --location $Location

# Build the container image
Write-Host "Building Docker image..."
docker build -t rag-api:latest .

# Push to Azure Container Registry
Write-Host "Pushing image to Azure Container Registry..."
$acrName = "ragacr${uniqueString}"
az acr create --name $acrName --resource-group $ResourceGroupName --location $Location --sku Basic
az acr login --name $acrName
docker tag rag-api:latest ${acrName}.azurecr.io/rag-api:latest
docker push ${acrName}.azurecr.io/rag-api:latest

if ($DeploymentType -eq "container-apps") {
    # Deploy to Azure Container Apps
    Write-Host "Deploying to Azure Container Apps..."
    
    # Create Container App Environment
    $envName = "rag-api-${uniqueString}-env"
    az containerapp env create --name $envName --resource-group $ResourceGroupName --location $Location
    
    # Deploy Container App
    $containerAppName = if ($ContainerAppName) { $ContainerAppName } else { "rag-api-${uniqueString}" }
    
    az deployment group create --resource-group $ResourceGroupName `
        --template-file main.bicep `
        --parameters `
            containerAppName=$containerAppName `
            groqApiKey=$GroqApiKey `
            langsmithApiKey=$LangSmithApiKey `
            replicaCount=$ReplicaCount `
            cpuCoreCount=$CpuCoreCount `
            memoryInGB=$MemoryInGB `
            containerImage="${acrName}.azurecr.io/rag-api:latest"
    
    # Get the Container App URL
    $appUrl = az deployment group show --resource-group $ResourceGroupName --name container-apps-deployment --query properties.outputs.containerAppHttpsUrl.value --output tsv
    Write-Host "Container App deployed successfully at: $appUrl"
} else {
    # Deploy to Azure App Service
    Write-Host "Deploying to Azure App Service..."
    
    $appServiceName = if ($AppServiceName) { $AppServiceName } else { "rag-api-${uniqueString}" }
    
    az deployment group create --resource-group $ResourceGroupName `
        --template-file azuredeploy.json `
        --parameters `
            appName=$appServiceName `
            sku=$Sku `
            dockerImage="${acrName}.azurecr.io/rag-api:latest" `
            groqApiKey=$GroqApiKey `
            langsmithApiKey=$LangSmithApiKey
    
    # Get the App Service URL
    $appUrl = az webapp show --resource-group $ResourceGroupName --name $appServiceName --query defaultHostName --output tsv
    Write-Host "App Service deployed successfully at: https://$appUrl"
}

# Clean up temporary resources
Write-Host "Cleaning up temporary resources..."
az acr delete --name $acrName --resource-group $ResourceGroupName --yes

Write-Host "Deployment completed successfully!"