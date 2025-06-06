# coding=utf-8
# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is regenerated.
# --------------------------------------------------------------------------
import pytest
from azure.mgmt.avs import AVSClient

from devtools_testutils import AzureMgmtRecordedTestCase, RandomNameResourceGroupPreparer, recorded_by_proxy

AZURE_LOCATION = "eastus"


@pytest.mark.skip("you may need to update the auto-generated test case before run it")
class TestAVSScriptExecutionsOperations(AzureMgmtRecordedTestCase):
    def setup_method(self, method):
        self.client = self.create_mgmt_client(AVSClient)

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_script_executions_list(self, resource_group):
        response = self.client.script_executions.list(
            resource_group_name=resource_group.name,
            private_cloud_name="str",
            api_version="2024-09-01",
        )
        result = [r for r in response]
        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_script_executions_get(self, resource_group):
        response = self.client.script_executions.get(
            resource_group_name=resource_group.name,
            private_cloud_name="str",
            script_execution_name="str",
            api_version="2024-09-01",
        )

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_script_executions_begin_create_or_update(self, resource_group):
        response = self.client.script_executions.begin_create_or_update(
            resource_group_name=resource_group.name,
            private_cloud_name="str",
            script_execution_name="str",
            script_execution={
                "errors": ["str"],
                "failureReason": "str",
                "finishedAt": "2020-02-20 00:00:00",
                "hiddenParameters": ["script_execution_parameter"],
                "id": "str",
                "information": ["str"],
                "name": "str",
                "namedOutputs": {"str": {}},
                "output": ["str"],
                "parameters": ["script_execution_parameter"],
                "provisioningState": "str",
                "retention": "str",
                "scriptCmdletId": "str",
                "startedAt": "2020-02-20 00:00:00",
                "submittedAt": "2020-02-20 00:00:00",
                "systemData": {
                    "createdAt": "2020-02-20 00:00:00",
                    "createdBy": "str",
                    "createdByType": "str",
                    "lastModifiedAt": "2020-02-20 00:00:00",
                    "lastModifiedBy": "str",
                    "lastModifiedByType": "str",
                },
                "timeout": "str",
                "type": "str",
                "warnings": ["str"],
            },
            api_version="2024-09-01",
        ).result()  # call '.result()' to poll until service return final result

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_script_executions_begin_delete(self, resource_group):
        response = self.client.script_executions.begin_delete(
            resource_group_name=resource_group.name,
            private_cloud_name="str",
            script_execution_name="str",
            api_version="2024-09-01",
        ).result()  # call '.result()' to poll until service return final result

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_script_executions_get_execution_logs(self, resource_group):
        response = self.client.script_executions.get_execution_logs(
            resource_group_name=resource_group.name,
            private_cloud_name="str",
            script_execution_name="str",
            api_version="2024-09-01",
        )

        # please add some check logic here by yourself
        # ...
