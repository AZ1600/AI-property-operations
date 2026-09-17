@description('Azure region for the container registry')
param location string

@description('Azure Container Registry name')
param acrName string


resource acr 'Microsoft.ContainerRegistry/registries@2023-01-01-preview' = {
  name: acrName
  location: location

  sku: {
    name: 'Basic'
  }

  properties: {
    adminUserEnabled: false

    // Existing registry does not allow anonymous pulls.
    anonymousPullEnabled: false

    dataEndpointEnabled: false

    // Existing registry uses Microsoft-managed encryption,
    // not a customer-managed key.
    encryption: {
      status: 'disabled'
    }

    networkRuleBypassOptions: 'AzureServices'

    policies: {
      // Preserve the registry's current ARM audience
      // authentication policy.
      azureADAuthenticationAsArmPolicy: {
        status: 'enabled'
      }
    }

    publicNetworkAccess: 'Enabled'
    zoneRedundancy: 'Disabled'
  }
}


output acrId string = acr.id

output acrName string = acr.name

output acrLoginServer string = acr.properties.loginServer