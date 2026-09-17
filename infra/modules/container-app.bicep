@description('Azure region for the Container App')
param location string

@description('Container App name')
param containerAppName string

@description('Container Apps Environment resource ID')
param environmentId string

@description('ACR login server')
param acrLoginServer string

@description('Managed identity used to pull images from ACR')
param acrPullIdentityId string

@description('Runtime managed identity')
param runtimeIdentityId string

@description('Key Vault URI')
param keyVaultUri string

@description('Container image to deploy')
param containerImage string

@description('Triage operating mode')
param triageMode string = 'rules'

@secure()
@description('Existing Application Insights connection string Container App secret')
param appInsightsConnectionStringSecret string

@secure()
@description('Existing Microsoft authentication provider secret')
param microsoftProviderAuthenticationSecret string


resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: containerAppName
  location: location

  identity: {
    type: 'UserAssigned'

    userAssignedIdentities: {
      '${acrPullIdentityId}': {}
      '${runtimeIdentityId}': {}
    }
  }

  properties: {
    environmentId: environmentId

    configuration: {
      activeRevisionsMode: 'Single'
      maxInactiveRevisions: 100

      ingress: {
        external: true
        targetPort: 8000
        exposedPort: 0
        transport: 'Auto'
        allowInsecure: false

        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }

      registries: [
        {
          server: acrLoginServer
          identity: acrPullIdentityId
        }
      ]

      secrets: [
        {
          name: 'appinsights-connection-string'
          value: appInsightsConnectionStringSecret
        }

        {
          name: 'database-url'
          keyVaultUrl: '${keyVaultUri}secrets/database-url'
          identity: runtimeIdentityId
        }

        {
          name: 'microsoft-provider-authentication-secret'
          value: microsoftProviderAuthenticationSecret
        }
      ]
    }

    template: {
      containers: [
        {
          name: containerAppName
          image: containerImage

          env: [
            {
              name: 'TRIAGE_MODE'
              value: triageMode
            }

            {
              name: 'DATABASE_URL'
              secretRef: 'database-url'
            }

            {
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              secretRef: 'appinsights-connection-string'
            }
          ]

          resources: {
            cpu: any('0.25')
            memory: '0.5Gi'
          }
        }
      ]

      scale: {
        minReplicas: 0
        maxReplicas: 1
      }
    }
  }
}


// ---------------------------------------------------------
// Existing Entra authentication configuration
//
// Authentication already works, so we intentionally leave
// the auth child resource untouched during this adoption.
// ---------------------------------------------------------

resource authConfig 'Microsoft.App/containerApps/authConfigs@2024-03-01' existing = {
  parent: containerApp
  name: 'current'
}


// ---------------------------------------------------------
// Outputs
// ---------------------------------------------------------

output containerAppId string = containerApp.id

output containerAppName string = containerApp.name

output containerAppFqdn string = containerApp.properties.configuration.ingress.fqdn

output authConfigId string = authConfig.id