# --------------------------------------------------------------------------
#
# Copyright (c) Microsoft Corporation. All rights reserved.
#
# The MIT License (MIT)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the ""Software""), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED *AS IS*, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
# --------------------------------------------------------------------------
"""
FILE: encode_and_decode_with_message_content.py
DESCRIPTION:
    This sample demonstrates the following:
     - Authenticating a sync SchemaRegistryClient to be used by the JsonSchemaEncoder.
     - Passing in content and schema to the JsonSchemaEncoder, which will return a TypedDict containing
      encoded and validated content and corresponding content type.
     - Manually setting the content and content type on a OutboundMessageContent object, specifically EventData.
     - Manually retrieving the content and content type from a InboundMessageContent object, and passing it to the
      JsonSchemaEncoder, which will return the decoded and validated content.
USAGE:
    python encode_and_decode_with_message_content.py
    Set the environment variables with your own values before running the sample:
    1) AZURE_TENANT_ID - The ID of the service principal's tenant. Also called its 'directory' ID.
    2) AZURE_CLIENT_ID - The service principal's client ID. Also called its 'application' ID.
    3) AZURE_CLIENT_SECRET - One of the service principal's client secrets.
    4) SCHEMAREGISTRY_JSON_FULLY_QUALIFIED_NAMESPACE - The schema registry fully qualified namespace,
     which should follow the format: `<your-namespace>.servicebus.windows.net`
    5) SCHEMAREGISTRY_GROUP - The name of the JSON schema group.

This example uses ClientSecretCredential, which requests a token from Azure Active Directory.
For more information on ClientSecretCredential, see:
    https://learn.microsoft.com/python/api/azure-identity/azure.identity.clientsecretcredential?view=azure-python
"""
import os
import json
from typing import List, cast

from azure.identity import ClientSecretCredential
from azure.schemaregistry import SchemaRegistryClient, MessageContent
from azure.schemaregistry.encoder.jsonencoder import JsonSchemaEncoder
from azure.eventhub import EventData

TENANT_ID = os.environ["AZURE_TENANT_ID"]
CLIENT_ID = os.environ["AZURE_CLIENT_ID"]
CLIENT_SECRET = os.environ["AZURE_CLIENT_SECRET"]

SCHEMAREGISTRY_FULLY_QUALIFIED_NAMESPACE = os.environ["SCHEMAREGISTRY_JSON_FULLY_QUALIFIED_NAMESPACE"]
GROUP_NAME = os.environ["SCHEMAREGISTRY_GROUP"]
SCHEMA_JSON = {
    "$id": "https://example.com/person.schema.json",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Person",
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "Person's name."},
        "favorite_color": {"type": "string", "description": "Favorite color."},
        "favorite_number": {
            "description": "Favorite number.",
            "type": "integer",
        },
    },
}
SCHEMA_STRING = json.dumps(SCHEMA_JSON)


token_credential = ClientSecretCredential(tenant_id=TENANT_ID, client_id=CLIENT_ID, client_secret=CLIENT_SECRET)


def encode_message_content_dict(encoder: JsonSchemaEncoder):
    dict_content_ben = {"name": "Ben", "favorite_number": 7, "favorite_color": "red"}
    encoded_message_content_ben = encoder.encode(dict_content_ben, schema=SCHEMA_STRING)

    print("Encoded message content is: ", encoded_message_content_ben)
    return EventData.from_message_content(
        encoded_message_content_ben["content"],
        encoded_message_content_ben["content_type"],
    )


def decode_with_content_and_content_type(encoder: JsonSchemaEncoder, event_data: EventData):
    # get content as bytes
    content = bytearray()
    for c in cast(List[bytes], event_data.body):
        content += c
    content_bytes = bytes(content)
    message_content = MessageContent({"content": content_bytes, "content_type": cast(str, event_data.content_type)})
    decoded_content = encoder.decode(message_content)

    print("Decoded content is: ", decoded_content)
    return decoded_content


if __name__ == "__main__":
    schema_registry = SchemaRegistryClient(
        fully_qualified_namespace=SCHEMAREGISTRY_FULLY_QUALIFIED_NAMESPACE,
        credential=token_credential,
    )
    encoder = JsonSchemaEncoder(
        client=schema_registry, group_name=GROUP_NAME, validate=cast(str, SCHEMA_JSON["$schema"])
    )
    event_data = encode_message_content_dict(encoder)
    decoded_content = decode_with_content_and_content_type(encoder, event_data)
    encoder.close()
