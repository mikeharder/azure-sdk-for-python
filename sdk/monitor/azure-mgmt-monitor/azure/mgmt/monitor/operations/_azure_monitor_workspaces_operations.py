# pylint: disable=line-too-long,useless-suppression
# coding=utf-8
# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is regenerated.
# --------------------------------------------------------------------------
from collections.abc import MutableMapping
from io import IOBase
from typing import Any, Callable, Dict, IO, Iterator, Optional, TypeVar, Union, cast, overload

from azure.core import PipelineClient
from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
    ResourceExistsError,
    ResourceNotFoundError,
    ResourceNotModifiedError,
    StreamClosedError,
    StreamConsumedError,
    map_error,
)
from azure.core.paging import ItemPaged
from azure.core.pipeline import PipelineResponse
from azure.core.polling import LROPoller, NoPolling, PollingMethod
from azure.core.rest import HttpRequest, HttpResponse
from azure.core.tracing.decorator import distributed_trace
from azure.core.utils import case_insensitive_dict
from azure.mgmt.core.exceptions import ARMErrorFormat
from azure.mgmt.core.polling.arm_polling import ARMPolling

from .. import models as _models
from .._configuration import MonitorManagementClientConfiguration
from .._utils.serialization import Deserializer, Serializer

T = TypeVar("T")
ClsType = Optional[Callable[[PipelineResponse[HttpRequest, HttpResponse], T, Dict[str, Any]], Any]]

_SERIALIZER = Serializer()
_SERIALIZER.client_side_validation = False


def build_list_by_resource_group_request(resource_group_name: str, subscription_id: str, **kwargs: Any) -> HttpRequest:
    _headers = case_insensitive_dict(kwargs.pop("headers", {}) or {})
    _params = case_insensitive_dict(kwargs.pop("params", {}) or {})

    api_version: str = kwargs.pop("api_version", _params.pop("api-version", "2023-04-03"))
    accept = _headers.pop("Accept", "application/json")

    # Construct URL
    _url = kwargs.pop(
        "template_url",
        "/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.Monitor/accounts",
    )
    path_format_arguments = {
        "subscriptionId": _SERIALIZER.url("subscription_id", subscription_id, "str", min_length=1),
        "resourceGroupName": _SERIALIZER.url(
            "resource_group_name", resource_group_name, "str", max_length=90, min_length=1
        ),
    }

    _url: str = _url.format(**path_format_arguments)  # type: ignore

    # Construct parameters
    _params["api-version"] = _SERIALIZER.query("api_version", api_version, "str")

    # Construct headers
    _headers["Accept"] = _SERIALIZER.header("accept", accept, "str")

    return HttpRequest(method="GET", url=_url, params=_params, headers=_headers, **kwargs)


def build_list_by_subscription_request(subscription_id: str, **kwargs: Any) -> HttpRequest:
    _headers = case_insensitive_dict(kwargs.pop("headers", {}) or {})
    _params = case_insensitive_dict(kwargs.pop("params", {}) or {})

    api_version: str = kwargs.pop("api_version", _params.pop("api-version", "2023-04-03"))
    accept = _headers.pop("Accept", "application/json")

    # Construct URL
    _url = kwargs.pop("template_url", "/subscriptions/{subscriptionId}/providers/Microsoft.Monitor/accounts")
    path_format_arguments = {
        "subscriptionId": _SERIALIZER.url("subscription_id", subscription_id, "str", min_length=1),
    }

    _url: str = _url.format(**path_format_arguments)  # type: ignore

    # Construct parameters
    _params["api-version"] = _SERIALIZER.query("api_version", api_version, "str")

    # Construct headers
    _headers["Accept"] = _SERIALIZER.header("accept", accept, "str")

    return HttpRequest(method="GET", url=_url, params=_params, headers=_headers, **kwargs)


