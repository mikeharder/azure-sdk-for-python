# coding=utf-8
# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is regenerated.
# --------------------------------------------------------------------------
import pytest
from azure.mgmt.desktopvirtualization import DesktopVirtualizationMgmtClient

from devtools_testutils import AzureMgmtRecordedTestCase, RandomNameResourceGroupPreparer, recorded_by_proxy

AZURE_LOCATION = "eastus"


@pytest.mark.skip("you may need to update the auto-generated test case before run it")
class TestDesktopVirtualizationMgmtApplicationsOperations(AzureMgmtRecordedTestCase):
    def setup_method(self, method):
        self.client = self.create_mgmt_client(DesktopVirtualizationMgmtClient)

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_get(self, resource_group):
        response = self.client.applications.get(
            resource_group_name=resource_group.name,
            application_group_name="str",
            application_name="str",
            api_version="2024-04-03",
        )

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_create_or_update(self, resource_group):
        response = self.client.applications.create_or_update(
            resource_group_name=resource_group.name,
            application_group_name="str",
            application_name="str",
            application={
                "commandLineSetting": "str",
                "applicationType": "str",
                "commandLineArguments": "str",
                "description": "str",
                "filePath": "str",
                "friendlyName": "str",
                "iconContent": bytes("bytes", encoding="utf-8"),
                "iconHash": "str",
                "iconIndex": 0,
                "iconPath": "str",
                "id": "str",
                "msixPackageApplicationId": "str",
                "msixPackageFamilyName": "str",
                "name": "str",
                "objectId": "str",
                "showInPortal": bool,
                "systemData": {
                    "createdAt": "2020-02-20 00:00:00",
                    "createdBy": "str",
                    "createdByType": "str",
                    "lastModifiedAt": "2020-02-20 00:00:00",
                    "lastModifiedBy": "str",
                    "lastModifiedByType": "str",
                },
                "type": "str",
            },
            api_version="2024-04-03",
        )

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_delete(self, resource_group):
        response = self.client.applications.delete(
            resource_group_name=resource_group.name,
            application_group_name="str",
            application_name="str",
            api_version="2024-04-03",
        )

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_update(self, resource_group):
        response = self.client.applications.update(
            resource_group_name=resource_group.name,
            application_group_name="str",
            application_name="str",
            api_version="2024-04-03",
        )

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_list(self, resource_group):
        response = self.client.applications.list(
            resource_group_name=resource_group.name,
            application_group_name="str",
            api_version="2024-04-03",
        )
        result = [r for r in response]
        # please add some check logic here by yourself
        # ...
