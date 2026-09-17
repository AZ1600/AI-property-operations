@description('Azure region for the Container Apps Environment')
param location string

@description('Container Apps Environment name')
param containerEnvironmentName string


resource containerEnvironment 'Microsoft.App/managedEnvironments@2025-07-01' = {
  name: containerEnvironmentName
  location: location

  properties: {
    publicNetworkAccess: 'Enabled'
    zoneRedundant: false

    peerAuthentication: {
      mtls: {
        enabled: false
      }
    }

    peerTrafficConfiguration: {
      encryption: {
        enabled: false
      }
    }
  }
}


// ---------------------------------------------------------
// Outputs
// ---------------------------------------------------------

output containerEnvironmentId string = containerEnvironment.id

output containerEnvironmentName string = containerEnvironment.name