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

@description('PostgreSQL Flexible Server name')
param postgresServerName string = 'az1600-propertyops-pg-31328'

@description('PropertyOps PostgreSQL database name')
param postgresDatabaseName string = 'propertyops'

@description('Current Container App outbound IP allowed through PostgreSQL firewall')
param containerAppOutboundIp string = '74.177.140.229'

@description('Container image currently deployed by CI/CD')
param containerImage string

@description('Triage operating mode')
param triageMode string = 'rules'

@description('Object ID of the GitHub Actions OIDC service principal')
param githubActionsPrincipalId string

@secure()
@description('Existing Application Insights connection string Container App secret')
param appInsightsConnectionStringSecret string

@secure()
@description('Existing Microsoft authentication provider secret')
param microsoftProviderAuthenticationSecret string


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
// PostgreSQL
// ---------------------------------------------------------

module postgres './modules/postgres.bicep' = {
  name: 'propertyops-postgres'

  params: {
    location: location
    postgresServerName: postgresServerName
    databaseName: postgresDatabaseName
    containerAppOutboundIp: containerAppOutboundIp
  }
}


// ---------------------------------------------------------
// Container App
// ---------------------------------------------------------

module containerApp './modules/container-app.bicep' = {
  name: 'propertyops-container-app'

  params: {
    location: location
    containerAppName: containerAppName

    environmentId: containerEnvironment.outputs.containerEnvironmentId

    acrLoginServer: '${acrName}${environment().suffixes.acrLoginServer}'

    acrPullIdentityId: identities.outputs.acrPullIdentityId
    runtimeIdentityId: identities.outputs.runtimeIdentityId

    keyVaultUri: 'https://${keyVaultName}${environment().suffixes.keyvaultDns}/'

    containerImage: containerImage
    triageMode: triageMode

    appInsightsConnectionStringSecret: appInsightsConnectionStringSecret

    microsoftProviderAuthenticationSecret: microsoftProviderAuthenticationSecret
  }
}


// ---------------------------------------------------------
// RBAC
// ---------------------------------------------------------

module rbac './modules/rbac.bicep' = {
  name: 'propertyops-rbac'

  params: {
    acrName: acrName
    keyVaultName: keyVaultName
    containerAppName: containerAppName

    acrPullPrincipalId: identities.outputs.acrPullPrincipalId
    runtimePrincipalId: identities.outputs.runtimePrincipalId

    githubActionsPrincipalId: githubActionsPrincipalId
  }

  dependsOn: [
    acr
    keyVault
    containerApp
  ]
}


// ---------------------------------------------------------
// Outputs
// ---------------------------------------------------------

// Container App

output containerAppId string = containerApp.outputs.containerAppId

output containerAppFqdn string = containerApp.outputs.containerAppFqdn

output authConfigId string = containerApp.outputs.authConfigId


// Container Apps Environment

output containerEnvironmentId string = containerEnvironment.outputs.containerEnvironmentId


// Azure Container Registry

output acrId string = acr.outputs.acrId

output acrLoginServer string = acr.outputs.acrLoginServer


// Managed identities

output acrPullIdentityId string = identities.outputs.acrPullIdentityId

output acrPullPrincipalId string = identities.outputs.acrPullPrincipalId

output runtimeIdentityId string = identities.outputs.runtimeIdentityId

output runtimePrincipalId string = identities.outputs.runtimePrincipalId


// Key Vault

output keyVaultId string = keyVault.outputs.keyVaultId

output keyVaultUri string = keyVault.outputs.keyVaultUri


// Monitoring

output logAnalyticsId string = monitoring.outputs.logAnalyticsId

output appInsightsId string = monitoring.outputs.appInsightsId


// PostgreSQL

output postgresServerId string = postgres.outputs.postgresServerId

output postgresFqdn string = postgres.outputs.fqdn

output postgresDatabaseName string = postgres.outputs.databaseName


// RBAC

output acrPullRoleAssignmentId string = rbac.outputs.acrPullRoleAssignmentId

output keyVaultSecretsUserRoleAssignmentId string = rbac.outputs.keyVaultSecretsUserRoleAssignmentId

output acrPushRoleAssignmentId string = rbac.outputs.acrPushRoleAssignmentId

output containerAppsContributorRoleAssignmentId string = rbac.outputs.containerAppsContributorRoleAssignmentId