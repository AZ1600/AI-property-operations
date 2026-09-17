@description('Azure region for the managed identities')
param location string

@description('Managed identity used by Container Apps to pull images from ACR')
param acrPullIdentityName string

@description('Managed identity used by the application at runtime')
param runtimeIdentityName string


resource acrPullIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: acrPullIdentityName
  location: location
}


resource runtimeIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: runtimeIdentityName
  location: location
}


// ---------------------------------------------------------
// Outputs
// ---------------------------------------------------------

output acrPullIdentityId string = acrPullIdentity.id

output acrPullPrincipalId string = acrPullIdentity.properties.principalId

output runtimeIdentityId string = runtimeIdentity.id

output runtimePrincipalId string = runtimeIdentity.properties.principalId