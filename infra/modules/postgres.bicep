@description('Azure region for PostgreSQL')
param location string

@description('PostgreSQL Flexible Server name')
param postgresServerName string

@description('Application database name')
param databaseName string = 'propertyops'

@description('Current Container App outbound IP allowed by PostgreSQL firewall')
param containerAppOutboundIp string = '74.177.140.229'


resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: postgresServerName
  location: location

  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }

  properties: {
    administratorLogin: 'propertyopsadmin'

    version: '16'

    availabilityZone: '3'

    authConfig: {
      activeDirectoryAuth: 'Disabled'
      passwordAuth: 'Enabled'
    }

    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }

    highAvailability: {
      mode: 'Disabled'
    }

    maintenanceWindow: {
      customWindow: 'Disabled'
      dayOfWeek: 0
      startHour: 0
      startMinute: 0
    }

    network: {
      publicNetworkAccess: 'Enabled'
    }

    storage: {
      storageSizeGB: 32
      autoGrow: 'Disabled'
      iops: 120
      tier: 'P4'
      type: 'Premium_LRS'
    }

    dataEncryption: {
      type: 'SystemManaged'
    }
    replica: {
      role: 'Primary'
    }

    replicationRole: 'Primary'
  }
}


// ---------------------------------------------------------
// PropertyOps application database
// ---------------------------------------------------------

resource propertyOpsDatabase 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: postgresServer
  name: databaseName

  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}


// ---------------------------------------------------------
// Current firewall rule
//
// This IP is intentionally preserved during IaC adoption.
// Later, stable outbound networking will replace this.
// ---------------------------------------------------------

resource containerAppFirewallRule 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2024-08-01' = {
  parent: postgresServer
  name: 'allow-propertyops-containerapp'

  properties: {
    startIpAddress: containerAppOutboundIp
    endIpAddress: containerAppOutboundIp
  }
}


// ---------------------------------------------------------
// Outputs
// ---------------------------------------------------------

output postgresServerId string = postgresServer.id

output postgresServerName string = postgresServer.name

output databaseName string = propertyOpsDatabase.name

output fqdn string = postgresServer.properties.fullyQualifiedDomainName