targetScope = 'resourceGroup'


// ---------------------------------------------------------
// Parameters
// ---------------------------------------------------------

@description('Azure region for PropertyOps resources')
param location string = 'uksouth'

@description('Container App name')
param containerAppName string = 'propertyops-ai-agent'

@description('Container Apps Environment name')
param containerEnvironmentName string = 'cae-propertyops-dev'

@description('Azure Container Registry name')
param acrName string = 'az1600propertyops22764'

@description('Managed identity used to pull images from ACR')
param acrPullIdentityName string = 'id-propertyops-acr-pull'

@description('Runtime managed identity')
param runtimeIdentityName string = 'id-propertyops-runtime'

@description('Key Vault name')
param keyVaultName string = 'kv-propertyops-23303'

@description('Log Analytics workspace name')
param logAnalyticsName string = 'law-propertyops-dev'

@description('Application Insights name')
param appInsightsName string = 'appi-propertyops-dev'


// ---------------------------------------------------------
// Managed identities
// ---------------------------------------------------------

module identities './modules/identities.bicep' = {
  name: 'propertyops-identities'

  params: {
    location: location
    acrPullIdentityName: acrPullIdentityName
    runtimeIdentityName: runtimeIdentityName
  }
}


// ---------------------------------------------------------
// Azure Container Registry
// ---------------------------------------------------------

module acr './modules/acr.bicep' = {
  name: 'propertyops-acr'

  params: {
    location: location
    acrName: acrName
  }
}


// ---------------------------------------------------------
// Monitoring
// ---------------------------------------------------------

module monitoring './modules/monitoring.bicep' = {
  name: 'propertyops-monitoring'

  params: {
    location: location
    logAnalyticsName: logAnalyticsName
    appInsightsName: appInsightsName
  }
}


// ---------------------------------------------------------
// Container Apps Environment
// ---------------------------------------------------------

module containerEnvironment './modules/container-environment.bicep' = {
  name: 'propertyops-container-environment'

  params: {
    location: location
    containerEnvironmentName: containerEnvironmentName
  }
}


// ---------------------------------------------------------
// Existing infrastructure
//
// These remain references only for now.
// ---------------------------------------------------------

resource containerApp 'Microsoft.App/containerApps@2024-03-01' existing = {
  name: containerAppName
}

// ---------------------------------------------------------
// Key Vault
// ---------------------------------------------------------

module keyVault './modules/key-vault.bicep' = {
  name: 'propertyops-key-vault'

  params: {
    location: location
    keyVaultName: keyVaultName
  }
}

// ---------------------------------------------------------
// Outputs
// ---------------------------------------------------------

// Container Apps

output containerAppId string = containerApp.id

output containerEnvironmentId string = containerEnvironment.outputs.containerEnvironmentId


// ACR

output acrId string = acr.outputs.acrId

output acrLoginServer string = acr.outputs.acrLoginServer


// Managed identities

output acrPullIdentityId string = identities.outputs.acrPullIdentityId

output acrPullPrincipalId string = identities.outputs.acrPullPrincipalId

output runtimeIdentityId string = identities.outputs.runtimeIdentityId

output runtimePrincipalId string = identities.outputs.runtimePrincipalId


// Key Vault
output keyVaultId string = keyVault.outputs.keyVaultId


// Monitoring

output logAnalyticsId string = monitoring.outputs.logAnalyticsId

output appInsightsId string = monitoring.outputs.appInsightsId