@description('Resource ID of the PropertyOps virtual network.')
param vnetId string

@description('Deployment environment.')
param environment string = 'dev'

var postgresPrivateDnsZoneName = 'privatelink.postgres.database.azure.com'
var keyVaultPrivateDnsZoneName = 'privatelink.vaultcore.azure.net'
var acrPrivateDnsZoneName = 'privatelink.azurecr.io'


// ---------------------------------------------------------
// PostgreSQL Private DNS
// ---------------------------------------------------------

resource postgresPrivateDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: postgresPrivateDnsZoneName
  location: 'global'

  tags: {
    Project: 'PropertyOps'
    Environment: environment
    ManagedBy: 'Bicep'
  }
}

resource postgresVnetLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: postgresPrivateDnsZone
  name: 'link-propertyops-${environment}-postgres'
  location: 'global'

  properties: {
    registrationEnabled: false

    virtualNetwork: {
      id: vnetId
    }
  }
}


// ---------------------------------------------------------
// Key Vault Private DNS
// ---------------------------------------------------------

resource keyVaultPrivateDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: keyVaultPrivateDnsZoneName
  location: 'global'

  tags: {
    Project: 'PropertyOps'
    Environment: environment
    ManagedBy: 'Bicep'
  }
}

resource keyVaultVnetLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: keyVaultPrivateDnsZone
  name: 'link-propertyops-${environment}-keyvault'
  location: 'global'

  properties: {
    registrationEnabled: false

    virtualNetwork: {
      id: vnetId
    }
  }
}


// ---------------------------------------------------------
// Azure Container Registry Private DNS
// ---------------------------------------------------------

resource acrPrivateDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: acrPrivateDnsZoneName
  location: 'global'

  tags: {
    Project: 'PropertyOps'
    Environment: environment
    ManagedBy: 'Bicep'
  }
}

resource acrVnetLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: acrPrivateDnsZone
  name: 'link-propertyops-${environment}-acr'
  location: 'global'

  properties: {
    registrationEnabled: false

    virtualNetwork: {
      id: vnetId
    }
  }
}


// ---------------------------------------------------------
// Outputs
// ---------------------------------------------------------

output postgresPrivateDnsZoneId string = postgresPrivateDnsZone.id
output postgresPrivateDnsZoneName string = postgresPrivateDnsZone.name

output keyVaultPrivateDnsZoneId string = keyVaultPrivateDnsZone.id
output keyVaultPrivateDnsZoneName string = keyVaultPrivateDnsZone.name

output acrPrivateDnsZoneId string = acrPrivateDnsZone.id
output acrPrivateDnsZoneName string = acrPrivateDnsZone.name