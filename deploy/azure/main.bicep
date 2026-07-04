@description('Location for all resources')
param location string = resourceGroup().location

@description('Name for the Container App')
param containerAppName string = 'rag-api-${uniqueString(resourceGroup().id)}'

@description('API key for Groq')
param groqApiKey string = ''

@description('API key for LangSmith')
param langsmithApiKey string = ''

@description('Number of replicas for the Container App')
param replicaCount int = 1

@description('CPU cores for the Container App')
param cpuCoreCount double = 0.25

@description('Memory in GB for the Container App')
param memoryInGB double = 0.5

@description('Image for the RAG API')
param containerImage string = 'rag-api:latest'

@description('Environment variables for the Container App')
@allowed([
  'Development'
  'Staging'
  'Production'
])
param environment string = 'Development'

@description('Enable ingress for the Container App')
param enableIngress bool = true

@description('Ingress type for the Container App')
@allowed([
  'standard'
  'internal'
])
param ingressType string = 'standard'

@description('Allow insecure traffic for the Container App')
param allowInsecure bool = false

@description('Target port for the Container App')
param targetPort int = 8000

@description('Secrets for the Container App')
param secrets array = [
  {
    name: 'groq-api-key'
    value: groqApiKey
  }
  {
    name: 'langsmith-api-key'
    value: langsmithApiKey
  }
]

// Container App Environment
resource containerAppEnvironment 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: 'rag-api-${uniqueString(resourceGroup().id)}-env'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
    }
  }
}

// Log Analytics Workspace
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: 'rag-api-${uniqueString(resourceGroup().id)}-logs'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
  }
}

// Container App
resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: containerAppName
  location: location
  properties: {
    managedEnvironmentId: containerAppEnvironment.id
    configuration: {
      secrets: secrets
      ingress: enableIngress ? {
        external: ingressType == 'standard'
        targetPort: targetPort
        allowInsecure: allowInsecure
        transport: 'auto'
      } : null
      dapr: {
        enabled: false
      }
      registries: []
    }
    template: {
      containers: [
        {
          name: 'rag-api'
          image: containerImage
          resources: {
            cpu: cpuCoreCount
            memory: '${memoryInGB}Gi'
          }
          env: [
            {
              name: 'RAG_DATA_DIR'
              value: '/app/data'
            }
            {
              name: 'RAG_PERSIST_DIR'
              value: '/app/faiss_store'
            }
            {
              name: 'RAG_EMBEDDING_MODEL'
              value: 'all-MiniLM-L6-v2'
            }
            {
              name: 'RAG_LLM_MODEL'
              value: 'llama-3.3-70b-versatile'
            }
            {
              name: 'RAG_DEFAULT_TOP_K'
              value: '5'
            }
            {
              name: 'RAG_AUTO_BUILD_INDEX'
              value: 'true'
            }
            {
              name: 'GROQ_API_KEY'
              secretRef: 'groq-api-key'
            }
            {
              name: 'LANGSMITH_API_KEY'
              secretRef: 'langsmith-api-key'
            }
            {
              name: 'ENVIRONMENT'
              value: environment
            }
          ]
          volumeMounts: [
            {
              name: 'data-volume'
              mountPath: '/app/data'
            }
            {
              name: 'faiss-volume'
              mountPath: '/app/faiss_store'
            }
          ]
        }
      ]
      volumes: [
        {
          name: 'data-volume'
          storage: {
            class: 'managed'
            accessMode: 'ReadWriteOnce'
            sizeInGb: 5
          }
        }
        {
          name: 'faiss-volume'
          storage: {
            class: 'managed'
            accessMode: 'ReadWriteOnce'
            sizeInGb: 5
          }
        }
      ]
    }
  }
}

// Output the Container App URL
output containerAppUrl string = containerApp.properties.configuration.ingress?.external
output containerAppFqdn string = containerApp.properties.configuration.ingress?.fqdn
output containerAppHttpsUrl string = enableIngress ? 'https://${containerApp.properties.configuration.ingress.fqdn}' : 'http://localhost:${targetPort}'