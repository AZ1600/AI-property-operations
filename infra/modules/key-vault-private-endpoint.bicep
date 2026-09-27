@description('Azure region for the Key Vault private endpoint.')
param location string

@description('Resource ID of the existing Key Vault.')
param keyVaultId string

@description('Resource ID of the subnet reserved for private endpoints.')
param privateEndpointSubnetId string

@description('Resource ID of the Key Vault private DNS zone.')
param keyVaultPrivateDnsZoneId string

@description('Deployment environment.')
param environment string = 'dev'

var privateEndpointName = 'pe-propertyops-keyvault'

resource privateEndpoint 'Microsoft.Network/privateEndpoints@2024-05-01' = {
  name: privateEndpointName
  location: location

  tags: {
    Project: 'PropertyOps'
    Environment: environment
    ManagedBy: 'Bicep'
  }

  properties: {
    subnet: {
      id: privateEndpointSubnetId
    }

    privateLinkServiceConnections: [
      {
        name: 'propertyops-keyvault-connection'

        properties: {
          privateLinkServiceId: keyVaultId

          groupIds: [
            'vault'
          ]

          requestMessage: 'Private Key Vault connectivity for PropertyOps.'
        }
      }
    ]
  }
}

resource privateDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = {
  parent: privateEndpoint
  name: 'default'

  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'keyvault-private-dns'

        properties: {
          privateDnsZoneId: keyVaultPrivateDnsZoneId
        }
      }
    ]
  }
}

output privateEndpointId string = privateEndpoint.id
output privateEndpointName string = privateEndpoint.name