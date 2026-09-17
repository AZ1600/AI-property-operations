@description('Azure Container Registry name')
param acrName string

@description('Key Vault name')
param keyVaultName string

@description('Container App name')
param containerAppName string

@description('Principal ID of the ACR pull managed identity')
param acrPullPrincipalId string

@description('Principal ID of the runtime managed identity')
param runtimePrincipalId string

@description('Object ID of the GitHub Actions OIDC service principal')
param githubActionsPrincipalId string


// ---------------------------------------------------------
// Existing role-assignment resource names
//
// These GUIDs already exist in Azure. We preserve them so
// Bicep adopts the assignments instead of attempting to
// create duplicates.
// ---------------------------------------------------------

param acrPullAssignmentName string = '53c3c19e-d037-41f3-87bc-6629f331c481'

param keyVaultRoleAssignmentName string = '1fd1e9b4-b4ee-41f3-922c-837e23d22a3b'

param acrPushAssignmentName string = 'b613d5e9-5c03-4f27-9525-4b3ed6e5d4c0'

param containerAppsContributorAssignmentName string = 'bbf2b323-38a2-42d6-adfb-d9e1685e4f82'


// ---------------------------------------------------------
// Existing resources used as RBAC scopes
// ---------------------------------------------------------

resource acr 'Microsoft.ContainerRegistry/registries@2023-01-01-preview' existing = {
  name: acrName
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

resource containerApp 'Microsoft.App/containerApps@2024-03-01' existing = {
  name: containerAppName
}


// ---------------------------------------------------------
// Built-in role definition IDs
// ---------------------------------------------------------

var acrPullRoleDefinitionId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '7f951dda-4ed3-4680-a7ca-43fe172d538d'
)

var acrPushRoleDefinitionId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '8311e382-0749-4cb8-b61a-304f252e45ec'
)

var keyVaultSecretsUserRoleDefinitionId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '4633458b-17de-408a-b874-0445c86b69e6'
)

var containerAppsContributorRoleDefinitionId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '358470bc-b998-42bd-ab17-a7e34c199c0f'
)


// ---------------------------------------------------------
// Container App identity -> ACR
//
// Allows the Container App to pull its container image.
// ---------------------------------------------------------

resource acrPullRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: acrPullAssignmentName
  scope: acr

  properties: {
    principalId: acrPullPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: acrPullRoleDefinitionId
  }
}


// ---------------------------------------------------------
// Runtime identity -> Key Vault
//
// Allows the application to retrieve secret values.
// ---------------------------------------------------------

resource keyVaultSecretsUserRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: keyVaultRoleAssignmentName
  scope: keyVault

  properties: {
    principalId: runtimePrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: keyVaultSecretsUserRoleDefinitionId
  }
}


// ---------------------------------------------------------
// GitHub Actions OIDC -> ACR
//
// Allows CI/CD to push new container images.
// ---------------------------------------------------------

resource acrPushRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: acrPushAssignmentName
  scope: acr

  properties: {
    principalId: githubActionsPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: acrPushRoleDefinitionId
  }
}


// ---------------------------------------------------------
// GitHub Actions OIDC -> Container App
//
// Allows CI/CD to deploy new revisions.
// ---------------------------------------------------------

resource containerAppsContributorRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: containerAppsContributorAssignmentName
  scope: containerApp

  properties: {
    principalId: githubActionsPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: containerAppsContributorRoleDefinitionId
  }
}


// ---------------------------------------------------------
// Outputs
// ---------------------------------------------------------

output acrPullRoleAssignmentId string = acrPullRoleAssignment.id

output keyVaultSecretsUserRoleAssignmentId string = keyVaultSecretsUserRoleAssignment.id

output acrPushRoleAssignmentId string = acrPushRoleAssignment.id

output containerAppsContributorRoleAssignmentId string = containerAppsContributorRoleAssignment.id