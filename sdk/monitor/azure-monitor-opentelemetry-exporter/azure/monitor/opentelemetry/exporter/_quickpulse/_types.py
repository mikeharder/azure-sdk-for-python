# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
# pylint: disable=protected-access
from dataclasses import dataclass, fields
from typing import Dict, no_type_check

from opentelemetry.sdk._logs import LogRecord
from opentelemetry.sdk.trace import Event, ReadableSpan
from opentelemetry.semconv._incubating.attributes import gen_ai_attributes
from opentelemetry.semconv.attributes.http_attributes import (
    HTTP_REQUEST_METHOD,
    HTTP_RESPONSE_STATUS_CODE,
)
from opentelemetry.semconv.trace import SpanAttributes
from opentelemetry.trace import SpanKind

from azure.monitor.opentelemetry.exporter.export.trace import _utils as trace_utils


@dataclass
class _TelemetryData:
    custom_dimensions: Dict[str, str]

    @staticmethod
    def _from_span(span: ReadableSpan):
        if span.kind in (SpanKind.SERVER, SpanKind.CONSUMER):
            return _RequestData._from_span(span)
        return _DependencyData._from_span(span)

    @staticmethod
    @no_type_check
    def _from_log_record(log_record: LogRecord):
        exc_type = log_record.attributes.get(SpanAttributes.EXCEPTION_TYPE)
        exc_message = log_record.attributes.get(SpanAttributes.EXCEPTION_MESSAGE)
        if exc_type is not None or exc_message is not None:
            return _ExceptionData._from_log_record(log_record)
        return _TraceData._from_log_record(log_record)


@dataclass
class _RequestData(_TelemetryData):
    duration: float
    success: bool
    name: str
    response_code: int
    url: str

    @staticmethod
    @no_type_check
    def _from_span(span: ReadableSpan):
        # Logic should match that of exporter to Breeze
        url = ""
        duration_ms = 0
        response_code = 0
        success = True
        attributes = {}
        if span.end_time and span.start_time:
            duration_ms = (span.end_time - span.start_time) / 1e9
        if span.attributes:
            attributes = span.attributes
            url = trace_utils._get_url_for_http_request(attributes)
            status_code = attributes.get(HTTP_RESPONSE_STATUS_CODE) or \
                attributes.get(SpanAttributes.HTTP_STATUS_CODE)
            if status_code:
                try:
                    status_code = int(status_code)
                except ValueError:
                    status_code = 0
            else:
                status_code = 0
            success = span.status.is_ok and status_code and status_code not in range(400, 500)
            response_code = status_code
        return _RequestData(
            duration=duration_ms,
            success=success,
            name=span.name,
            response_code=response_code,
            url=url or "",
            custom_dimensions=attributes,
        )