def build_get_request(
    resource_group_name: str, azure_monitor_workspace_name: str, subscription_id: str, **kwargs: Any
) -> HttpRequest:
    _headers = case_insensitive_dict(kwargs.pop("headers", {}) or {})
    _params = case_insensitive_dict(kwargs.pop("params", {}) or {})

    api_version: str = kwargs.pop("api_version", _params.pop("api-version", "2023-04-03"))
    accept = _headers.pop("Accept", "application/json")

    # Construct URL
    _url = kwargs.pop(
        "template_url",
        "/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.Monitor/accounts/{azureMonitorWorkspaceName}",
    )
    path_format_arguments = {
        "subscriptionId": _SERIALIZER.url("subscription_id", subscription_id, "str", min_length=1),
        "resourceGroupName": _SERIALIZER.url(
            "resource_group_name", resource_group_name, "str", max_length=90, min_length=1
        ),
        "azureMonitorWorkspaceName": _SERIALIZER.url(
            "azure_monitor_workspace_name", azure_monitor_workspace_name, "str", pattern=r"^(?!-)[a-zA-Z0-9-]+[^-]$"
        ),
    }

    _url: str = _url.format(**path_format_arguments)  # type: ignore

    # Construct parameters
    _params["api-version"] = _SERIALIZER.query("api_version", api_version, "str")

    # Construct headers
    _headers["Accept"] = _SERIALIZER.header("accept", accept, "str")

    return HttpRequest(method="GET", url=_url, params=_params, headers=_headers, **kwargs)


def build_create_request(
    resource_group_name: str, azure_monitor_workspace_name: str, subscription_id: str, **kwargs: Any
) -> HttpRequest:
    _headers = case_insensitive_dict(kwargs.pop("headers", {}) or {})
    _params = case_insensitive_dict(kwargs.pop("params", {}) or {})

    api_version: str = kwargs.pop("api_version", _params.pop("api-version", "2023-04-03"))
    content_type: Optional[str] = kwargs.pop("content_type", _headers.pop("Content-Type", None))
    accept = _headers.pop("Accept", "application/json")

    # Construct URL
    _url = kwargs.pop(
        "template_url",
        "/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.Monitor/accounts/{azureMonitorWorkspaceName}",
    )
    path_format_arguments = {
        "subscriptionId": _SERIALIZER.url("subscription_id", subscription_id, "str", min_length=1),
        "resourceGroupName": _SERIALIZER.url(
            "resource_group_name", resource_group_name, "str", max_length=90, min_length=1
        ),
        "azureMonitorWorkspaceName": _SERIALIZER.url(
            "azure_monitor_workspace_name", azure_monitor_workspace_name, "str", pattern=r"^(?!-)[a-zA-Z0-9-]+[^-]$"
        ),
    }

    _url: str = _url.format(**path_format_arguments)  # type: ignore

    # Construct parameters
    _params["api-version"] = _SERIALIZER.query("api_version", api_version, "str")

    # Construct headers
    if content_type is not None:
        _headers["Content-Type"] = _SERIALIZER.header("content_type", content_type, "str")
    _headers["Accept"] = _SERIALIZER.header("accept", accept, "str")

    return HttpRequest(method="PUT", url=_url, params=_params, headers=_headers, **kwargs)


def build_update_request(
    resource_group_name: str, azure_monitor_workspace_name: str, subscription_id: str, **kwargs: Any
) -> HttpRequest:
    _headers = case_insensitive_dict(kwargs.pop("headers", {}) or {})
    _params = case_insensitive_dict(kwargs.pop("params", {}) or {})

    api_version: str = kwargs.pop("api_version", _params.pop("api-version", "2023-04-03"))
    content_type: Optional[str] = kwargs.pop("content_type", _headers.pop("Content-Type", None))
    accept = _headers.pop("Accept", "application/json")

    # Construct URL
    _url = kwargs.pop(
        "template_url",
        "/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.Monitor/accounts/{azureMonitorWorkspaceName}",
    )
    path_format_arguments = {
        "subscriptionId": _SERIALIZER.url("subscription_id", subscription_id, "str", min_length=1),
        "resourceGroupName": _SERIALIZER.url(
            "resource_group_name", resource_group_name, "str", max_length=90, min_length=1
        ),
        "azureMonitorWorkspaceName": _SERIALIZER.url(
            "azure_monitor_workspace_name", azure_monitor_workspace_name, "str", pattern=r"^(?!-)[a-zA-Z0-9-]+[^-]$"
        ),
    }

    _url: str = _url.format(**path_format_arguments)  # type: ignore

    # Construct parameters
    _params["api-version"] = _SERIALIZER.query("api_version", api_version, "str")

    # Construct headers
    if content_type is not None:
        _headers["Content-Type"] = _SERIALIZER.header("content_type", content_type, "str")
    _headers["Accept"] = _SERIALIZER.header("accept", accept, "str")

    return HttpRequest(method="PATCH", url=_url, params=_params, headers=_headers, **kwargs)


