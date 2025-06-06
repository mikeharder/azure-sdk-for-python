# coding=utf-8
# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------
"""Customize generated code here.

Follow our quickstart for examples: https://aka.ms/azsdk/python/dpcodegen/python/customize
"""
from copy import deepcopy
from enum import Enum
from typing import Any, IO, List, MutableMapping, overload, Union
from urllib.parse import urlparse

from azure.core import CaseInsensitiveEnumMeta
from azure.core.credentials import TokenCredential
from azure.core.pipeline.policies import HttpLoggingPolicy
from azure.core.polling import LROPoller
from azure.core.rest import HttpRequest, HttpResponse
from azure.core.tracing.decorator import distributed_trace

from ._client import SecurityDomainClient as KeyVaultClient
from ._internal import (
    ChallengeAuthPolicy,
    SecurityDomainDownloadNoPolling,
    SecurityDomainDownloadPolling,
    SecurityDomainDownloadPollingMethod,
    SecurityDomainUploadNoPolling,
    SecurityDomainUploadPolling,
    SecurityDomainUploadPollingMethod,
)
from .models import CertificateInfo, SecurityDomain
from ._utils.serialization import Serializer

JSON = MutableMapping[str, Any]  # pylint: disable=unsubscriptable-object

__all__: List[str] = [
    "SecurityDomainClient",
]  # Add all objects you want publicly available to users at this package level


class ApiVersion(str, Enum, metaclass=CaseInsensitiveEnumMeta):
    """Key Vault API versions supported by this package"""

    #: this is the default version
    V7_5 = "7.5"


DEFAULT_VERSION = ApiVersion.V7_5

_SERIALIZER = Serializer()
_SERIALIZER.client_side_validation = False


def _format_api_version(request: HttpRequest, api_version: str) -> HttpRequest:
    """Returns a request copy that includes an api-version query parameter if one wasn't originally present.

    :param request: The HTTP request being sent.
    :type request: ~azure.core.rest.HttpRequest
    :param str api_version: The service API version that the request should include.

    :returns: A copy of the request that includes an api-version query parameter.
    :rtype: ~azure.core.rest.HttpRequest
    """
    request_copy = deepcopy(request)
    params = {"api-version": api_version}  # By default, we want to use the client's API version
    query = urlparse(request_copy.url).query

    if query:
        request_copy.url = request_copy.url.partition("?")[0]
        existing_params = {p[0]: p[-1] for p in [p.partition("=") for p in query.split("&")]}
        params.update(existing_params)  # If an api-version was provided, this will overwrite our default

    # Reconstruct the query parameters onto the URL
    query_params = []
    for k, v in params.items():
        query_params.append("{}={}".format(k, v))
    query = "?" + "&".join(query_params)
    request_copy.url = request_copy.url + query
    return request_copy