@dataclass
class _DependencyData(_TelemetryData):
    duration: float
    success: bool
    name: str
    result_code: int
    target: str
    type: str
    data: str

    @staticmethod
    @no_type_check
    def _from_span(span: ReadableSpan):
        # Logic should match that of exporter to Breeze
        url = ""
        duration_ms = 0
        result_code = 0
        attributes = {}
        dependency_type = "InProc"
        data = ""
        target = ""
        if span.end_time and span.start_time:
            duration_ms = (span.end_time - span.start_time) / 1e9
        if span.attributes:
            attributes = span.attributes
            target = trace_utils._get_target_for_dependency_from_peer(attributes)
            if span.kind is SpanKind.CLIENT:
                if HTTP_REQUEST_METHOD in attributes or SpanAttributes.HTTP_METHOD in attributes:
                    dependency_type = "HTTP"
                    url = trace_utils._get_url_for_http_dependency(attributes)
                    target, _ = trace_utils._get_target_and_path_for_http_dependency(
                        attributes,
                        url,
                    )
                    data = url
                elif SpanAttributes.DB_SYSTEM in attributes:
                    db_system = attributes[SpanAttributes.DB_SYSTEM]
                    dependency_type = db_system
                    target = trace_utils._get_target_for_db_dependency(
                        target,
                        db_system,
                        attributes,
                    )
                    if SpanAttributes.DB_STATEMENT in attributes:
                        data = attributes[SpanAttributes.DB_STATEMENT]
                    elif SpanAttributes.DB_OPERATION in attributes:
                        data = attributes[SpanAttributes.DB_OPERATION]
                elif SpanAttributes.MESSAGING_SYSTEM in attributes:
                    dependency_type = attributes[SpanAttributes.MESSAGING_SYSTEM]
                    target = trace_utils._get_target_for_messaging_dependency(
                        target,
                        attributes,
                    )
                elif SpanAttributes.RPC_SYSTEM in attributes:
                    dependency_type = attributes[SpanAttributes.RPC_SYSTEM]
                    target = trace_utils._get_target_for_rpc_dependency(
                        target,
                        attributes,
                    )
                elif gen_ai_attributes.GEN_AI_SYSTEM in span.attributes:
                    dependency_type = attributes[gen_ai_attributes.GEN_AI_SYSTEM]
            elif span.kind is SpanKind.PRODUCER:
                dependency_type = "Queue Message"
                msg_system = attributes.get(SpanAttributes.MESSAGING_SYSTEM)
                if msg_system:
                    dependency_type += " | {}".format(msg_system)
            else:
                dependency_type = "InProc"

        return _DependencyData(
            duration=duration_ms,
            success=span.status.is_ok,
            name=span.name,
            result_code=result_code,
            target=target,
            type=str(dependency_type),
            data=data,
            custom_dimensions=attributes,
        )


@dataclass
class _ExceptionData(_TelemetryData):
    message: str
    stack_trace: str

    @staticmethod
    @no_type_check
    def _from_log_record(log_record: LogRecord):
        return _ExceptionData(
            message=str(log_record.attributes.get(SpanAttributes.EXCEPTION_MESSAGE, "")),
            stack_trace=str(log_record.attributes.get(SpanAttributes.EXCEPTION_STACKTRACE, "")),
            custom_dimensions=log_record.attributes,
        )

    @staticmethod
    @no_type_check
    def _from_span_event(span_event: Event):
        return _ExceptionData(
            message=str(span_event.attributes.get(SpanAttributes.EXCEPTION_MESSAGE, "")),
            stack_trace=str(span_event.attributes.get(SpanAttributes.EXCEPTION_STACKTRACE, "")),
            custom_dimensions=span_event.attributes,
        )


@dataclass
class _TraceData(_TelemetryData):
    message: str

    @staticmethod
    @no_type_check
    def _TraceData(log_record: LogRecord):
        return _TraceData(
            message=str(log_record.body),
            custom_dimensions=log_record.attributes,
        )

    @staticmethod
    @no_type_check
    def _from_log_record(log_record: LogRecord):
        return _TraceData(
            message=str(log_record.body),
            custom_dimensions=log_record.attributes,
        )


def _get_field_names(data_type: type):
    field_map = {}
    for field in fields(data_type):
        field_map[field.name.replace("_", "").lower()] = field.name
    return field_map


_DEPENDENCY_DATA_FIELD_NAMES = _get_field_names(_DependencyData)
_EXCEPTION_DATA_FIELD_NAMES = _get_field_names(_ExceptionData)
_REQUEST_DATA_FIELD_NAMES = _get_field_names(_RequestData)
_TRACE_DATA_FIELD_NAMES = _get_field_names(_TraceData)
_DATA_FIELD_NAMES = {
    _DependencyData: _DEPENDENCY_DATA_FIELD_NAMES,
    _ExceptionData: _EXCEPTION_DATA_FIELD_NAMES,
    _RequestData: _REQUEST_DATA_FIELD_NAMES,
    _TraceData: _TRACE_DATA_FIELD_NAMES,
}
_KNOWN_STRING_FIELD_NAMES = (
    "Url",
    "Name",
    "Target",
    "Type",
    "Data",
    "Message",
    "Exception.Message",
    "Exception.StackTrace",
)
