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
from __future__ import annotations
import logging
from typing import (
    Generic,
    TypeVar,
    Union,
    Any,
    List,
    Dict,
    Optional,
    Iterable,
    ContextManager,
)
from azure.core.pipeline import (
    PipelineRequest,
    PipelineResponse,
    PipelineContext,
)
from azure.core.pipeline.policies import HTTPPolicy, SansIOHTTPPolicy
from ._tools import await_result as _await_result
from .transport import HttpTransport

HTTPResponseType = TypeVar("HTTPResponseType")
HTTPRequestType = TypeVar("HTTPRequestType")

_LOGGER = logging.getLogger(__name__)


def cleanup_kwargs_for_transport(kwargs: Dict[str, str]) -> None:
    """Remove kwargs that are not meant for the transport layer.

    :param kwargs: The keyword arguments.
    :type kwargs: dict

    "insecure_domain_change" is used to indicate that a redirect
      has occurred to a different domain. This tells the SensitiveHeaderCleanupPolicy
      to clean up sensitive headers. We need to remove it before sending the request
      to the transport layer. This code is needed to handle the case that the
      SensitiveHeaderCleanupPolicy is not added into the pipeline and "insecure_domain_change" is not popped.
    "enable_cae" is added to the `get_token` method of the `TokenCredential` protocol.
    "tracing_options" is used in the DistributedTracingPolicy and tracing decorators.
    """
    kwargs_to_remove = ["insecure_domain_change", "enable_cae", "tracing_options"]
    if not kwargs:
        return
    for key in kwargs_to_remove:
        kwargs.pop(key, None)


class _SansIOHTTPPolicyRunner(HTTPPolicy[HTTPRequestType, HTTPResponseType]):
    """Sync implementation of the SansIO policy.

    Modifies the request and sends to the next policy in the chain.

    :param policy: A SansIO policy.
    :type policy: ~azure.core.pipeline.policies.SansIOHTTPPolicy
    """

    def __init__(self, policy: SansIOHTTPPolicy[HTTPRequestType, HTTPResponseType]) -> None:
        super(_SansIOHTTPPolicyRunner, self).__init__()
        self._policy = policy

    def send(self, request: PipelineRequest[HTTPRequestType]) -> PipelineResponse[HTTPRequestType, HTTPResponseType]:
        """Modifies the request and sends to the next policy in the chain.

        :param request: The PipelineRequest object.
        :type request: ~azure.core.pipeline.PipelineRequest
        :return: The PipelineResponse object.
        :rtype: ~azure.core.pipeline.PipelineResponse
        """
        _await_result(self._policy.on_request, request)
        try:
            response = self.next.send(request)
        except Exception:
            _await_result(self._policy.on_exception, request)
            raise
        _await_result(self._policy.on_response, request, response)
        return response


class _TransportRunner(HTTPPolicy[HTTPRequestType, HTTPResponseType]):
    """Transport runner.

    Uses specified HTTP transport type to send request and returns response.

    :param sender: The Http Transport instance.
    :type sender: ~azure.core.pipeline.transport.HttpTransport
    """

    def __init__(self, sender: HttpTransport[HTTPRequestType, HTTPResponseType]) -> None:
        super(_TransportRunner, self).__init__()
        self._sender = sender

    def send(self, request: PipelineRequest[HTTPRequestType]) -> PipelineResponse[HTTPRequestType, HTTPResponseType]:
        """HTTP transport send method.

        :param request: The PipelineRequest object.
        :type request: ~azure.core.pipeline.PipelineRequest
        :return: The PipelineResponse object.
        :rtype: ~azure.core.pipeline.PipelineResponse
        """
        cleanup_kwargs_for_transport(request.context.options)
        return PipelineResponse(
            request.http_request,
            self._sender.send(request.http_request, **request.context.options),
            context=request.context,
        )


