# coding: utf-8

# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest

from datetime import datetime, timedelta, timezone
from dateutil.tz import tzutc, tzoffset
from enum import Enum
from math import isnan
from uuid import UUID

from devtools_testutils import AzureRecordedTestCase, recorded_by_proxy

from azure.data.tables import (
    TableServiceClient,
    TableClient,
    generate_table_sas,
    TableEntity,
    EntityProperty,
    EdmType,
    TableSasPermissions,
    TableAccessPolicy,
    UpdateMode,
)

from azure.core import MatchConditions
from azure.core.credentials import AzureSasCredential
from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
    ResourceNotFoundError,
    ResourceExistsError,
    ResourceModifiedError,
)

from _shared.testcase import TableTestCase
from preparers import tables_decorator

TEST_GUID = UUID("1c241c8d-f7b6-4b0a-abba-d9b169010038")

# ------------------------------------------------------------------------------


class TestTableEntity(AzureRecordedTestCase, TableTestCase):
    @tables_decorator
    @recorded_by_proxy
    def test_url_encoding_at_symbol(self, tables_storage_account_name, tables_primary_storage_account_key):
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity = {"PartitionKey": "PK", "RowKey": "table@storage.com", "Value": 100}

            for i in range(10):
                entity["RowKey"] += str(i)
                entity["Value"] += i
                self.table.create_entity(entity)

            f = "RowKey eq '{}'".format(entity["RowKey"])
            entities = self.table.query_entities(f)
            count = 0
            for e in entities:
                assert e["PartitionKey"] == entity["PartitionKey"]
                assert e["RowKey"] == entity["RowKey"]
                assert e["Value"] == entity["Value"]
                count += 1
                self.table.delete_entity(e["PartitionKey"], e["RowKey"])

            assert count == 1

            count = 0
            for e in self.table.query_entities(f):
                count += 1
            assert count == 0
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_insert_etag(self, tables_storage_account_name, tables_primary_storage_account_key):

        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:

            entity, _ = self._insert_random_entity()

            entity1 = self.table.get_entity(row_key=entity["RowKey"], partition_key=entity["PartitionKey"])

            assert "etag" not in entity1
            assert "timestamp" not in entity1
            assert entity1.metadata
            assert entity1.metadata["etag"]
            assert entity1.metadata["timestamp"]

        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_query_user_filter(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity, _ = self._insert_two_opposite_entities()

            # Act
            entities = self.table.query_entities("married eq @my_param", parameters={"my_param": entity["married"]})

            assert entities is not None
            length = 0
            for e in entities:
                self._assert_default_entity(e)
                length += 1

            assert length == 1
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_query_user_filter_multiple_params(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity, _ = self._insert_two_opposite_entities()

            # Act
            parameters = {"my_param": True, "rk": entity["RowKey"]}
            entities = self.table.query_entities("married eq @my_param and RowKey eq @rk", parameters=parameters)

            length = 0
            assert entities is not None
            for entity in entities:
                self._assert_default_entity(entity)
                length += 1

            assert length == 1
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_query_user_filter_integers(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity, _ = self._insert_two_opposite_entities()

            # Act
            parameters = {
                "my_param": 40,
            }
            entities = self.table.query_entities("age lt @my_param", parameters=parameters)

            length = 0
            assert entities is not None
            for entity in entities:
                self._assert_default_entity(entity)
                length += 1

            assert length == 1
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_query_user_filter_floats(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity, _ = self._insert_two_opposite_entities()

            # Act
            parameters = {
                "my_param": entity["ratio"] + 1,
            }
            entities = self.table.query_entities("ratio lt @my_param", parameters=parameters)

            length = 0
            assert entities is not None
            for entity in entities:
                self._assert_default_entity(entity)
                length += 1

            assert length == 1
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_query_user_filter_datetimes(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity, _ = self._insert_two_opposite_entities()

            # Act
            parameters = {
                "my_param": entity["birthday"],
            }
            entities = self.table.query_entities("birthday eq @my_param", parameters=parameters)

            length = 0
            assert entities is not None
            for entity in entities:
                self._assert_default_entity(entity)
                length += 1

            assert length == 1
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_query_user_filter_guids(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity, _ = self._insert_two_opposite_entities()

            # Act
            parameters = {"my_param": entity["clsid"]}
            entities = self.table.query_entities("clsid eq @my_param", parameters=parameters)

            length = 0
            assert entities is not None
            for entity in entities:
                self._assert_default_entity(entity)
                length += 1

            assert length == 1
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_query_user_filter_binary(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity, _ = self._insert_two_opposite_entities()

            # Act
            parameters = {"my_param": entity["binary"]}
            entities = self.table.query_entities("binary eq @my_param", parameters=parameters)

            length = 0
            assert entities is not None
            for entity in entities:
                self._assert_default_entity(entity)
                length += 1

            assert length == 1
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_query_user_filter_int64(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity, _ = self._insert_two_opposite_entities()
            large_entity = {
                "PartitionKey": "pk001",
                "RowKey": "rk001",
                "large_int": EntityProperty(2**40, EdmType.INT64),
            }
            self.table.create_entity(large_entity)

            # Act
            parameters = {"my_param": large_entity["large_int"].value}
            entities = self.table.query_entities("large_int eq @my_param", parameters=parameters)

            length = 0
            assert entities is not None
            for entity in entities:
                # self._assert_default_entity(entity)
                assert large_entity["large_int"] == entity["large_int"]
                length += 1

            assert length == 1
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_query_invalid_filter(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            base_entity = {"PartitionKey": "pk", "RowKey": "rk", "value": 1}

            for i in range(5):
                base_entity["RowKey"] += str(i)
                base_entity["value"] += i
                self.table.create_entity(base_entity)
            # Act
            with pytest.raises(HttpResponseError):
                resp = self.table.query_entities("aaa bbb ccc")
                for row in resp:
                    _ = row

        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_insert_entity_dictionary(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity = self._create_random_entity_dict()

            # Act
            resp = self.table.create_entity(entity=entity)

            # Assert
            self._assert_valid_metadata(resp)
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_insert_entity_with_hook(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity = self._create_random_entity_dict()

            # Act
            resp = self.table.create_entity(entity=entity)
            received_entity = self.table.get_entity(row_key=entity["RowKey"], partition_key=entity["PartitionKey"])

            # Assert
            self._assert_valid_metadata(resp)
            self._assert_default_entity(received_entity)
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_insert_entity_with_no_metadata(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity = self._create_random_entity_dict()
            headers = {"Accept": "application/json;odata=nometadata"}
            # Act
            # response_hook=lambda e, h: (e, h)
            resp = self.table.create_entity(
                entity=entity,
                headers=headers,
            )
            received_entity = self.table.get_entity(
                row_key=entity["RowKey"], partition_key=entity["PartitionKey"], headers=headers
            )

            # Assert
            self._assert_valid_metadata(resp)
            self._assert_default_entity_json_no_metadata(received_entity)
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_insert_entity_with_full_metadata(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity = self._create_random_entity_dict()
            headers = {"Accept": "application/json;odata=fullmetadata"}

            # Act
            resp = self.table.create_entity(
                entity=entity,
                headers=headers,
            )
            received_entity = self.table.get_entity(
                row_key=entity["RowKey"], partition_key=entity["PartitionKey"], headers=headers
            )

            # Assert
            self._assert_valid_metadata(resp)
            self._assert_default_entity_json_full_metadata(received_entity)
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_insert_entity_conflict(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity, _ = self._insert_random_entity()

            # Act
            with pytest.raises(ResourceExistsError):
                self.table.create_entity(entity=entity)

            # Assert
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_insert_entity_with_large_int32_value_throws(
        self, tables_storage_account_name, tables_primary_storage_account_key
    ):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            # Act
            dict32 = self._create_random_base_entity_dict()
            dict32["large"] = EntityProperty(2**31, EdmType.INT32)

            # Assert
            with pytest.raises(HttpResponseError) as error:
                self.table.create_entity(entity=dict32)
            assert "Operation returned an invalid status 'Bad Request'" in str(error.value)
            assert (
                '"code":"InvalidInput","message":{"lang":"en-US","value":"An error occurred while processing this request.'
                in str(error.value)
            )

            dict32["large"] = EntityProperty(-(2**31 + 1), EdmType.INT32)
            with pytest.raises(HttpResponseError) as error:
                self.table.create_entity(entity=dict32)
            assert "Operation returned an invalid status 'Bad Request'" in str(error.value)
            assert (
                '"code":"InvalidInput","message":{"lang":"en-US","value":"An error occurred while processing this request.'
                in str(error.value)
            )
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_insert_entity_with_large_int64_value_throws(
        self, tables_storage_account_name, tables_primary_storage_account_key
    ):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            # Act
            dict64 = self._create_random_base_entity_dict()
            dict64["large"] = EntityProperty(2**63, EdmType.INT64)

            # Assert
            with pytest.raises(HttpResponseError) as error:
                self.table.create_entity(entity=dict64)
            assert "Operation returned an invalid status 'Bad Request'" in str(error.value)
            assert (
                '"code":"InvalidInput","message":{"lang":"en-US","value":"An error occurred while processing this request.'
                in str(error.value)
            )

            dict64["large"] = EntityProperty(-(2**63 + 1), EdmType.INT64)
            with pytest.raises(HttpResponseError) as error:
                self.table.create_entity(entity=dict64)
            assert "Operation returned an invalid status 'Bad Request'" in str(error.value)
            assert (
                '"code":"InvalidInput","message":{"lang":"en-US","value":"An error occurred while processing this request.'
                in str(error.value)
            )
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_insert_entity_with_large_int_success(
        self, tables_storage_account_name, tables_primary_storage_account_key
    ):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            # Act
            dict64 = self._create_random_base_entity_dict()
            dict64["large"] = EntityProperty(2**50, EdmType.INT64)

            # Assert
            self.table.create_entity(entity=dict64)

            received_entity = self.table.get_entity(dict64["PartitionKey"], dict64["RowKey"])
            assert received_entity["large"].value == dict64["large"].value

            dict64["RowKey"] = "negative"
            dict64["large"] = EntityProperty(-(2**50 + 1), EdmType.INT64)
            self.table.create_entity(entity=dict64)

            received_entity = self.table.get_entity(dict64["PartitionKey"], dict64["RowKey"])
            assert received_entity["large"].value == dict64["large"].value

        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_insert_entity_missing_pk(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity = {"RowKey": "rk"}

            # Act
            with pytest.raises(ValueError) as error:
                resp = self.table.create_entity(entity=entity)
                assert str(error).contains("PartitionKey must be present in an entity")
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_insert_entity_empty_string_pk(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity = {"RowKey": "rk", "PartitionKey": ""}

            # Act
            resp = self.table.create_entity(entity=entity)
            self._assert_valid_metadata(resp)

        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_insert_entity_missing_rk(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity = {"PartitionKey": "pk"}

            # Act
            with pytest.raises(ValueError) as error:
                resp = self.table.create_entity(entity=entity)
                assert str(error).contains("RowKey must be present in an entity")

        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_insert_entity_empty_string_rk(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity = {"PartitionKey": "pk", "RowKey": ""}

            # Act
            resp = self.table.create_entity(entity=entity)
            self._assert_valid_metadata(resp)

        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_insert_entity_too_many_properties(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity = self._create_random_base_entity_dict()
            for i in range(255):
                entity["key{0}".format(i)] = "value{0}".format(i)

            # Act
            with pytest.raises(HttpResponseError):
                resp = self.table.create_entity(entity=entity)

            # Assert
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_insert_entity_property_name_too_long(
        self, tables_storage_account_name, tables_primary_storage_account_key
    ):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity = self._create_random_base_entity_dict()
            entity["a" * 256] = "badval"

            # Act
            with pytest.raises(HttpResponseError):
                resp = self.table.create_entity(entity=entity)

            # Assert
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_insert_entity_with_enums(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            # Act
            class Color(Enum):
                RED = 1
                BLUE = 2
                YELLOW = 3

            pk, rk = self._create_pk_rk(None, None)
            entity = TableEntity(PartitionKey=pk, RowKey=rk, test1=Color.YELLOW, test2=Color.BLUE, test3=Color.RED)

            self.table.create_entity(entity=entity)
            resp_entity = self.table.get_entity(partition_key=pk, row_key=rk)
            assert entity["test1"].value == resp_entity["test1"]
            assert entity["test2"].value == resp_entity["test2"]
            assert entity["test3"].value == resp_entity["test3"]

        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_get_entity(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity, _ = self._insert_random_entity()

            # Act
            resp = self.table.get_entity(partition_key=entity["PartitionKey"], row_key=entity["RowKey"])

            # Assert
            assert resp["PartitionKey"] == entity["PartitionKey"]
            assert resp["RowKey"] == entity["RowKey"]
            self._assert_default_entity(resp)
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_get_entity_with_select(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity, _ = self._insert_random_entity()

            resp = self.table.get_entity(
                partition_key=entity["PartitionKey"], row_key=entity["RowKey"], select=["age", "ratio"]
            )
            resp.pop("_metadata", None)
            assert resp == {"age": 39, "ratio": 3.1}
            resp = self.table.get_entity(
                partition_key=entity["PartitionKey"], row_key=entity["RowKey"], select="age,ratio"
            )
            resp.pop("_metadata", None)
            assert resp == {"age": 39, "ratio": 3.1}

        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_get_entity_with_hook(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity, _ = self._insert_random_entity()

            # Act
            # resp, headers
            # response_hook=lambda e, h: (e, h)
            resp = self.table.get_entity(
                partition_key=entity["PartitionKey"],
                row_key=entity["RowKey"],
            )

            # Assert
            assert resp["PartitionKey"] == entity["PartitionKey"]
            assert resp["RowKey"] == entity["RowKey"]
            self._assert_default_entity(resp)
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_get_entity_if_match(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity, etag = self._insert_random_entity()

            entity = self.table.get_entity(partition_key=entity["PartitionKey"], row_key=entity["RowKey"])

            self.table.delete_entity(entity, etag=etag, match_condition=MatchConditions.IfNotModified)

            with pytest.raises(ResourceNotFoundError):
                self.table.get_entity(partition_key=entity["PartitionKey"], row_key=entity["RowKey"])
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_get_entity_if_match_entity_bad_etag(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity, old_etag = self._insert_random_entity()

            entity["value"] = 10
            self.table.update_entity(entity)

            # Get Entity and set old etag
            e = self.table.get_entity(entity["PartitionKey"], entity["RowKey"])
            new_etag = e.metadata["etag"]
            e.metadata["etag"] = old_etag

            with pytest.raises(ResourceModifiedError):
                self.table.delete_entity(e, match_condition=MatchConditions.IfNotModified)

            # Try delete with correct etag
            self.table.delete_entity(e, etag=new_etag, match_condition=MatchConditions.IfNotModified)

        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_delete_entity_if_match_table_entity(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity, etag = self._insert_random_entity()
            table_entity = TableEntity(**entity)

            entity = self.table.get_entity(partition_key=entity["PartitionKey"], row_key=entity["RowKey"])

            with pytest.raises(ValueError):
                self.table.delete_entity(table_entity, match_condition=MatchConditions.IfNotModified)

            self.table.delete_entity(table_entity, etag=etag, match_condition=MatchConditions.IfNotModified)

            with pytest.raises(ResourceNotFoundError):
                self.table.get_entity(entity["PartitionKey"], entity["RowKey"])
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_get_entity_full_metadata(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity, _ = self._insert_random_entity()

            # Act
            resp = self.table.get_entity(
                entity["PartitionKey"], entity["RowKey"], headers={"accept": "application/json;odata=fullmetadata"}
            )

            # Assert
            assert resp["PartitionKey"] == entity["PartitionKey"]
            assert resp["RowKey"] == entity["RowKey"]
            self._assert_default_entity_json_full_metadata(resp)
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_get_entity_no_metadata(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity, _ = self._insert_random_entity()

            # Act
            resp = self.table.get_entity(
                partition_key=entity["PartitionKey"],
                row_key=entity["RowKey"],
                headers={"accept": "application/json;odata=nometadata"},
            )

            # Assert
            assert resp["PartitionKey"] == entity["PartitionKey"]
            assert resp["RowKey"] == entity["RowKey"]
            self._assert_default_entity_json_no_metadata(resp)
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_get_entity_not_existing(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity = self._create_random_entity_dict()

            # Act
            with pytest.raises(ResourceNotFoundError):
                self.table.get_entity(partition_key=entity["PartitionKey"], row_key=entity["RowKey"])

            # Assert
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_get_entity_with_special_doubles(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity = self._create_random_base_entity_dict()
            entity.update({"inf": float("inf"), "negativeinf": float("-inf"), "nan": float("nan")})
            self.table.create_entity(entity=entity)

            # Act
            received_entity = self.table.get_entity(partition_key=entity["PartitionKey"], row_key=entity["RowKey"])

            # Assert
            assert received_entity["inf"] == float("inf")
            assert received_entity["negativeinf"] == float("-inf")
            assert isnan(received_entity["nan"])
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_update_entity(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity, _ = self._insert_random_entity()

            # Act
            sent_entity = self._create_updated_entity_dict(entity["PartitionKey"], entity["RowKey"])

            resp = self.table.update_entity(mode=UpdateMode.REPLACE, entity=sent_entity)

            # Assert
            #  assert resp
            received_entity = self.table.get_entity(partition_key=entity["PartitionKey"], row_key=entity["RowKey"])

            with pytest.raises(KeyError):
                del received_entity["property_that_does_not_exist"]
            self._assert_valid_metadata(resp)
            self._assert_updated_entity(received_entity)
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_update_entity_not_existing(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity = self._create_random_base_entity_dict()

            sent_entity = self._create_updated_entity_dict(entity["PartitionKey"], entity["RowKey"])
            with pytest.raises(ResourceNotFoundError) as ex:
                self.table.update_entity(mode=UpdateMode.REPLACE, entity=sent_entity)
            assert ex.value.response.status_code == 404
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_update_entity_with_if_matches(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity, etag = self._insert_random_entity()

            # Act
            sent_entity = self._create_updated_entity_dict(entity["PartitionKey"], entity["RowKey"])

            resp = self.table.update_entity(
                mode=UpdateMode.REPLACE, entity=sent_entity, etag=etag, match_condition=MatchConditions.IfNotModified
            )

            # Assert
            self._assert_valid_metadata(resp)
            received_entity = self.table.get_entity(entity["PartitionKey"], entity["RowKey"])
            self._assert_updated_entity(received_entity)
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_update_entity_with_if_doesnt_match(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            # Test when the entity not exists
            entity = self._create_random_base_entity_dict()
            sent_entity = self._create_updated_entity_dict(entity["PartitionKey"], entity["RowKey"])
            with pytest.raises(ResourceNotFoundError) as ex:
                self.table.update_entity(
                    mode=UpdateMode.REPLACE,
                    entity=sent_entity,
                    etag="W/\"datetime'2012-06-15T22%3A51%3A44.9662825Z'\"",
                    match_condition=MatchConditions.IfNotModified,
                )
            assert ex.value.response.status_code == 404

            # Test when the entity exists
            entity, _ = self._insert_random_entity()
            sent_entity = self._create_updated_entity_dict(entity["PartitionKey"], entity["RowKey"])
            with pytest.raises(ResourceModifiedError) as ex:
                self.table.update_entity(
                    mode=UpdateMode.REPLACE,
                    entity=sent_entity,
                    etag="W/\"datetime'2012-06-15T22%3A51%3A44.9662825Z'\"",
                    match_condition=MatchConditions.IfNotModified,
                )
            assert ex.value.response.status_code == 412
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_insert_or_merge_entity_with_existing_entity(
        self, tables_storage_account_name, tables_primary_storage_account_key
    ):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity, _ = self._insert_random_entity()

            # Act
            sent_entity = self._create_updated_entity_dict(entity["PartitionKey"], entity["RowKey"])
            resp = self.table.upsert_entity(mode=UpdateMode.MERGE, entity=sent_entity)

            # Assert
            self._assert_valid_metadata(resp)
            received_entity = self.table.get_entity(entity["PartitionKey"], entity["RowKey"])
            self._assert_merged_entity(received_entity)
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_insert_or_merge_entity_with_non_existing_entity(
        self, tables_storage_account_name, tables_primary_storage_account_key
    ):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity = self._create_random_base_entity_dict()

            # Act
            sent_entity = self._create_updated_entity_dict(entity["PartitionKey"], entity["RowKey"])
            resp = self.table.upsert_entity(mode=UpdateMode.MERGE, entity=sent_entity)

            # Assert
            self._assert_valid_metadata(resp)
            received_entity = self.table.get_entity(entity["PartitionKey"], entity["RowKey"])
            self._assert_updated_entity(received_entity)
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_insert_or_replace_entity_with_existing_entity(
        self, tables_storage_account_name, tables_primary_storage_account_key
    ):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity, _ = self._insert_random_entity()

            # Act
            sent_entity = self._create_updated_entity_dict(entity["PartitionKey"], entity["RowKey"])
            resp = self.table.upsert_entity(mode=UpdateMode.REPLACE, entity=sent_entity)

            # Assert
            self._assert_valid_metadata(resp)
            received_entity = self.table.get_entity(entity["PartitionKey"], entity["RowKey"])
            self._assert_updated_entity(received_entity)
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_insert_or_replace_entity_with_non_existing_entity(
        self, tables_storage_account_name, tables_primary_storage_account_key
    ):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity = self._create_random_base_entity_dict()

            # Act
            sent_entity = self._create_updated_entity_dict(entity["PartitionKey"], entity["RowKey"])
            resp = self.table.upsert_entity(mode=UpdateMode.REPLACE, entity=sent_entity)

            # Assert
            self._assert_valid_metadata(resp)
            received_entity = self.table.get_entity(entity["PartitionKey"], entity["RowKey"])
            self._assert_updated_entity(received_entity)
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_merge_entity(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity, _ = self._insert_random_entity()

            # Act
            sent_entity = self._create_updated_entity_dict(entity["PartitionKey"], entity["RowKey"])
            resp = self.table.update_entity(mode=UpdateMode.MERGE, entity=sent_entity)

            # Assert
            self._assert_valid_metadata(resp)
            received_entity = self.table.get_entity(entity["PartitionKey"], entity["RowKey"])
            self._assert_merged_entity(received_entity)
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_merge_entity_not_existing(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity = self._create_random_base_entity_dict()
            sent_entity = self._create_updated_entity_dict(entity["PartitionKey"], entity["RowKey"])

            with pytest.raises(ResourceNotFoundError) as ex:
                self.table.update_entity(mode=UpdateMode.MERGE, entity=sent_entity)
            assert ex.value.response.status_code == 404
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_merge_entity_with_if_matches(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity, etag = self._insert_random_entity()

            # Act
            sent_entity = self._create_updated_entity_dict(entity["PartitionKey"], entity["RowKey"])
            resp = self.table.update_entity(
                mode=UpdateMode.MERGE, entity=sent_entity, etag=etag, match_condition=MatchConditions.IfNotModified
            )

            # Assert
            self._assert_valid_metadata(resp)
            received_entity = self.table.get_entity(entity["PartitionKey"], entity["RowKey"])
            self._assert_merged_entity(received_entity)
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_merge_entity_with_if_doesnt_match(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            # Test when the entity not exists
            entity = self._create_random_base_entity_dict()
            sent_entity = self._create_updated_entity_dict(entity["PartitionKey"], entity["RowKey"])

            with pytest.raises(ResourceNotFoundError) as ex:
                self.table.update_entity(
                    mode=UpdateMode.MERGE,
                    entity=sent_entity,
                    etag="W/\"datetime'2012-06-15T22%3A51%3A44.9662825Z'\"",
                    match_condition=MatchConditions.IfNotModified,
                )
            assert ex.value.response.status_code == 404

            # Test when the entity exists
            entity, _ = self._insert_random_entity()
            sent_entity = self._create_updated_entity_dict(entity["PartitionKey"], entity["RowKey"])

            with pytest.raises(ResourceModifiedError) as ex:
                self.table.update_entity(
                    mode=UpdateMode.MERGE,
                    entity=sent_entity,
                    etag="W/\"datetime'2012-06-15T22%3A51%3A44.9662825Z'\"",
                    match_condition=MatchConditions.IfNotModified,
                )
            assert ex.value.response.status_code == 412
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_delete_entity(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity, _ = self._insert_random_entity()

            # Act
            self.table.delete_entity(partition_key=entity["PartitionKey"], row_key=entity["RowKey"])

            # Assert
            with pytest.raises(ResourceNotFoundError) as ex:
                self.table.get_entity(entity["PartitionKey"], entity["RowKey"])
            assert ex.value.response.status_code == 404
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_delete_entity_not_existing(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity = self._create_random_base_entity_dict()
            self.table.delete_entity(entity["PartitionKey"], entity["RowKey"])
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_delete_entity_with_if_matches(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity, etag = self._insert_random_entity()

            # Act
            self.table.delete_entity(
                entity["PartitionKey"], entity["RowKey"], etag=etag, match_condition=MatchConditions.IfNotModified
            )

            # Assert
            with pytest.raises(ResourceNotFoundError) as ex:
                self.table.get_entity(entity["PartitionKey"], entity["RowKey"])
            assert ex.value.response.status_code == 404
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_delete_entity_with_if_doesnt_match(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity = self._create_random_base_entity_dict()
            self.table.delete_entity(
                entity["PartitionKey"],
                entity["RowKey"],
                etag="W/\"datetime'2012-06-15T22%3A51%3A44.9662825Z'\"",
                match_condition=MatchConditions.IfNotModified,
            )

            entity, _ = self._insert_random_entity()
            with pytest.raises(ResourceModifiedError) as ex:
                self.table.delete_entity(
                    entity["PartitionKey"],
                    entity["RowKey"],
                    etag="W/\"datetime'2012-06-15T22%3A51%3A44.9662825Z'\"",
                    match_condition=MatchConditions.IfNotModified,
                )
            ex.value.response.status_code == 412
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_delete_entity_overloads(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity, _ = self._insert_random_entity()

            # Act
            self.table.delete_entity(entity)

            pk, rk = self._create_pk_rk("pk", "rk")
            pk, rk = pk + "2", rk + "2"
            entity2 = {"PartitionKey": pk, "RowKey": rk, "Value": 100}
            self.table.create_entity(entity2)

            self.table.delete_entity(pk, rk)

            count = 0
            for entity in self.table.list_entities():
                count += 1
            assert count == 0
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_delete_entity_overloads_kwargs(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity, _ = self._insert_random_entity()

            # Act
            self.table.delete_entity(entity=entity)

            pk, rk = self._create_pk_rk("pk", "rk")
            pk, rk = pk + "2", rk + "2"
            entity2 = {"PartitionKey": pk, "RowKey": rk, "Value": 100}
            self.table.create_entity(entity2)

            self.table.delete_entity(partition_key=pk, row_key=rk)

            count = 0
            for entity in self.table.list_entities():
                count += 1
            assert count == 0
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_delete_entity_with_empty_keys(self, tables_storage_account_name, tables_primary_storage_account_key):
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity, _ = self._insert_random_entity(rk="")
            self.table.delete_entity(entity)
            entity, _ = self._insert_random_entity(pk="", rk="")
            result = self.table.get_entity("", "")
            assert result["PartitionKey"] == ""
            assert result["RowKey"] == ""
            self.table.delete_entity(partition_key="", row_key="")
            res = self.table.list_entities()
            assert len(list(res)) == 0
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_unicode_property_value(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity = self._create_random_base_entity_dict()
            entity1 = entity.copy()
            entity1.update({"Description": "ꀕ"})
            entity2 = entity.copy()
            entity2.update({"RowKey": "test2", "Description": "ꀕ"})

            # Act
            self.table.create_entity(entity=entity1)
            self.table.create_entity(entity=entity2)
            entities = list(self.table.query_entities("PartitionKey eq '{}'".format(entity["PartitionKey"])))

            # Assert
            assert len(entities) == 2
            assert entities[0]["Description"] == "ꀕ"
            assert entities[1]["Description"] == "ꀕ"
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_unicode_property_name(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity = self._create_random_base_entity_dict()
            entity1 = entity.copy()
            entity1.update({"啊齄丂狛狜": "ꀕ"})
            entity2 = entity.copy()
            entity2.update({"RowKey": "test2", "啊齄丂狛狜": "hello"})

            # Act
            self.table.create_entity(entity=entity1)
            self.table.create_entity(entity=entity2)
            entities = list(self.table.query_entities("PartitionKey eq '{}'".format(entity["PartitionKey"])))

            # Assert
            assert len(entities) == 2
            assert entities[0]["啊齄丂狛狜"] == "ꀕ"
            assert entities[1]["啊齄丂狛狜"] == "hello"
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_operations_on_entity_with_partition_key_having_single_quote(
        self, tables_storage_account_name, tables_primary_storage_account_key
    ):
        # Arrange
        partition_key_with_single_quote = "a''''b"
        row_key_with_single_quote = "a''''b"
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity, _ = self._insert_random_entity(pk=partition_key_with_single_quote, rk=row_key_with_single_quote)

            # Act
            sent_entity = self._create_updated_entity_dict(entity["PartitionKey"], entity["RowKey"])
            resp = self.table.upsert_entity(mode=UpdateMode.REPLACE, entity=sent_entity)

            # Assert
            self._assert_valid_metadata(resp)
            # row key here only has 2 quotes
            received_entity = self.table.get_entity(entity["PartitionKey"], entity["RowKey"])
            self._assert_updated_entity(received_entity)

            # Act
            sent_entity["newField"] = "newFieldValue"
            resp = self.table.update_entity(mode=UpdateMode.REPLACE, entity=sent_entity)

            # Assert
            self._assert_valid_metadata(resp)
            received_entity = self.table.get_entity(entity["PartitionKey"], entity["RowKey"])
            self._assert_updated_entity(received_entity)
            assert received_entity["newField"] == "newFieldValue"

            # Act
            resp = self.table.delete_entity(entity["PartitionKey"], entity["RowKey"])

            # Assert
            assert resp is None
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_empty_and_spaces_property_value(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity = self._create_random_base_entity_dict()
            entity.update(
                {
                    "EmptyByte": b"",
                    "EmptyUnicode": "",
                    "SpacesOnlyByte": b"   ",
                    "SpacesOnlyUnicode": "   ",
                    "SpacesBeforeByte": b"   Text",
                    "SpacesBeforeUnicode": "   Text",
                    "SpacesAfterByte": b"Text   ",
                    "SpacesAfterUnicode": "Text   ",
                    "SpacesBeforeAndAfterByte": b"   Text   ",
                    "SpacesBeforeAndAfterUnicode": "   Text   ",
                }
            )

            # Act
            self.table.create_entity(entity=entity)
            resp = self.table.get_entity(entity["PartitionKey"], entity["RowKey"])

            # Assert
            assert resp is not None
            assert resp["EmptyByte"] == b""
            assert resp["EmptyUnicode"] == ""
            assert resp["SpacesOnlyByte"] == b"   "
            assert resp["SpacesOnlyUnicode"] == "   "
            assert resp["SpacesBeforeByte"] == b"   Text"
            assert resp["SpacesBeforeUnicode"] == "   Text"
            assert resp["SpacesAfterByte"] == b"Text   "
            assert resp["SpacesAfterUnicode"] == "Text   "
            assert resp["SpacesBeforeAndAfterByte"] == b"   Text   "
            assert resp["SpacesBeforeAndAfterUnicode"] == "   Text   "
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_none_property_value(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity = self._create_random_base_entity_dict()
            entity.update({"NoneValue": None})

            # Act
            self.table.create_entity(entity=entity)
            resp = self.table.get_entity(entity["PartitionKey"], entity["RowKey"])

            # Assert
            assert resp is not None
            assert not hasattr(resp, "NoneValue")
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_binary_property_value(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            binary_data = b"\x01\x02\x03\x04\x05\x06\x07\x08\t\n"
            entity = self._create_random_base_entity_dict()
            entity.update({"binary": b"\x01\x02\x03\x04\x05\x06\x07\x08\t\n"})

            # Act
            self.table.create_entity(entity=entity)
            resp = self.table.get_entity(entity["PartitionKey"], entity["RowKey"])

            # Assert
            assert resp is not None
            assert resp["binary"] == binary_data
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_timezone(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            local_tz = tzoffset("BRST", -10800)
            local_date = datetime(2003, 9, 27, 9, 52, 43, tzinfo=local_tz)
            entity = self._create_random_base_entity_dict()
            entity.update({"date": local_date})

            # Act
            self.table.create_entity(entity=entity)
            resp = self.table.get_entity(entity["PartitionKey"], entity["RowKey"])

            # Assert
            assert resp is not None
            # times are not equal because request is made after
            assert resp["date"].astimezone(tzutc()) == local_date.astimezone(tzutc())
            assert resp["date"].astimezone(local_tz) == local_date
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_query_entities(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            table = self._create_query_table(2)

            # Act
            entities = list(table.list_entities())

            # Assert
            assert len(entities) == 2
            for entity in entities:
                self._assert_default_entity(entity)
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_query_entities_each_page(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            base_entity = {
                "PartitionKey": "pk",
                "RowKey": "1",
            }

            for i in range(10):
                if i > 5:
                    base_entity["PartitionKey"] += str(i)
                base_entity["RowKey"] += str(i)
                base_entity["value"] = i
                try:
                    self.table.create_entity(base_entity)
                except ResourceExistsError:
                    pass

            query_filter = "PartitionKey eq 'pk'"

            entity_count = 0
            page_count = 0
            for entity_page in self.table.query_entities(query_filter, results_per_page=2).by_page():

                temp_count = 0
                for ent in entity_page:
                    temp_count += 1

                assert temp_count <= 2
                page_count += 1
                entity_count += temp_count

            assert entity_count == 6
            assert page_count == 3

        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_query_zero_entities(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            table = self._create_query_table(0)

            # Act
            entities = list(table.list_entities())

            # Assert
            assert len(entities) == 0
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_query_entities_full_metadata(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            table = self._create_query_table(2)

            # Act
            entities = list(table.list_entities(headers={"accept": "application/json;odata=fullmetadata"}))

            # Assert
            assert len(entities) == 2
            for entity in entities:
                self._assert_default_entity_json_full_metadata(entity)
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_query_entities_no_metadata(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            table = self._create_query_table(2)

            # Act
            entities = list(table.list_entities(headers={"accept": "application/json;odata=nometadata"}))

            # Assert
            assert len(entities) == 2
            for entity in entities:
                self._assert_default_entity_json_no_metadata(entity)
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_query_entities_with_filter(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity, _ = self._insert_random_entity()
            entity2, _ = self._insert_random_entity(pk="foo" + entity["PartitionKey"])
            entity3, _ = self._insert_random_entity(pk="bar" + entity["PartitionKey"])

            # Act
            entities = list(
                self.table.query_entities("PartitionKey eq '{}'".format(entity["PartitionKey"]), results_per_page=1)
            )

            # Assert
            assert len(entities) == 1
            assert entity["PartitionKey"] == entities[0]["PartitionKey"]
            self._assert_default_entity(entities[0])
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_query_injection(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            table_name = self.get_resource_name("querytable")
            table = self.ts.create_table_if_not_exists(table_name)
            entity_a = {"PartitionKey": "foo", "RowKey": "bar1", "IsAdmin": "admin"}
            entity_b = {"PartitionKey": "foo", "RowKey": "bar2", "IsAdmin": ""}
            table.create_entity(entity_a)
            table.create_entity(entity_b)

            is_user_admin = "PartitionKey eq @first and IsAdmin eq 'admin'"
            entities = list(table.query_entities(is_user_admin, parameters={"first": "foo"}))
            assert len(entities) == 1

            injection = "foo' or RowKey eq 'bar2"
            injected_query = "PartitionKey eq '{}' and IsAdmin eq 'admin'".format(injection)
            entities = list(table.query_entities(injected_query))
            assert len(entities) == 2

            entities = list(table.query_entities(is_user_admin, parameters={"first": injection}))
            assert len(entities) == 0
        finally:
            self.ts.delete_table(table_name)
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_query_special_chars(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            table_name = self.get_resource_name("querytable")
            table = self.ts.create_table_if_not_exists(table_name)
            entity_a = {"PartitionKey": ":@", "RowKey": "+,$", "Chars": "?'/!_^#"}
            entity_b = {"PartitionKey": ":@", "RowKey": "=& ", "Chars": '?"\\{}<>%'}
            table.create_entity(entity_a)
            table.create_entity(entity_b)

            all_entities = list(table.query_entities("PartitionKey eq ':@'"))
            assert len(all_entities) == 2

            parameters = {"key": ":@"}
            all_entities = list(table.query_entities("PartitionKey eq @key", parameters=parameters))
            assert len(all_entities) == 2

            query = "PartitionKey eq ':@' and RowKey eq '+,$' and Chars eq '?''/!_^#'"
            entities = list(table.query_entities(query))
            assert len(entities) == 1

            query = "PartitionKey eq @key and RowKey eq @row and Chars eq @quote"
            parameters = {"key": ":@", "row": "+,$", "quote": "?'/!_^#"}
            entities = list(table.query_entities(query, parameters=parameters))
            assert len(entities) == 1

            query = "PartitionKey eq ':@' and RowKey eq '=& ' and Chars eq '?\"\\{}<>%'"
            entities = list(table.query_entities(query))
            assert len(entities) == 1

            query = "PartitionKey eq @key and RowKey eq @row and Chars eq @quote"
            parameters = {"key": ":@", "row": "=& ", "quote": '?"\\{}<>%'}
            entities = list(table.query_entities(query, parameters=parameters))
            assert len(entities) == 1

        finally:
            self.ts.delete_table(table_name)
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_query_entities_with_select(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            table = self._create_query_table(2)

            # Act
            entities = list(table.list_entities(select=["age", "sex"]))

            # Assert
            assert len(entities) == 2
            assert entities[0]["age"] == 39
            assert entities[0]["sex"] == "male"
            assert not "birthday" in entities[0]
            assert not "married" in entities[0]
            assert not "deceased" in entities[0]
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_query_entities_with_top(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            table = self._create_query_table(3)
            # circular dependencies made this return a list not an item paged - problem when calling by page
            # Act
            entities = list(next(table.list_entities(results_per_page=2).by_page()))

            # Assert
            assert len(entities) == 2
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_query_entities_with_top_and_next(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            table = self._create_query_table(5)

            # Act
            resp1 = table.list_entities(results_per_page=2).by_page()
            next(resp1)
            resp2 = table.list_entities(results_per_page=2).by_page(continuation_token=resp1.continuation_token)
            next(resp2)
            resp3 = table.list_entities(results_per_page=2).by_page(continuation_token=resp2.continuation_token)
            next(resp3)

            entities1 = resp1._current_page
            entities2 = resp2._current_page
            entities3 = resp3._current_page

            # Assert
            assert len(entities1) == 2
            assert len(entities2) == 2
            assert len(entities3) == 1
            self._assert_default_entity(entities1[0])
            self._assert_default_entity(entities1[1])
            self._assert_default_entity(entities2[0])
            self._assert_default_entity(entities2[1])
            self._assert_default_entity(entities3[0])
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_sas_query(self, tables_storage_account_name, tables_primary_storage_account_key):
        url = self.account_url(tables_storage_account_name, "table")

        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            # Arrange
            entity, _ = self._insert_random_entity()
            token = self.generate_sas(
                generate_table_sas,
                tables_primary_storage_account_key,
                self.table_name,
                permission=TableSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(hours=1),
                start=datetime.utcnow() - timedelta(minutes=1),
            )

            # Act
            service = TableServiceClient(
                self.account_url(tables_storage_account_name, "table"),
                credential=AzureSasCredential(token),
            )
            table = service.get_table_client(self.table_name)
            entities = list(table.query_entities("PartitionKey eq '{}'".format(entity["PartitionKey"])))

            # Assert
            assert len(entities) == 1
            self._assert_default_entity(entities[0])
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_sas_add(self, tables_storage_account_name, tables_primary_storage_account_key):
        url = self.account_url(tables_storage_account_name, "table")
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            # Arrange
            token = self.generate_sas(
                generate_table_sas,
                tables_primary_storage_account_key,
                self.table_name,
                permission=TableSasPermissions(add=True),
                expiry=datetime.utcnow() + timedelta(hours=1),
                start=datetime.utcnow() - timedelta(minutes=1),
            )

            # Act
            service = TableServiceClient(
                self.account_url(tables_storage_account_name, "table"),
                credential=AzureSasCredential(token),
            )
            table = service.get_table_client(self.table_name)

            entity = self._create_random_entity_dict()
            table.create_entity(entity=entity)

            # Assert
            resp = self.table.get_entity(partition_key=entity["PartitionKey"], row_key=entity["RowKey"])
            self._assert_default_entity(resp)
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_sas_add_inside_range(self, tables_storage_account_name, tables_primary_storage_account_key):
        url = self.account_url(tables_storage_account_name, "table")
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            # Arrange
            token = self.generate_sas(
                generate_table_sas,
                tables_primary_storage_account_key,
                self.table_name,
                permission=TableSasPermissions(add=True),
                expiry=datetime.utcnow() + timedelta(hours=1),
                start_pk="test",
                start_rk="test1",
                end_pk="test",
                end_rk="test1",
            )

            # Act
            service = TableServiceClient(
                self.account_url(tables_storage_account_name, "table"),
                credential=AzureSasCredential(token),
            )
            table = service.get_table_client(self.table_name)
            entity = self._create_random_entity_dict("test", "test1")
            table.create_entity(entity=entity)

            # Assert
            resp = self.table.get_entity("test", "test1")
            self._assert_default_entity(resp)
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_sas_add_outside_range(self, tables_storage_account_name, tables_primary_storage_account_key):
        url = self.account_url(tables_storage_account_name, "table")
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            # Arrange
            token = self.generate_sas(
                generate_table_sas,
                tables_primary_storage_account_key,
                self.table_name,
                permission=TableSasPermissions(add=True),
                expiry=datetime.utcnow() + timedelta(hours=1),
                start_pk="test",
                start_rk="test1",
                end_pk="test",
                end_rk="test1",
            )

            # Act
            service = TableServiceClient(
                self.account_url(tables_storage_account_name, "table"),
                credential=AzureSasCredential(token),
            )
            table = service.get_table_client(self.table_name)
            with pytest.raises(HttpResponseError):
                entity = self._create_random_entity_dict()
                table.create_entity(entity=entity)

            # Assert
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_sas_update(self, tables_storage_account_name, tables_primary_storage_account_key):
        url = self.account_url(tables_storage_account_name, "table")
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            # Arrange
            entity, _ = self._insert_random_entity()
            token = self.generate_sas(
                generate_table_sas,
                tables_primary_storage_account_key,
                self.table_name,
                permission=TableSasPermissions(update=True),
                expiry=datetime.utcnow() + timedelta(hours=1),
            )

            service = TableServiceClient(
                self.account_url(tables_storage_account_name, "table"),
                credential=AzureSasCredential(token),
            )
            table = service.get_table_client(self.table_name)
            updated_entity = self._create_updated_entity_dict(entity["PartitionKey"], entity["RowKey"])
            resp = table.update_entity(mode=UpdateMode.REPLACE, entity=updated_entity)

            # Assert
            received_entity = self.table.get_entity(entity["PartitionKey"], entity["RowKey"])
            assert resp is not None
            self._assert_updated_entity(received_entity)
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_sas_delete(self, tables_storage_account_name, tables_primary_storage_account_key):
        url = self.account_url(tables_storage_account_name, "table")
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            # Arrange
            entity, _ = self._insert_random_entity()
            token = self.generate_sas(
                generate_table_sas,
                tables_primary_storage_account_key,
                self.table_name,
                permission=TableSasPermissions(delete=True),
                expiry=datetime.utcnow() + timedelta(hours=1),
            )

            # Act
            service = TableServiceClient(
                self.account_url(tables_storage_account_name, "table"),
                credential=AzureSasCredential(token),
            )
            table = service.get_table_client(self.table_name)
            table.delete_entity(entity["PartitionKey"], entity["RowKey"])

            # Assert
            with pytest.raises(ResourceNotFoundError):
                self.table.get_entity(entity["PartitionKey"], entity["RowKey"])
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_sas_upper_case_table_name(self, tables_storage_account_name, tables_primary_storage_account_key):
        url = self.account_url(tables_storage_account_name, "table")
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            # Arrange
            entity, _ = self._insert_random_entity()

            access_policy = TableAccessPolicy()
            access_policy.start = datetime(2011, 10, 11)
            access_policy.expiry = datetime(2025, 10, 12)
            access_policy.permission = TableSasPermissions(read=True)
            identifiers = {"testid": access_policy}

            self.table.set_table_access_policy(identifiers)

            token = self.generate_sas(
                generate_table_sas,
                tables_primary_storage_account_key,
                self.table_name.upper(),
                permission=TableSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(hours=1),
                start=datetime.utcnow() - timedelta(minutes=1),
            )

            # Act
            service = TableServiceClient(
                self.account_url(tables_storage_account_name, "table"),
                credential=AzureSasCredential(token),
            )
            table = service.get_table_client(self.table_name)
            entities = list(table.query_entities("PartitionKey eq '{}'".format(entity["PartitionKey"])))

            # Assert
            assert len(entities) == 1
            self._assert_default_entity(entities[0])
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_sas_signed_identifier(self, tables_storage_account_name, tables_primary_storage_account_key):
        url = self.account_url(tables_storage_account_name, "table")
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            # Arrange
            entity, _ = self._insert_random_entity()

            access_policy = TableAccessPolicy()
            access_policy.start = datetime(2011, 10, 11)
            access_policy.expiry = datetime(2025, 10, 12)
            access_policy.permission = TableSasPermissions(read=True)
            identifiers = {"testid": access_policy}

            self.table.set_table_access_policy(identifiers)

            token = self.generate_sas(
                generate_table_sas, tables_primary_storage_account_key, self.table_name, policy_id="testid"
            )

            # Act
            service = TableServiceClient(
                self.account_url(tables_storage_account_name, "table"),
                credential=AzureSasCredential(token),
            )
            table = service.get_table_client(self.table_name)
            entities = list(table.query_entities("PartitionKey eq '{}'".format(entity["PartitionKey"])))

            # Assert
            assert len(entities) == 1
            self._assert_default_entity(entities[0])
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_datetime_milliseconds(self, tables_storage_account_name, tables_primary_storage_account_key):
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            entity = self._create_random_entity_dict()

            entity["milliseconds"] = datetime(2011, 11, 4, 0, 5, 23, 283000, tzinfo=tzutc())

            self.table.create_entity(entity)

            received_entity = self.table.get_entity(partition_key=entity["PartitionKey"], row_key=entity["RowKey"])

            assert entity["milliseconds"] == received_entity["milliseconds"]

        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_datetime_str_passthrough(self, tables_storage_account_name, tables_primary_storage_account_key):
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        partition, row = self._create_pk_rk(None, None)

        dotnet_timestamp = "2013-08-22T01:12:06.2608595Z"
        entity = {
            "PartitionKey": partition,
            "RowKey": row,
            "datetime1": EntityProperty(dotnet_timestamp, EdmType.DATETIME),
        }
        try:
            self.table.create_entity(entity)
            received = self.table.get_entity(partition, row)
            assert isinstance(received["datetime1"], datetime)
            assert received["datetime1"].tables_service_value == dotnet_timestamp

            received["datetime2"] = received["datetime1"].replace(year=2020)
            assert received["datetime2"].tables_service_value == ""

            self.table.update_entity(received)
            updated = self.table.get_entity(partition, row)
            assert isinstance(updated["datetime1"], datetime)
            assert isinstance(updated["datetime2"], datetime)
            assert updated["datetime1"].tables_service_value == dotnet_timestamp
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_datetime_duplicate_field(self, tables_storage_account_name, tables_primary_storage_account_key):
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        partition, row = self._create_pk_rk(None, None)

        entity = {
            "PartitionKey": partition,
            "RowKey": row,
            "Timestamp": datetime(year=1999, month=9, day=9, hour=9, minute=9, tzinfo=timezone.utc),
        }
        try:
            self.table.create_entity(entity)
            received = self.table.get_entity(partition, row)

            assert "Timestamp" not in received
            assert "timestamp" in received.metadata
            assert isinstance(received.metadata["timestamp"], datetime)
            assert received.metadata["timestamp"].year > 2020

            received["timestamp"] = datetime(year=1999, month=9, day=9, hour=9, minute=9, tzinfo=timezone.utc)
            self.table.update_entity(received, mode=UpdateMode.REPLACE)
            received = self.table.get_entity(partition, row)

            assert "timestamp" in received
            assert isinstance(received["timestamp"], datetime)
            assert received["timestamp"].year == 1999
            assert isinstance(received.metadata["timestamp"], datetime)
            assert received.metadata["timestamp"].year > 2020
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_etag_duplicate_field(self, tables_storage_account_name, tables_primary_storage_account_key):
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        partition, row = self._create_pk_rk(None, None)

        entity = {
            "PartitionKey": partition,
            "RowKey": row,
            "ETag": "foo",
            "etag": "bar",
            "Etag": "baz",
        }
        try:
            self.table.create_entity(entity)
            created = self.table.get_entity(partition, row)

            assert created["ETag"] == "foo"
            assert created["etag"] == "bar"
            assert created["Etag"] == "baz"
            assert created.metadata["etag"].startswith("W/\"datetime'")

            entity["ETag"] = "one"
            entity["etag"] = "two"
            entity["Etag"] = "three"
            with pytest.raises(ValueError):
                self.table.update_entity(entity, match_condition=MatchConditions.IfNotModified)

            created["ETag"] = "one"
            created["etag"] = "two"
            created["Etag"] = "three"
            self.table.update_entity(created, match_condition=MatchConditions.IfNotModified)

            updated = self.table.get_entity(partition, row)
            assert updated["ETag"] == "one"
            assert updated["etag"] == "two"
            assert updated["Etag"] == "three"
            assert updated.metadata["etag"].startswith("W/\"datetime'")
            assert updated.metadata["etag"] != created.metadata["etag"]
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_entity_create_response_echo(self, tables_storage_account_name, tables_primary_storage_account_key):
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        partition, row = self._create_pk_rk(None, None)

        entity = {"PartitionKey": partition, "RowKey": row, "Value": "foobar", "Answer": 42}
        try:
            result = self.table.create_entity(entity)
            assert "preference_applied" not in result
            assert "content" not in result
            self.table.delete_entity(entity)

            result = self.table.create_entity(entity, headers={"Prefer": "return-no-content"})
            assert "preference_applied" in result
            assert result["preference_applied"] == "return-no-content"
            assert "content" in result
            assert result["content"] is None
            self.table.delete_entity(entity)

            result = self.table.create_entity(entity, headers={"Prefer": "return-content"})
            assert "preference_applied" in result
            assert result["preference_applied"] == "return-content"
            assert "content" in result
            assert result["content"]["PartitionKey"] == partition
            assert result["content"]["Value"] == "foobar"
            assert result["content"]["Answer"] == 42
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_keys_with_specialchar(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            table2_name = self._get_table_reference("table2")
            table2 = self.ts.get_table_client(table2_name)
            table2.create_table()

            # Act
            entity1 = {"PartitionKey": "A'aaa\"_bbbb2", "RowKey": '"A\'aaa"_bbbb2', "test": '"A\'aaa"_bbbb2'}

            self.table.create_entity(entity1.copy())
            get_entity = self.table.get_entity(partition_key=entity1["PartitionKey"], row_key=entity1["RowKey"])
            assert get_entity == entity1
            self.table.upsert_entity(entity1.copy(), mode="merge")
            get_entity = self.table.get_entity(partition_key=entity1["PartitionKey"], row_key=entity1["RowKey"])
            assert get_entity == entity1
            self.table.upsert_entity(entity1.copy(), mode="replace")
            get_entity = self.table.get_entity(partition_key=entity1["PartitionKey"], row_key=entity1["RowKey"])
            assert get_entity == entity1
            self.table.update_entity(entity1.copy(), mode="merge")
            get_entity = self.table.get_entity(partition_key=entity1["PartitionKey"], row_key=entity1["RowKey"])
            assert get_entity == entity1
            self.table.update_entity(entity1.copy(), mode="replace")
            get_entity = self.table.get_entity(partition_key=entity1["PartitionKey"], row_key=entity1["RowKey"])
            assert get_entity == entity1

            entity_results = list(self.table.list_entities())
            assert entity_results[0] == entity1
            for entity in entity_results:
                get_entity = self.table.get_entity(partition_key=entity["PartitionKey"], row_key=entity["RowKey"])
                assert get_entity == entity1

            self.table.delete_entity(entity1.copy())
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_entity_with_edmtypes(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        partition, row = self._create_pk_rk(None, None)

        entity = {
            "PartitionKey": partition,
            "RowKey": row,
            "bool": ("false", "Edm.Boolean"),
            "text": (42, EdmType.STRING),
            "number": ("23", EdmType.INT32),
            "bigNumber": (64, EdmType.INT64),
            "bytes": ("test", "Edm.Binary"),
            "amount": ("0", EdmType.DOUBLE),
            "since": ("2008-07-10T00:00:00", EdmType.DATETIME),
            "guid": (TEST_GUID, EdmType.GUID),
        }
        try:
            self.table.upsert_entity(entity)
            result = self.table.get_entity(entity["PartitionKey"], entity["RowKey"])
            assert result["bool"] == False
            assert result["text"] == "42"
            assert result["number"] == 23
            assert result["bigNumber"][0] == 64
            assert result["bytes"] == b"test"
            assert result["amount"] == 0.0
            assert str(result["since"]) == "2008-07-10 00:00:00+00:00"
            assert result["guid"] == entity["guid"][0]

            with pytest.raises(HttpResponseError) as e:
                entity = {"PartitionKey": partition, "RowKey": row, "bool": ("not a bool", EdmType.BOOLEAN)}
                self.table.upsert_entity(entity)
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_upsert_entity_with_invalid_key_type(self, tables_storage_account_name, tables_primary_storage_account_key):
        # Arrange
        self._set_up(tables_storage_account_name, tables_primary_storage_account_key)
        try:
            table_name = self._get_table_reference("table")
            table = self.ts.get_table_client(table_name)
            table.create_table()

            # Act
            entity1 = {"PartitionKey": 1, "RowKey": "0", "data": 123}
            entity2 = {"PartitionKey": "1", "RowKey": 0, "data": 123}

            with pytest.raises(TypeError):
                self.table.upsert_entity(entity1)
            with pytest.raises(TypeError):
                self.table.upsert_entity(entity2)
        finally:
            self._tear_down()

    @tables_decorator
    @recorded_by_proxy
    def test_list_tables_with_invalid_credential(self, tables_storage_account_name, tables_primary_storage_account_key):
        account_url = self.account_url(tables_storage_account_name, "table")
        credential = self.generate_fake_token_credential()
        client = TableServiceClient(credential=credential, endpoint=account_url, api_version="2020-12-06")
        with pytest.raises(ClientAuthenticationError):
            for _ in client.list_tables():
                pass

    @tables_decorator
    @recorded_by_proxy
    def test_get_entity_with_flatten_metadata(self, tables_storage_account_name, tables_primary_storage_account_key):
        table_name = self._get_table_reference("table")
        url = self.account_url(tables_storage_account_name, "table")
        entity = {"PartitionKey": "pk", "RowKey": "rk", "Value": "foobar", "Answer": 42}

        with TableClient(url, table_name, credential=tables_primary_storage_account_key) as client:
            client.create_table()
            client.create_entity(entity)
            received_entity1 = client.get_entity("pk", "rk")
            assert received_entity1.metadata

        with TableClient(
            url, table_name, credential=tables_primary_storage_account_key, flatten_result_entity=True
        ) as client:
            received_entity2 = client.get_entity("pk", "rk")
            assert received_entity2.metadata == received_entity1.metadata
            for key, value in received_entity1.metadata.items():
                assert received_entity2[key] == value
            client.delete_table()
