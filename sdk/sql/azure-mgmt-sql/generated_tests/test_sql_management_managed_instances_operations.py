# coding=utf-8
# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is regenerated.
# --------------------------------------------------------------------------
import pytest
from azure.mgmt.sql import SqlManagementClient

from devtools_testutils import AzureMgmtRecordedTestCase, RandomNameResourceGroupPreparer, recorded_by_proxy

AZURE_LOCATION = "eastus"


@pytest.mark.skip("you may need to update the auto-generated test case before run it")
class TestSqlManagementManagedInstancesOperations(AzureMgmtRecordedTestCase):
    def setup_method(self, method):
        self.client = self.create_mgmt_client(SqlManagementClient)

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_managed_instances_list(self, resource_group):
        response = self.client.managed_instances.list(
            api_version="2024-11-01-preview",
        )
        result = [r for r in response]
        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_managed_instances_list_by_instance_pool(self, resource_group):
        response = self.client.managed_instances.list_by_instance_pool(
            resource_group_name=resource_group.name,
            instance_pool_name="str",
            api_version="2024-11-01-preview",
        )
        result = [r for r in response]
        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_managed_instances_list_by_resource_group(self, resource_group):
        response = self.client.managed_instances.list_by_resource_group(
            resource_group_name=resource_group.name,
            api_version="2024-11-01-preview",
        )
        result = [r for r in response]
        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_managed_instances_get(self, resource_group):
        response = self.client.managed_instances.get(
            resource_group_name=resource_group.name,
            managed_instance_name="str",
            api_version="2024-11-01-preview",
        )

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_managed_instances_begin_create_or_update(self, resource_group):
        response = self.client.managed_instances.begin_create_or_update(
            resource_group_name=resource_group.name,
            managed_instance_name="str",
            parameters={
                "location": "str",
                "administratorLogin": "str",
                "administratorLoginPassword": "str",
                "administrators": {
                    "administratorType": "str",
                    "azureADOnlyAuthentication": bool,
                    "login": "str",
                    "principalType": "str",
                    "sid": "str",
                    "tenantId": "str",
                },
                "authenticationMetadata": "str",
                "collation": "str",
                "createTime": "2020-02-20 00:00:00",
                "currentBackupStorageRedundancy": "str",
                "databaseFormat": "str",
                "dnsZone": "str",
                "dnsZonePartner": "str",
                "externalGovernanceStatus": "str",
                "fullyQualifiedDomainName": "str",
                "hybridSecondaryUsage": "str",
                "hybridSecondaryUsageDetected": "str",
                "id": "str",
                "identity": {
                    "principalId": "str",
                    "tenantId": "str",
                    "type": "str",
                    "userAssignedIdentities": {"str": {"clientId": "str", "principalId": "str"}},
                },
                "instancePoolId": "str",
                "isGeneralPurposeV2": bool,
                "keyId": "str",
                "licenseType": "str",
                "maintenanceConfigurationId": "str",
                "managedInstanceCreateMode": "str",
                "memorySizeInGB": 0,
                "minimalTlsVersion": "str",
                "name": "str",
                "pricingModel": "str",
                "primaryUserAssignedIdentityId": "str",
                "privateEndpointConnections": [
                    {
                        "id": "str",
                        "properties": {
                            "privateEndpoint": {"id": "str"},
                            "privateLinkServiceConnectionState": {
                                "description": "str",
                                "status": "str",
                                "actionsRequired": "str",
                            },
                            "provisioningState": "str",
                        },
                    }
                ],
                "provisioningState": "str",
                "proxyOverride": "str",
                "publicDataEndpointEnabled": bool,
                "requestedBackupStorageRedundancy": "str",
                "requestedLogicalAvailabilityZone": "str",
                "restorePointInTime": "2020-02-20 00:00:00",
                "servicePrincipal": {"clientId": "str", "principalId": "str", "tenantId": "str", "type": "str"},
                "sku": {"name": "str", "capacity": 0, "family": "str", "size": "str", "tier": "str"},
                "sourceManagedInstanceId": "str",
                "state": "str",
                "storageIOps": 0,
                "storageSizeInGB": 0,
                "storageThroughputMBps": 0,
                "subnetId": "str",
                "tags": {"str": "str"},
                "timezoneId": "str",
                "type": "str",
                "vCores": 0,
                "virtualClusterId": "str",
                "zoneRedundant": bool,
            },
            api_version="2024-11-01-preview",
        ).result()  # call '.result()' to poll until service return final result

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_managed_instances_begin_delete(self, resource_group):
        response = self.client.managed_instances.begin_delete(
            resource_group_name=resource_group.name,
            managed_instance_name="str",
            api_version="2024-11-01-preview",
        ).result()  # call '.result()' to poll until service return final result

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_managed_instances_begin_update(self, resource_group):
        response = self.client.managed_instances.begin_update(
            resource_group_name=resource_group.name,
            managed_instance_name="str",
            parameters={
                "administratorLogin": "str",
                "administratorLoginPassword": "str",
                "administrators": {
                    "administratorType": "str",
                    "azureADOnlyAuthentication": bool,
                    "login": "str",
                    "principalType": "str",
                    "sid": "str",
                    "tenantId": "str",
                },
                "authenticationMetadata": "str",
                "collation": "str",
                "createTime": "2020-02-20 00:00:00",
                "currentBackupStorageRedundancy": "str",
                "databaseFormat": "str",
                "dnsZone": "str",
                "dnsZonePartner": "str",
                "externalGovernanceStatus": "str",
                "fullyQualifiedDomainName": "str",
                "hybridSecondaryUsage": "str",
                "hybridSecondaryUsageDetected": "str",
                "identity": {
                    "principalId": "str",
                    "tenantId": "str",
                    "type": "str",
                    "userAssignedIdentities": {"str": {"clientId": "str", "principalId": "str"}},
                },
                "instancePoolId": "str",
                "isGeneralPurposeV2": bool,
                "keyId": "str",
                "licenseType": "str",
                "maintenanceConfigurationId": "str",
                "managedInstanceCreateMode": "str",
                "memorySizeInGB": 0,
                "minimalTlsVersion": "str",
                "pricingModel": "str",
                "primaryUserAssignedIdentityId": "str",
                "privateEndpointConnections": [
                    {
                        "id": "str",
                        "properties": {
                            "privateEndpoint": {"id": "str"},
                            "privateLinkServiceConnectionState": {
                                "description": "str",
                                "status": "str",
                                "actionsRequired": "str",
                            },
                            "provisioningState": "str",
                        },
                    }
                ],
                "provisioningState": "str",
                "proxyOverride": "str",
                "publicDataEndpointEnabled": bool,
                "requestedBackupStorageRedundancy": "str",
                "requestedLogicalAvailabilityZone": "str",
                "restorePointInTime": "2020-02-20 00:00:00",
                "servicePrincipal": {"clientId": "str", "principalId": "str", "tenantId": "str", "type": "str"},
                "sku": {"name": "str", "capacity": 0, "family": "str", "size": "str", "tier": "str"},
                "sourceManagedInstanceId": "str",
                "state": "str",
                "storageIOps": 0,
                "storageSizeInGB": 0,
                "storageThroughputMBps": 0,
                "subnetId": "str",
                "tags": {"str": "str"},
                "timezoneId": "str",
                "vCores": 0,
                "virtualClusterId": "str",
                "zoneRedundant": bool,
            },
            api_version="2024-11-01-preview",
        ).result()  # call '.result()' to poll until service return final result

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_managed_instances_begin_failover(self, resource_group):
        response = self.client.managed_instances.begin_failover(
            resource_group_name=resource_group.name,
            managed_instance_name="str",
            api_version="2024-11-01-preview",
        ).result()  # call '.result()' to poll until service return final result

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_managed_instances_list_outbound_network_dependencies_by_managed_instance(self, resource_group):
        response = self.client.managed_instances.list_outbound_network_dependencies_by_managed_instance(
            resource_group_name=resource_group.name,
            managed_instance_name="str",
            api_version="2024-11-01-preview",
        )
        result = [r for r in response]
        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_managed_instances_begin_reevaluate_inaccessible_database_state(self, resource_group):
        response = self.client.managed_instances.begin_reevaluate_inaccessible_database_state(
            resource_group_name=resource_group.name,
            managed_instance_name="str",
            api_version="2024-11-01-preview",
        ).result()  # call '.result()' to poll until service return final result

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_managed_instances_begin_refresh_status(self, resource_group):
        response = self.client.managed_instances.begin_refresh_status(
            resource_group_name=resource_group.name,
            managed_instance_name="str",
            api_version="2024-11-01-preview",
        ).result()  # call '.result()' to poll until service return final result

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_managed_instances_begin_start(self, resource_group):
        response = self.client.managed_instances.begin_start(
            resource_group_name=resource_group.name,
            managed_instance_name="str",
            api_version="2024-11-01-preview",
        ).result()  # call '.result()' to poll until service return final result

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_managed_instances_begin_stop(self, resource_group):
        response = self.client.managed_instances.begin_stop(
            resource_group_name=resource_group.name,
            managed_instance_name="str",
            api_version="2024-11-01-preview",
        ).result()  # call '.result()' to poll until service return final result

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_managed_instances_list_by_managed_instance(self, resource_group):
        response = self.client.managed_instances.list_by_managed_instance(
            resource_group_name=resource_group.name,
            managed_instance_name="str",
            api_version="2024-11-01-preview",
        )
        result = [r for r in response]
        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_managed_instances_begin_validate_azure_key_vault_encryption_key(self, resource_group):
        response = self.client.managed_instances.begin_validate_azure_key_vault_encryption_key(
            resource_group_name=resource_group.name,
            managed_instance_name="str",
            parameters={"tdeKeyUri": "str"},
            api_version="2024-11-01-preview",
        ).result()  # call '.result()' to poll until service return final result

        # please add some check logic here by yourself
        # ...
