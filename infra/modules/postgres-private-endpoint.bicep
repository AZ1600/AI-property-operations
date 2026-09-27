@description('Azure region for the PostgreSQL private endpoint.')
param location string

@description('Resource ID of the existing PostgreSQL Flexible Server.')
param postgresServerId string

@description('Resource ID of the subnet reserved for private endpoints.')
param privateEndpointSubnetId string

@description('Resource ID of the PostgreSQL private DNS zone.')
param postgresPrivateDnsZoneId string

@description('Deployment environment.')
param environment string = 'dev'

var privateEndpointName = 'pe-propertyops-postgres'


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
        name: 'propertyops-postgres-connection'

        properties: {
          privateLinkServiceId: postgresServerId

          groupIds: [
            'postgresqlServer'
          ]

          requestMessage: 'Private PostgreSQL connectivity for PropertyOps.'
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
        name: 'postgres-private-dns'

        properties: {
          privateDnsZoneId: postgresPrivateDnsZoneId
        }
      }
    ]
  }
}


output privateEndpointId string = privateEndpoint.id
output privateEndpointName string = privateEndpoint.name