def build_delete_request(
    resource_group_name: str, azure_monitor_workspace_name: str, subscription_id: str, **kwargs: Any
) -> HttpRequest:
    _headers = case_insensitive_dict(kwargs.pop("headers", {}) or {})
    _params = case_insensitive_dict(kwargs.pop("params", {}) or {})

    api_version: str = kwargs.pop("api_version", _params.pop("api-version", "2023-04-03"))
    accept = _headers.pop("Accept", "application/json")

    # Construct URL
    _url = kwargs.pop(
        "template_url",
        "/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.Monitor/accounts/{azureMonitorWorkspaceName}",
    )
    path_format_arguments = {
        "subscriptionId": _SERIALIZER.url("subscription_id", subscription_id, "str", min_length=1),
        "resourceGroupName": _SERIALIZER.url(
            "resource_group_name", resource_group_name, "str", max_length=90, min_length=1
        ),
        "azureMonitorWorkspaceName": _SERIALIZER.url(
            "azure_monitor_workspace_name", azure_monitor_workspace_name, "str", pattern=r"^(?!-)[a-zA-Z0-9-]+[^-]$"
        ),
    }

    _url: str = _url.format(**path_format_arguments)  # type: ignore

    # Construct parameters
    _params["api-version"] = _SERIALIZER.query("api_version", api_version, "str")

    # Construct headers
    _headers["Accept"] = _SERIALIZER.header("accept", accept, "str")

    return HttpRequest(method="DELETE", url=_url, params=_params, headers=_headers, **kwargs)


