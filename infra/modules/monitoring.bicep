@description('Azure region for monitoring resources')
param location string

@description('Log Analytics workspace name')
param logAnalyticsName string

@description('Application Insights component name')
param appInsightsName string


// ---------------------------------------------------------
// Log Analytics Workspace
// ---------------------------------------------------------

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: logAnalyticsName
  location: location

  properties: {
    retentionInDays: 30

    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'

    sku: {
      name: 'PerGB2018'
    }
  }
}


// ---------------------------------------------------------
// Application Insights
//
// The workspace link is derived from the Log Analytics
// resource instead of hardcoding the subscription/resource ID.
// ---------------------------------------------------------

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'

  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
    RetentionInDays: 90

    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}


// ---------------------------------------------------------
// Outputs
// ---------------------------------------------------------

output logAnalyticsId string = logAnalytics.id

output logAnalyticsName string = logAnalytics.name

output appInsightsId string = appInsights.id

output appInsightsName string = appInsights.name