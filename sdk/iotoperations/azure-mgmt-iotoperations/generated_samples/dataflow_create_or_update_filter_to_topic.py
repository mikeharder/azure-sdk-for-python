# coding=utf-8
# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# Code generated by Microsoft (R) Python Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is regenerated.
# --------------------------------------------------------------------------

from azure.identity import DefaultAzureCredential

from azure.mgmt.iotoperations import IoTOperationsMgmtClient

"""
# PREREQUISITES
    pip install azure-identity
    pip install azure-mgmt-iotoperations
# USAGE
    python dataflow_create_or_update_filter_to_topic.py

    Before run the sample, please set the values of the client ID, tenant ID and client secret
    of the AAD application as environment variables: AZURE_CLIENT_ID, AZURE_TENANT_ID,
    AZURE_CLIENT_SECRET. For more info about how to get the value, please see:
    https://docs.microsoft.com/azure/active-directory/develop/howto-create-service-principal-portal
"""


def main():
    client = IoTOperationsMgmtClient(
        credential=DefaultAzureCredential(),
        subscription_id="SUBSCRIPTION_ID",
    )

    response = client.dataflow.begin_create_or_update(
        resource_group_name="rgiotoperations",
        instance_name="resource-name123",
        dataflow_profile_name="resource-name123",
        dataflow_name="mqtt-filter-to-topic",
        resource={
            "extendedLocation": {"name": "qmbrfwcpwwhggszhrdjv", "type": "CustomLocation"},
            "properties": {
                "mode": "Enabled",
                "operations": [
                    {
                        "name": "source1",
                        "operationType": "Source",
                        "sourceSettings": {
                            "dataSources": ["azure-iot-operations/data/thermostat"],
                            "endpointRef": "aio-builtin-broker-endpoint",
                        },
                    },
                    {
                        "builtInTransformationSettings": {
                            "filter": [
                                {
                                    "description": "filter-datapoint",
                                    "expression": "$1 > 9000 && $2 >= 8000",
                                    "inputs": ["temperature.Value", '"Tag 10".Value'],
                                    "type": "Filter",
                                }
                            ],
                            "map": [{"inputs": ["*"], "output": "*", "type": "PassThrough"}],
                        },
                        "name": "transformation1",
                        "operationType": "BuiltInTransformation",
                    },
                    {
                        "destinationSettings": {
                            "dataDestination": "data/filtered/thermostat",
                            "endpointRef": "aio-builtin-broker-endpoint",
                        },
                        "name": "destination1",
                        "operationType": "Destination",
                    },
                ],
            },
        },
    ).result()
    print(response)


# x-ms-original-file: 2024-11-01/Dataflow_CreateOrUpdate_FilterToTopic.json
if __name__ == "__main__":
    main()