class AzureMonitorWorkspacesOperations:
    """
    .. warning::
        **DO NOT** instantiate this class directly.

        Instead, you should access the following operations through
        :class:`~azure.mgmt.monitor.MonitorManagementClient`'s
        :attr:`azure_monitor_workspaces` attribute.
    """

    models = _models

    def __init__(self, *args, **kwargs) -> None:
        input_args = list(args)
        self._client: PipelineClient = input_args.pop(0) if input_args else kwargs.pop("client")
        self._config: MonitorManagementClientConfiguration = input_args.pop(0) if input_args else kwargs.pop("config")
        self._serialize: Serializer = input_args.pop(0) if input_args else kwargs.pop("serializer")
        self._deserialize: Deserializer = input_args.pop(0) if input_args else kwargs.pop("deserializer")

    @distributed_trace
    def list_by_resource_group(
        self, resource_group_name: str, **kwargs: Any
    ) -> ItemPaged["_models.AzureMonitorWorkspaceResource"]:
        """Lists all Azure Monitor Workspaces in the specified resource group.

        :param resource_group_name: The name of the resource group. The name is case insensitive.
         Required.
        :type resource_group_name: str
        :return: An iterator like instance of either AzureMonitorWorkspaceResource or the result of
         cls(response)
        :rtype: ~azure.core.paging.ItemPaged[~azure.mgmt.monitor.models.AzureMonitorWorkspaceResource]
        :raises ~azure.core.exceptions.HttpResponseError:
        """
        _headers = kwargs.pop("headers", {}) or {}
        _params = case_insensitive_dict(kwargs.pop("params", {}) or {})

        api_version: str = kwargs.pop("api_version", _params.pop("api-version", "2023-04-03"))
        cls: ClsType[_models.AzureMonitorWorkspaceResourceListResult] = kwargs.pop("cls", None)

        error_map: MutableMapping = {
            401: ClientAuthenticationError,
            404: ResourceNotFoundError,
            409: ResourceExistsError,
            304: ResourceNotModifiedError,
        }
        error_map.update(kwargs.pop("error_map", {}) or {})

        def prepare_request(next_link=None):
            if not next_link:

                _request = build_list_by_resource_group_request(
                    resource_group_name=resource_group_name,
                    subscription_id=self._config.subscription_id,
                    api_version=api_version,
                    headers=_headers,
                    params=_params,
                )
                _request.url = self._client.format_url(_request.url)

            else:
                _request = HttpRequest("GET", next_link)
                _request.url = self._client.format_url(_request.url)
                _request.method = "GET"
            return _request

        def extract_data(pipeline_response):
            deserialized = self._deserialize("AzureMonitorWorkspaceResourceListResult", pipeline_response)
            list_of_elem = deserialized.value
            if cls:
                list_of_elem = cls(list_of_elem)  # type: ignore
            return deserialized.next_link or None, iter(list_of_elem)

        def get_next(next_link=None):
            _request = prepare_request(next_link)

            _stream = False
            pipeline_response: PipelineResponse = self._client._pipeline.run(  # pylint: disable=protected-access
                _request, stream=_stream, **kwargs
            )
            response = pipeline_response.http_response

            if response.status_code not in [200]:
                map_error(status_code=response.status_code, response=response, error_map=error_map)
                error = self._deserialize.failsafe_deserialize(_models.ErrorResponseAutoGenerated5, pipeline_response)
                raise HttpResponseError(response=response, model=error, error_format=ARMErrorFormat)

            return pipeline_response

        return ItemPaged(get_next, extract_data)

    @distributed_trace
    def list_by_subscription(self, **kwargs: Any) -> ItemPaged["_models.AzureMonitorWorkspaceResource"]:
        """Lists all Azure Monitor Workspaces in the specified subscription.

        :return: An iterator like instance of either AzureMonitorWorkspaceResource or the result of
         cls(response)
        :rtype: ~azure.core.paging.ItemPaged[~azure.mgmt.monitor.models.AzureMonitorWorkspaceResource]
        :raises ~azure.core.exceptions.HttpResponseError:
        """
        _headers = kwargs.pop("headers", {}) or {}
        _params = case_insensitive_dict(kwargs.pop("params", {}) or {})

        api_version: str = kwargs.pop("api_version", _params.pop("api-version", "2023-04-03"))
        cls: ClsType[_models.AzureMonitorWorkspaceResourceListResult] = kwargs.pop("cls", None)

        error_map: MutableMapping = {
            401: ClientAuthenticationError,
            404: ResourceNotFoundError,
            409: ResourceExistsError,
            304: ResourceNotModifiedError,
        }
        error_map.update(kwargs.pop("error_map", {}) or {})

        def prepare_request(next_link=None):
            if not next_link:

                _request = build_list_by_subscription_request(
                    subscription_id=self._config.subscription_id,
                    api_version=api_version,
                    headers=_headers,
                    params=_params,
                )
                _request.url = self._client.format_url(_request.url)

            else:
                _request = HttpRequest("GET", next_link)
                _request.url = self._client.format_url(_request.url)
                _request.method = "GET"
            return _request

        def extract_data(pipeline_response):
            deserialized = self._deserialize("AzureMonitorWorkspaceResourceListResult", pipeline_response)
            list_of_elem = deserialized.value
            if cls:
                list_of_elem = cls(list_of_elem)  # type: ignore
            return deserialized.next_link or None, iter(list_of_elem)

        def get_next(next_link=None):
            _request = prepare_request(next_link)

            _stream = False
            pipeline_response: PipelineResponse = self._client._pipeline.run(  # pylint: disable=protected-access
                _request, stream=_stream, **kwargs
            )
            response = pipeline_response.http_response

            if response.status_code not in [200]:
                map_error(status_code=response.status_code, response=response, error_map=error_map)
                error = self._deserialize.failsafe_deserialize(_models.ErrorResponseAutoGenerated5, pipeline_response)
                raise HttpResponseError(response=response, model=error, error_format=ARMErrorFormat)

            return pipeline_response

        return ItemPaged(get_next, extract_data)

    @distributed_trace
    def get(
        self, resource_group_name: str, azure_monitor_workspace_name: str, **kwargs: Any
    ) -> _models.AzureMonitorWorkspaceResource:
        """Returns the specified Azure Monitor Workspace.

        :param resource_group_name: The name of the resource group. The name is case insensitive.
         Required.
        :type resource_group_name: str
        :param azure_monitor_workspace_name: The name of the Azure Monitor Workspace. The name is case
         insensitive. Required.
        :type azure_monitor_workspace_name: str
        :return: AzureMonitorWorkspaceResource or the result of cls(response)
        :rtype: ~azure.mgmt.monitor.models.AzureMonitorWorkspaceResource
        :raises ~azure.core.exceptions.HttpResponseError:
        """
        error_map: MutableMapping = {
            401: ClientAuthenticationError,
            404: ResourceNotFoundError,
            409: ResourceExistsError,
            304: ResourceNotModifiedError,
        }
        error_map.update(kwargs.pop("error_map", {}) or {})

        _headers = kwargs.pop("headers", {}) or {}
        _params = case_insensitive_dict(kwargs.pop("params", {}) or {})

        api_version: str = kwargs.pop("api_version", _params.pop("api-version", "2023-04-03"))
        cls: ClsType[_models.AzureMonitorWorkspaceResource] = kwargs.pop("cls", None)

        _request = build_get_request(
            resource_group_name=resource_group_name,
            azure_monitor_workspace_name=azure_monitor_workspace_name,
            subscription_id=self._config.subscription_id,
            api_version=api_version,
            headers=_headers,
            params=_params,
        )
        _request.url = self._client.format_url(_request.url)

        _stream = False
        pipeline_response: PipelineResponse = self._client._pipeline.run(  # pylint: disable=protected-access
            _request, stream=_stream, **kwargs
        )

        response = pipeline_response.http_response

        if response.status_code not in [200]:
            map_error(status_code=response.status_code, response=response, error_map=error_map)
            error = self._deserialize.failsafe_deserialize(_models.ErrorResponseAutoGenerated5, pipeline_response)
            raise HttpResponseError(response=response, model=error, error_format=ARMErrorFormat)

        deserialized = self._deserialize("AzureMonitorWorkspaceResource", pipeline_response.http_response)

        if cls:
            return cls(pipeline_response, deserialized, {})  # type: ignore

        return deserialized  # type: ignore

    @overload
    def create(
        self,
        resource_group_name: str,
        azure_monitor_workspace_name: str,
        azure_monitor_workspace_properties: _models.AzureMonitorWorkspaceResource,
        *,
        content_type: str = "application/json",
        **kwargs: Any
    ) -> _models.AzureMonitorWorkspaceResource:
        """Creates or updates an Azure Monitor Workspace.

        :param resource_group_name: The name of the resource group. The name is case insensitive.
         Required.
        :type resource_group_name: str
        :param azure_monitor_workspace_name: The name of the Azure Monitor Workspace. The name is case
         insensitive. Required.
        :type azure_monitor_workspace_name: str
        :param azure_monitor_workspace_properties: Properties that need to be specified to create a new
         Azure Monitor Workspace. Required.
        :type azure_monitor_workspace_properties:
         ~azure.mgmt.monitor.models.AzureMonitorWorkspaceResource
        :keyword content_type: Body Parameter content-type. Content type parameter for JSON body.
         Default value is "application/json".
        :paramtype content_type: str
        :return: AzureMonitorWorkspaceResource or the result of cls(response)
        :rtype: ~azure.mgmt.monitor.models.AzureMonitorWorkspaceResource
        :raises ~azure.core.exceptions.HttpResponseError:
        """

    @overload
    def create(
        self,
        resource_group_name: str,
        azure_monitor_workspace_name: str,
        azure_monitor_workspace_properties: IO[bytes],
        *,
        content_type: str = "application/json",
        **kwargs: Any
    ) -> _models.AzureMonitorWorkspaceResource:
        """Creates or updates an Azure Monitor Workspace.

        :param resource_group_name: The name of the resource group. The name is case insensitive.
         Required.
        :type resource_group_name: str
        :param azure_monitor_workspace_name: The name of the Azure Monitor Workspace. The name is case
         insensitive. Required.
        :type azure_monitor_workspace_name: str
        :param azure_monitor_workspace_properties: Properties that need to be specified to create a new
         Azure Monitor Workspace. Required.
        :type azure_monitor_workspace_properties: IO[bytes]
        :keyword content_type: Body Parameter content-type. Content type parameter for binary body.
         Default value is "application/json".
        :paramtype content_type: str
        :return: AzureMonitorWorkspaceResource or the result of cls(response)
        :rtype: ~azure.mgmt.monitor.models.AzureMonitorWorkspaceResource
        :raises ~azure.core.exceptions.HttpResponseError:
        """

    @distributed_trace
    def create(
        self,
        resource_group_name: str,
        azure_monitor_workspace_name: str,
        azure_monitor_workspace_properties: Union[_models.AzureMonitorWorkspaceResource, IO[bytes]],
        **kwargs: Any
    ) -> _models.AzureMonitorWorkspaceResource:
        """Creates or updates an Azure Monitor Workspace.

        :param resource_group_name: The name of the resource group. The name is case insensitive.
         Required.
        :type resource_group_name: str
        :param azure_monitor_workspace_name: The name of the Azure Monitor Workspace. The name is case
         insensitive. Required.
        :type azure_monitor_workspace_name: str
        :param azure_monitor_workspace_properties: Properties that need to be specified to create a new
         Azure Monitor Workspace. Is either a AzureMonitorWorkspaceResource type or a IO[bytes] type.
         Required.
        :type azure_monitor_workspace_properties:
         ~azure.mgmt.monitor.models.AzureMonitorWorkspaceResource or IO[bytes]
        :return: AzureMonitorWorkspaceResource or the result of cls(response)
        :rtype: ~azure.mgmt.monitor.models.AzureMonitorWorkspaceResource
        :raises ~azure.core.exceptions.HttpResponseError:
        """
        error_map: MutableMapping = {
            401: ClientAuthenticationError,
            404: ResourceNotFoundError,
            409: ResourceExistsError,
            304: ResourceNotModifiedError,
        }
        error_map.update(kwargs.pop("error_map", {}) or {})

        _headers = case_insensitive_dict(kwargs.pop("headers", {}) or {})
        _params = case_insensitive_dict(kwargs.pop("params", {}) or {})

        api_version: str = kwargs.pop("api_version", _params.pop("api-version", "2023-04-03"))
        content_type: Optional[str] = kwargs.pop("content_type", _headers.pop("Content-Type", None))
        cls: ClsType[_models.AzureMonitorWorkspaceResource] = kwargs.pop("cls", None)

        content_type = content_type or "application/json"
        _json = None
        _content = None
        if isinstance(azure_monitor_workspace_properties, (IOBase, bytes)):
            _content = azure_monitor_workspace_properties
        else:
            _json = self._serialize.body(azure_monitor_workspace_properties, "AzureMonitorWorkspaceResource")

        _request = build_create_request(
            resource_group_name=resource_group_name,
            azure_monitor_workspace_name=azure_monitor_workspace_name,
            subscription_id=self._config.subscription_id,
            api_version=api_version,
            content_type=content_type,
            json=_json,
            content=_content,
            headers=_headers,
            params=_params,
        )
        _request.url = self._client.format_url(_request.url)

        _stream = False
        pipeline_response: PipelineResponse = self._client._pipeline.run(  # pylint: disable=protected-access
            _request, stream=_stream, **kwargs
        )

        response = pipeline_response.http_response

        if response.status_code not in [200, 201]:
            map_error(status_code=response.status_code, response=response, error_map=error_map)
            error = self._deserialize.failsafe_deserialize(_models.ErrorResponseAutoGenerated5, pipeline_response)
            raise HttpResponseError(response=response, model=error, error_format=ARMErrorFormat)

        deserialized = self._deserialize("AzureMonitorWorkspaceResource", pipeline_response.http_response)

        if cls:
            return cls(pipeline_response, deserialized, {})  # type: ignore

        return deserialized  # type: ignore

    @overload
    def update(
        self,
        resource_group_name: str,
        azure_monitor_workspace_name: str,
        azure_monitor_workspace_properties: Optional[_models.AzureMonitorWorkspaceResourceForUpdate] = None,
        *,
        content_type: str = "application/json",
        **kwargs: Any
    ) -> _models.AzureMonitorWorkspaceResource:
        """Updates part of an Azure Monitor Workspace.

        :param resource_group_name: The name of the resource group. The name is case insensitive.
         Required.
        :type resource_group_name: str
        :param azure_monitor_workspace_name: The name of the Azure Monitor Workspace. The name is case
         insensitive. Required.
        :type azure_monitor_workspace_name: str
        :param azure_monitor_workspace_properties: The payload. Default value is None.
        :type azure_monitor_workspace_properties:
         ~azure.mgmt.monitor.models.AzureMonitorWorkspaceResourceForUpdate
        :keyword content_type: Body Parameter content-type. Content type parameter for JSON body.
         Default value is "application/json".
        :paramtype content_type: str
        :return: AzureMonitorWorkspaceResource or the result of cls(response)
        :rtype: ~azure.mgmt.monitor.models.AzureMonitorWorkspaceResource
        :raises ~azure.core.exceptions.HttpResponseError:
        """

    @overload
    def update(
        self,
        resource_group_name: str,
        azure_monitor_workspace_name: str,
        azure_monitor_workspace_properties: Optional[IO[bytes]] = None,
        *,
        content_type: str = "application/json",
        **kwargs: Any
    ) -> _models.AzureMonitorWorkspaceResource:
        """Updates part of an Azure Monitor Workspace.

        :param resource_group_name: The name of the resource group. The name is case insensitive.
         Required.
        :type resource_group_name: str
        :param azure_monitor_workspace_name: The name of the Azure Monitor Workspace. The name is case
         insensitive. Required.
        :type azure_monitor_workspace_name: str
        :param azure_monitor_workspace_properties: The payload. Default value is None.
        :type azure_monitor_workspace_properties: IO[bytes]
        :keyword content_type: Body Parameter content-type. Content type parameter for binary body.
         Default value is "application/json".
        :paramtype content_type: str
        :return: AzureMonitorWorkspaceResource or the result of cls(response)
        :rtype: ~azure.mgmt.monitor.models.AzureMonitorWorkspaceResource
        :raises ~azure.core.exceptions.HttpResponseError:
        """

    @distributed_trace
    def update(
        self,
        resource_group_name: str,
        azure_monitor_workspace_name: str,
        azure_monitor_workspace_properties: Optional[
            Union[_models.AzureMonitorWorkspaceResourceForUpdate, IO[bytes]]
        ] = None,
        **kwargs: Any
    ) -> _models.AzureMonitorWorkspaceResource:
        """Updates part of an Azure Monitor Workspace.

        :param resource_group_name: The name of the resource group. The name is case insensitive.
         Required.
        :type resource_group_name: str
        :param azure_monitor_workspace_name: The name of the Azure Monitor Workspace. The name is case
         insensitive. Required.
        :type azure_monitor_workspace_name: str
        :param azure_monitor_workspace_properties: The payload. Is either a
         AzureMonitorWorkspaceResourceForUpdate type or a IO[bytes] type. Default value is None.
        :type azure_monitor_workspace_properties:
         ~azure.mgmt.monitor.models.AzureMonitorWorkspaceResourceForUpdate or IO[bytes]
        :return: AzureMonitorWorkspaceResource or the result of cls(response)
        :rtype: ~azure.mgmt.monitor.models.AzureMonitorWorkspaceResource
        :raises ~azure.core.exceptions.HttpResponseError:
        """
        error_map: MutableMapping = {
            401: ClientAuthenticationError,
            404: ResourceNotFoundError,
            409: ResourceExistsError,
            304: ResourceNotModifiedError,
        }
        error_map.update(kwargs.pop("error_map", {}) or {})

        _headers = case_insensitive_dict(kwargs.pop("headers", {}) or {})
        _params = case_insensitive_dict(kwargs.pop("params", {}) or {})

        api_version: str = kwargs.pop("api_version", _params.pop("api-version", "2023-04-03"))
        content_type: Optional[str] = kwargs.pop("content_type", _headers.pop("Content-Type", None))
        cls: ClsType[_models.AzureMonitorWorkspaceResource] = kwargs.pop("cls", None)

        content_type = content_type or "application/json"
        _json = None
        _content = None
        if isinstance(azure_monitor_workspace_properties, (IOBase, bytes)):
            _content = azure_monitor_workspace_properties
        else:
            if azure_monitor_workspace_properties is not None:
                _json = self._serialize.body(
                    azure_monitor_workspace_properties, "AzureMonitorWorkspaceResourceForUpdate"
                )
            else:
                _json = None

        _request = build_update_request(
            resource_group_name=resource_group_name,
            azure_monitor_workspace_name=azure_monitor_workspace_name,
            subscription_id=self._config.subscription_id,
            api_version=api_version,
            content_type=content_type,
            json=_json,
            content=_content,
            headers=_headers,
            params=_params,
        )
        _request.url = self._client.format_url(_request.url)

        _stream = False
        pipeline_response: PipelineResponse = self._client._pipeline.run(  # pylint: disable=protected-access
            _request, stream=_stream, **kwargs
        )

        response = pipeline_response.http_response

        if response.status_code not in [200]:
            map_error(status_code=response.status_code, response=response, error_map=error_map)
            error = self._deserialize.failsafe_deserialize(_models.ErrorResponseAutoGenerated5, pipeline_response)
            raise HttpResponseError(response=response, model=error, error_format=ARMErrorFormat)

        deserialized = self._deserialize("AzureMonitorWorkspaceResource", pipeline_response.http_response)

        if cls:
            return cls(pipeline_response, deserialized, {})  # type: ignore

        return deserialized  # type: ignore

    def _delete_initial(
        self, resource_group_name: str, azure_monitor_workspace_name: str, **kwargs: Any
    ) -> Iterator[bytes]:
        error_map: MutableMapping = {
            401: ClientAuthenticationError,
            404: ResourceNotFoundError,
            409: ResourceExistsError,
            304: ResourceNotModifiedError,
        }
        error_map.update(kwargs.pop("error_map", {}) or {})

        _headers = kwargs.pop("headers", {}) or {}
        _params = case_insensitive_dict(kwargs.pop("params", {}) or {})

        api_version: str = kwargs.pop("api_version", _params.pop("api-version", "2023-04-03"))
        cls: ClsType[Iterator[bytes]] = kwargs.pop("cls", None)

        _request = build_delete_request(
            resource_group_name=resource_group_name,
            azure_monitor_workspace_name=azure_monitor_workspace_name,
            subscription_id=self._config.subscription_id,
            api_version=api_version,
            headers=_headers,
            params=_params,
        )
        _request.url = self._client.format_url(_request.url)

        _decompress = kwargs.pop("decompress", True)
        _stream = True
        pipeline_response: PipelineResponse = self._client._pipeline.run(  # pylint: disable=protected-access
            _request, stream=_stream, **kwargs
        )

        response = pipeline_response.http_response

        if response.status_code not in [202, 204]:
            try:
                response.read()  # Load the body in memory and close the socket
            except (StreamConsumedError, StreamClosedError):
                pass
            map_error(status_code=response.status_code, response=response, error_map=error_map)
            error = self._deserialize.failsafe_deserialize(_models.ErrorResponseAutoGenerated5, pipeline_response)
            raise HttpResponseError(response=response, model=error, error_format=ARMErrorFormat)

        response_headers = {}
        if response.status_code == 202:
            response_headers["Azure-AsyncOperation"] = self._deserialize(
                "str", response.headers.get("Azure-AsyncOperation")
            )
            response_headers["Location"] = self._deserialize("str", response.headers.get("Location"))

        deserialized = response.stream_download(self._client._pipeline, decompress=_decompress)

        if cls:
            return cls(pipeline_response, deserialized, response_headers)  # type: ignore

        return deserialized  # type: ignore

    @distributed_trace
    def begin_delete(
        self, resource_group_name: str, azure_monitor_workspace_name: str, **kwargs: Any
    ) -> LROPoller[None]:
        """Deletes an Azure Monitor Workspace.

        :param resource_group_name: The name of the resource group. The name is case insensitive.
         Required.
        :type resource_group_name: str
        :param azure_monitor_workspace_name: The name of the Azure Monitor Workspace. The name is case
         insensitive. Required.
        :type azure_monitor_workspace_name: str
        :return: An instance of LROPoller that returns either None or the result of cls(response)
        :rtype: ~azure.core.polling.LROPoller[None]
        :raises ~azure.core.exceptions.HttpResponseError:
        """
        _headers = kwargs.pop("headers", {}) or {}
        _params = case_insensitive_dict(kwargs.pop("params", {}) or {})

        api_version: str = kwargs.pop("api_version", _params.pop("api-version", "2023-04-03"))
        cls: ClsType[None] = kwargs.pop("cls", None)
        polling: Union[bool, PollingMethod] = kwargs.pop("polling", True)
        lro_delay = kwargs.pop("polling_interval", self._config.polling_interval)
        cont_token: Optional[str] = kwargs.pop("continuation_token", None)
        if cont_token is None:
            raw_result = self._delete_initial(
                resource_group_name=resource_group_name,
                azure_monitor_workspace_name=azure_monitor_workspace_name,
                api_version=api_version,
                cls=lambda x, y, z: x,
                headers=_headers,
                params=_params,
                **kwargs
            )
            raw_result.http_response.read()  # type: ignore
        kwargs.pop("error_map", None)

        def get_long_running_output(pipeline_response):  # pylint: disable=inconsistent-return-statements
            if cls:
                return cls(pipeline_response, None, {})  # type: ignore

        if polling is True:
            polling_method: PollingMethod = cast(
                PollingMethod, ARMPolling(lro_delay, lro_options={"final-state-via": "location"}, **kwargs)
            )
        elif polling is False:
            polling_method = cast(PollingMethod, NoPolling())
        else:
            polling_method = polling
        if cont_token:
            return LROPoller[None].from_continuation_token(
                polling_method=polling_method,
                continuation_token=cont_token,
                client=self._client,
                deserialization_callback=get_long_running_output,
            )
        return LROPoller[None](self._client, raw_result, get_long_running_output, polling_method)  # type: ignore
