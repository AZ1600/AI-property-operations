@description('Azure region for the Key Vault')
param location string

@description('Key Vault name')
param keyVaultName string


resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location

  properties: {
    tenantId: tenant().tenantId

    sku: {
      family: 'A'
      name: 'standard'
    }

    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 90

    publicNetworkAccess: 'Enabled'
  }
}


// ---------------------------------------------------------
// Outputs
// ---------------------------------------------------------

output keyVaultId string = keyVault.id

output keyVaultName string = keyVault.name

output keyVaultUri string = keyVault.properties.vaultUri