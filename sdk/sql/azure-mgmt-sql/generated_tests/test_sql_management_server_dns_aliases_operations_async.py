# coding=utf-8
# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is regenerated.
# --------------------------------------------------------------------------
import pytest
from azure.mgmt.sql.aio import SqlManagementClient

from devtools_testutils import AzureMgmtRecordedTestCase, RandomNameResourceGroupPreparer
from devtools_testutils.aio import recorded_by_proxy_async

AZURE_LOCATION = "eastus"


@pytest.mark.skip("you may need to update the auto-generated test case before run it")
class TestSqlManagementServerDnsAliasesOperationsAsync(AzureMgmtRecordedTestCase):
    def setup_method(self, method):
        self.client = self.create_mgmt_client(SqlManagementClient, is_async=True)

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy_async
    async def test_server_dns_aliases_list_by_server(self, resource_group):
        response = self.client.server_dns_aliases.list_by_server(
            resource_group_name=resource_group.name,
            server_name="str",
            api_version="2024-11-01-preview",
        )
        result = [r async for r in response]
        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy_async
    async def test_server_dns_aliases_get(self, resource_group):
        response = await self.client.server_dns_aliases.get(
            resource_group_name=resource_group.name,
            server_name="str",
            dns_alias_name="str",
            api_version="2024-11-01-preview",
        )

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy_async
    async def test_server_dns_aliases_begin_create_or_update(self, resource_group):
        response = await (
            await self.client.server_dns_aliases.begin_create_or_update(
                resource_group_name=resource_group.name,
                server_name="str",
                dns_alias_name="str",
                api_version="2024-11-01-preview",
            )
        ).result()  # call '.result()' to poll until service return final result

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy_async
    async def test_server_dns_aliases_begin_delete(self, resource_group):
        response = await (
            await self.client.server_dns_aliases.begin_delete(
                resource_group_name=resource_group.name,
                server_name="str",
                dns_alias_name="str",
                api_version="2024-11-01-preview",
            )
        ).result()  # call '.result()' to poll until service return final result

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy_async
    async def test_server_dns_aliases_begin_acquire(self, resource_group):
        response = await (
            await self.client.server_dns_aliases.begin_acquire(
                resource_group_name=resource_group.name,
                server_name="str",
                dns_alias_name="str",
                parameters={"oldServerDnsAliasId": "str"},
                api_version="2024-11-01-preview",
            )
        ).result()  # call '.result()' to poll until service return final result

        # please add some check logic here by yourself
        # ...