class Pipeline(ContextManager["Pipeline"], Generic[HTTPRequestType, HTTPResponseType]):
    """A pipeline implementation.

    This is implemented as a context manager, that will activate the context
    of the HTTP sender. The transport is the last node in the pipeline.

    :param transport: The Http Transport instance
    :type transport: ~azure.core.pipeline.transport.HttpTransport
    :param list policies: List of configured policies.

    .. admonition:: Example:

        .. literalinclude:: ../samples/test_example_sync.py
            :start-after: [START build_pipeline]
            :end-before: [END build_pipeline]
            :language: python
            :dedent: 4
            :caption: Builds the pipeline for synchronous transport.
    """

    def __init__(
        self,
        transport: HttpTransport[HTTPRequestType, HTTPResponseType],
        policies: Optional[
            Iterable[
                Union[
                    HTTPPolicy[HTTPRequestType, HTTPResponseType],
                    SansIOHTTPPolicy[HTTPRequestType, HTTPResponseType],
                ]
            ]
        ] = None,
    ) -> None:
        self._impl_policies: List[HTTPPolicy[HTTPRequestType, HTTPResponseType]] = []
        self._transport = transport

        for policy in policies or []:
            if isinstance(policy, SansIOHTTPPolicy):
                self._impl_policies.append(_SansIOHTTPPolicyRunner(policy))
            elif policy:
                self._impl_policies.append(policy)
        for index in range(len(self._impl_policies) - 1):
            self._impl_policies[index].next = self._impl_policies[index + 1]
        if self._impl_policies:
            self._impl_policies[-1].next = _TransportRunner(self._transport)

    def __enter__(self) -> Pipeline[HTTPRequestType, HTTPResponseType]:
        self._transport.__enter__()
        return self

    def __exit__(self, *exc_details: Any) -> None:
        self._transport.__exit__(*exc_details)

    @staticmethod
    def _prepare_multipart_mixed_request(request: HTTPRequestType) -> None:
        """Will execute the multipart policies.

        Does nothing if "set_multipart_mixed" was never called.

        :param request: The request object.
        :type request: ~azure.core.rest.HttpRequest
        """
        multipart_mixed_info = request.multipart_mixed_info  # type: ignore
        if not multipart_mixed_info:
            return

        requests: List[HTTPRequestType] = multipart_mixed_info[0]
        policies: List[SansIOHTTPPolicy] = multipart_mixed_info[1]
        pipeline_options: Dict[str, Any] = multipart_mixed_info[3]

        # Apply on_requests concurrently to all requests
        import concurrent.futures

        def prepare_requests(req):
            if req.multipart_mixed_info:
                # Recursively update changeset "sub requests"
                Pipeline._prepare_multipart_mixed_request(req)
            context = PipelineContext(None, **pipeline_options)
            pipeline_request = PipelineRequest(req, context)
            for policy in policies:
                _await_result(policy.on_request, pipeline_request)

        with concurrent.futures.ThreadPoolExecutor() as executor:
            # List comprehension to raise exceptions if happened
            [  # pylint: disable=expression-not-assigned, unnecessary-comprehension
                _ for _ in executor.map(prepare_requests, requests)
            ]

    def _prepare_multipart(self, request: HTTPRequestType) -> None:
        # This code is fine as long as HTTPRequestType is actually
        # azure.core.pipeline.transport.HTTPRequest, bu we don't check it in here
        # since we didn't see (yet) pipeline usage where it's not this actual instance
        # class used
        self._prepare_multipart_mixed_request(request)
        request.prepare_multipart_body()  # type: ignore

    def run(self, request: HTTPRequestType, **kwargs: Any) -> PipelineResponse[HTTPRequestType, HTTPResponseType]:
        """Runs the HTTP Request through the chained policies.

        :param request: The HTTP request object.
        :type request: ~azure.core.pipeline.transport.HttpRequest
        :return: The PipelineResponse object
        :rtype: ~azure.core.pipeline.PipelineResponse
        """
        self._prepare_multipart(request)
        context = PipelineContext(self._transport, **kwargs)
        pipeline_request: PipelineRequest[HTTPRequestType] = PipelineRequest(request, context)
        first_node = self._impl_policies[0] if self._impl_policies else _TransportRunner(self._transport)
        return first_node.send(pipeline_request)