class SecurityDomainClient(KeyVaultClient):
    """Manages the security domain of a Managed HSM.

    :param str vault_url: URL of the vault on which the client will operate. This is also called the vault's "DNS Name".
        You should validate that this URL references a valid Key Vault or Managed HSM resource.
        See https://aka.ms/azsdk/blog/vault-uri for details.
    :param credential: An object which can provide an access token for the vault, such as a credential from
        :mod:`azure.identity`
    :type credential: ~azure.core.credentials.TokenCredential

    :keyword str api_version: The API version to use for this operation. Default value is "7.5". Note that overriding
        this default value may result in unsupported behavior.
    :keyword bool verify_challenge_resource: Whether to verify the authentication challenge resource matches the Key
        Vault or Managed HSM domain. Defaults to True.
    """

    def __init__(self, vault_url: str, credential: TokenCredential, **kwargs: Any) -> None:
        self.api_version = kwargs.pop("api_version", DEFAULT_VERSION)
        # If API version was provided as an enum value, need to make a plain string for 3.11 compatibility
        if hasattr(self.api_version, "value"):
            self.api_version = self.api_version.value
        self._vault_url = vault_url.strip(" /")

        http_logging_policy = HttpLoggingPolicy(**kwargs)
        http_logging_policy.allowed_header_names.update(
            {"x-ms-keyvault-network-info", "x-ms-keyvault-region", "x-ms-keyvault-service-version"}
        )
        verify_challenge = kwargs.pop("verify_challenge_resource", True)
        super().__init__(
            vault_url,
            credential,
            api_version=self.api_version,
            authentication_policy=ChallengeAuthPolicy(credential, verify_challenge_resource=verify_challenge),
            http_logging_policy=http_logging_policy,
            **kwargs,
        )

    @overload
    def begin_download(
        self,
        certificate_info: CertificateInfo,
        *,
        content_type: str = "application/json",
        skip_activation_polling: bool = False,
        **kwargs: Any,
    ) -> LROPoller[SecurityDomain]: ...

    @overload
    def begin_download(
        self,
        certificate_info: JSON,
        *,
        content_type: str = "application/json",
        skip_activation_polling: bool = False,
        **kwargs: Any,
    ) -> LROPoller[SecurityDomain]: ...

    @overload
    def begin_download(
        self,
        certificate_info: IO[bytes],
        *,
        content_type: str = "application/json",
        skip_activation_polling: bool = False,
        **kwargs: Any,
    ) -> LROPoller[SecurityDomain]: ...

    @distributed_trace
    def begin_download(
        self,
        certificate_info: Union[CertificateInfo, JSON, IO[bytes]],
        *,
        content_type: str = "application/json",
        skip_activation_polling: bool = False,
        **kwargs: Any,
    ) -> LROPoller[SecurityDomain]:
        """Retrieves the Security Domain from the managed HSM. Calling this endpoint can
        be used to activate a provisioned managed HSM resource.

        :param certificate_info: The Security Domain download operation requires the customer to provide N
         certificates (minimum 3 and maximum 10) containing a public key in JWK format. Required in one of the
         following types: CertificateInfo, JSON, or IO[bytes].
        :type certificate_info: ~azure.keyvault.securitydomain.models.CertificateInfo or
         JSON or IO[bytes]
        :keyword str content_type: Body Parameter content-type. Content type parameter for JSON body.
         Default value is "application/json".
        :keyword bool skip_activation_polling: If set to True, the operation will not poll for HSM activation to
         complete and calling `.result()` on the poller will return the security domain object immediately. Default
         value is False.

        :return: An instance of LROPoller that returns SecurityDomain. The
         SecurityDomain is compatible with MutableMapping
        :rtype:
         ~azure.core.polling.LROPoller[~azure.keyvault.securitydomain.models.SecurityDomain]
        :raises ~azure.core.exceptions.HttpResponseError:
        """
        delay = kwargs.pop("polling_interval", self._config.polling_interval)
        polling_method = (
            SecurityDomainDownloadNoPolling()
            if skip_activation_polling
            else SecurityDomainDownloadPollingMethod(lro_algorithms=[SecurityDomainDownloadPolling()], timeout=delay)
        )
        return super()._begin_download(  # type: ignore[return-value]
            certificate_info,
            content_type=content_type,
            polling=polling_method,
            **kwargs,
        )

    @overload
    @distributed_trace
    def begin_upload(
        self,
        security_domain: SecurityDomain,
        *,
        content_type: str = "application/json",
        skip_activation_polling: bool = False,
        **kwargs: Any,
    ) -> LROPoller[None]: ...

    @overload
    @distributed_trace
    def begin_upload(
        self,
        security_domain: JSON,
        *,
        content_type: str = "application/json",
        skip_activation_polling: bool = False,
        **kwargs: Any,
    ) -> LROPoller[None]: ...

    @overload
    @distributed_trace
    def begin_upload(
        self,
        security_domain: IO[bytes],
        *,
        content_type: str = "application/json",
        skip_activation_polling: bool = False,
        **kwargs: Any,
    ) -> LROPoller[None]: ...

    @distributed_trace
    def begin_upload(
        self,
        security_domain: Union[SecurityDomain, JSON, IO[bytes]],
        *,
        content_type: str = "application/json",
        skip_activation_polling: bool = False,
        **kwargs: Any,
    ) -> LROPoller[None]:
        """Restore the provided Security Domain.

        :param security_domain: The Security Domain to be restored. Required in one of the following types:
         SecurityDomain, JSON, or IO[bytes].
        :type security_domain: ~azure.keyvault.securitydomain.models.SecurityDomain or JSON or
         IO[bytes]
        :keyword str content_type: Body Parameter content-type. Content type parameter for JSON body.
         Default value is "application/json".
        :keyword bool skip_activation_polling: If set to True, the operation will not poll for HSM activation to
         complete and calling `.result()` on the poller will return None immediately, or raise an exception in case of
         an error. Default value is False.

        :return: An instance of LROPoller that returns None.
        :rtype: ~azure.core.polling.LROPoller[None]
        :raises ~azure.core.exceptions.HttpResponseError:
        """
        delay = kwargs.pop("polling_interval", self._config.polling_interval)
        polling_method = (
            SecurityDomainUploadNoPolling()
            if skip_activation_polling
            else SecurityDomainUploadPollingMethod(lro_algorithms=[SecurityDomainUploadPolling()], timeout=delay)
        )
        return super()._begin_upload(  # type: ignore[return-value]
            security_domain,
            content_type=content_type,
            polling=polling_method,
            **kwargs,
        )

    @property
    def vault_url(self) -> str:
        return self._vault_url

    @distributed_trace
    def send_request(self, request: HttpRequest, *, stream: bool = False, **kwargs: Any) -> HttpResponse:
        """Runs a network request using the client's existing pipeline.

        The request URL can be relative to the vault URL. The service API version used for the request is the same as
        the client's unless otherwise specified. This method does not raise if the response is an error; to raise an
        exception, call `raise_for_status()` on the returned response object. For more information about how to send
        custom requests with this method, see https://aka.ms/azsdk/dpcodegen/python/send_request.

        :param request: The network request you want to make.
        :type request: ~azure.core.rest.HttpRequest

        :keyword bool stream: Whether the response payload will be streamed. Defaults to False.

        :return: The response of your network call. Does not do error handling on your response.
        :rtype: ~azure.core.rest.HttpResponse
        """
        request_copy = _format_api_version(request, self.api_version)
        path_format_arguments = {
            "vaultBaseUrl": _SERIALIZER.url("vault_base_url", self._vault_url, "str", skip_quote=True),
        }
        request_copy.url = self._client.format_url(request_copy.url, **path_format_arguments)
        return self._client.send_request(request_copy, stream=stream, **kwargs)


def patch_sdk():
    """Do not remove from this file.

    `patch_sdk` is a last resort escape hatch that allows you to do customizations
    you can't accomplish using the techniques described in
    https://aka.ms/azsdk/python/dpcodegen/python/customize
    """
