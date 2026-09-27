@description('Azure region for PropertyOps networking.')
param location string

@description('PropertyOps virtual network name.')
param vnetName string = 'vnet-propertyops-dev'

@description('PropertyOps virtual network address space.')
param vnetAddressPrefix string = '10.30.0.0/16'

@description('Dedicated subnet for a future VNet-integrated Container Apps Environment.')
param containerAppsSubnetName string = 'snet-containerapps'

@description('Address range for the future Container Apps Environment.')
param containerAppsSubnetPrefix string = '10.30.0.0/24'

@description('Subnet used by Azure Private Endpoints.')
param privateEndpointSubnetName string = 'snet-private-endpoints'

@description('Address range reserved for private endpoints.')
param privateEndpointSubnetPrefix string = '10.30.1.0/24'

resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: vnetName
  location: location

  tags: {
    Project: 'PropertyOps'
    Environment: 'dev'
    ManagedBy: 'Bicep'
  }

  properties: {
    addressSpace: {
      addressPrefixes: [
        vnetAddressPrefix
      ]
    }

    subnets: [
      {
        name: containerAppsSubnetName
        properties: {
          addressPrefix: containerAppsSubnetPrefix

          delegations: [
            {
              name: 'container-apps-environment'
              properties: {
                serviceName: 'Microsoft.App/environments'
              }
            }
          ]
        }
      }

      {
        name: privateEndpointSubnetName
        properties: {
          addressPrefix: privateEndpointSubnetPrefix
          privateEndpointNetworkPolicies: 'Disabled'
        }
      }
    ]
  }
}

output vnetId string = vnet.id
output vnetName string = vnet.name

output containerAppsSubnetId string = resourceId(
  'Microsoft.Network/virtualNetworks/subnets',
  vnet.name,
  containerAppsSubnetName
)

output privateEndpointSubnetId string = resourceId(
  'Microsoft.Network/virtualNetworks/subnets',
  vnet.name,
  privateEndpointSubnetName
)