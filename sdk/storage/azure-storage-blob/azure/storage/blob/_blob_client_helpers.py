# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
# pylint: disable=too-many-lines

from io import BytesIO
from typing import (
    Any, AnyStr, AsyncGenerator, AsyncIterable, cast,
    Dict, IO, Iterable, List, Optional, Tuple, Union,
    TYPE_CHECKING
)
from urllib.parse import quote, unquote, urlparse

from ._deserialize import deserialize_blob_stream
from ._encryption import modify_user_agent_for_encryption, _ERROR_UNSUPPORTED_METHOD_FOR_ENCRYPTION
from ._generated.models import (
    AppendPositionAccessConditions,
    BlobHTTPHeaders,
    BlockList,
    BlockLookupList,
    CpkInfo,
    DeleteSnapshotsOptionType,
    QueryRequest,
    SequenceNumberAccessConditions
)
from ._models import (
    BlobBlock,
    BlobProperties,
    BlobType,
    DelimitedJsonDialect,
    DelimitedTextDialect,
    PremiumPageBlobTier,
    QuickQueryDialect
)
from ._serialize import (
    get_access_conditions,
    get_cpk_scope_info,
    get_modify_conditions,
    get_source_conditions,
    serialize_blob_tags_header,
    serialize_blob_tags,
    serialize_query_format
)
from ._shared import encode_base64
from ._shared.base_client import parse_query
from ._shared.request_handlers import (
    add_metadata_headers,
    get_length,
    read_length,
    validate_and_format_range_headers
)
from ._shared.response_handlers import return_headers_and_deserialized, return_response_headers
from ._shared.uploads import IterStreamer
from ._shared.uploads_async import AsyncIterStreamer
from ._upload_helpers import _any_conditions

if TYPE_CHECKING:
    from urllib.parse import ParseResult
    from ._generated import AzureBlobStorage
    from ._models import ContentSettings
    from ._shared.models import StorageConfiguration


def _parse_url(
    account_url: str,
    container_name: str,
    blob_name: str
) -> Tuple["ParseResult", Optional[str], Optional[str]]:
    try:
        if not account_url.lower().startswith('http'):
            account_url = "https://" + account_url
    except AttributeError as exc:
        raise ValueError("Account URL must be a string.") from exc
    parsed_url = urlparse(account_url.rstrip('/'))

    if not (container_name and blob_name):
        raise ValueError("Please specify a container name and blob name.")
    if not parsed_url.netloc:
        raise ValueError(f"Invalid URL: {account_url}")

    path_snapshot, sas_token = parse_query(parsed_url.query)

    return parsed_url, sas_token, path_snapshot

def _format_url(container_name: Union[bytes, str], scheme: str, blob_name: str, query_str: str, hostname: str) -> str:
    if isinstance(container_name, str):
        container_name = container_name.encode('UTF-8')
    return f"{scheme}://{hostname}/{quote(container_name)}/{quote(blob_name, safe='~/')}{query_str}"

def _encode_source_url(source_url: str) -> str:
    parsed_source_url = urlparse(source_url)
    source_scheme = parsed_source_url.scheme
    source_hostname = parsed_source_url.netloc.rstrip('/')
    source_path = unquote(parsed_source_url.path)
    source_query = parsed_source_url.query
    result = [f"{source_scheme}://{source_hostname}{quote(source_path, safe='~/')}"]
    if source_query:
        result.append(source_query)
    return '?'.join(result)

def _upload_blob_options(  # pylint:disable=too-many-statements
    data: Union[bytes, str, Iterable[AnyStr], AsyncIterable[AnyStr], IO[bytes]],
    blob_type: Union[str, BlobType],
    length: Optional[int],
    metadata: Optional[Dict[str, str]],
    encryption_options: Dict[str, Any],
    config: "StorageConfiguration",
    sdk_moniker: str,
    client: "AzureBlobStorage",
    **kwargs: Any
) -> Dict[str, Any]:
    encoding = kwargs.pop('encoding', 'UTF-8')
    if isinstance(data, str):
        data = data.encode(encoding)
    if length is None:
        length = get_length(data)
    if isinstance(data, bytes):
        data = data[:length]

    stream: Optional[Any] = None
    if isinstance(data, bytes):
        stream = BytesIO(data)
    elif hasattr(data, 'read'):
        stream = data
    elif hasattr(data, '__iter__') and not isinstance(data, (list, tuple, set, dict)):
        stream = IterStreamer(data, encoding=encoding)
    elif hasattr(data, '__aiter__'):
        stream = AsyncIterStreamer(cast(AsyncGenerator, data), encoding=encoding)
    else:
        raise TypeError(f"Unsupported data type: {type(data)}")

    validate_content = kwargs.pop('validate_content', False)
    content_settings = kwargs.pop('content_settings', None)
    overwrite = kwargs.pop('overwrite', False)
    max_concurrency = kwargs.pop('max_concurrency', 1)
    cpk = kwargs.pop('cpk', None)
    cpk_info = None
    if cpk:
        cpk_info = CpkInfo(encryption_key=cpk.key_value, encryption_key_sha256=cpk.key_hash,
                            encryption_algorithm=cpk.algorithm)
    kwargs['cpk_info'] = cpk_info

    headers = kwargs.pop('headers', {})
    headers.update(add_metadata_headers(metadata))
    kwargs['lease_access_conditions'] = get_access_conditions(kwargs.pop('lease', None))
    kwargs['modified_access_conditions'] = get_modify_conditions(kwargs)
    kwargs['cpk_scope_info'] = get_cpk_scope_info(kwargs)
    if content_settings:
        kwargs['blob_headers'] = BlobHTTPHeaders(
            blob_cache_control=content_settings.cache_control,
            blob_content_type=content_settings.content_type,
            blob_content_md5=content_settings.content_md5,
            blob_content_encoding=content_settings.content_encoding,
            blob_content_language=content_settings.content_language,
            blob_content_disposition=content_settings.content_disposition
        )
    kwargs['blob_tags_string'] = serialize_blob_tags_header(kwargs.pop('tags', None))
    kwargs['stream'] = stream
    kwargs['length'] = length
    kwargs['overwrite'] = overwrite
    kwargs['headers'] = headers
    kwargs['validate_content'] = validate_content
    kwargs['blob_settings'] = config
    kwargs['max_concurrency'] = max_concurrency
    kwargs['encryption_options'] = encryption_options
    # Add feature flag to user agent for encryption
    if encryption_options['key']:
        modify_user_agent_for_encryption(
            config.user_agent_policy.user_agent,
            sdk_moniker,
            encryption_options['version'],
            kwargs)

    if blob_type == BlobType.BlockBlob:
        kwargs['client'] = client.block_blob
    elif blob_type == BlobType.PageBlob:
        if (encryption_options['version'] == '2.0' and
            (encryption_options['required'] or encryption_options['key'] is not None)):
            raise ValueError("Encryption version 2.0 does not currently support page blobs.")
        kwargs['client'] = client.page_blob
    elif blob_type == BlobType.AppendBlob:
        if encryption_options['required'] or (encryption_options['key'] is not None):
            raise ValueError(_ERROR_UNSUPPORTED_METHOD_FOR_ENCRYPTION)
        kwargs['client'] = client.append_blob
    else:
        raise ValueError(f"Unsupported BlobType: {blob_type}")
    return kwargs

def _upload_blob_from_url_options(source_url: str, **kwargs: Any) -> Dict[str, Any]:
    metadata = kwargs.pop('metadata', None)
    headers = kwargs.pop('headers', {})
    headers.update(add_metadata_headers(metadata))
    source_url = _encode_source_url(source_url=source_url)
    tier = kwargs.pop('standard_blob_tier', None)
    overwrite = kwargs.pop('overwrite', False)
    content_settings = kwargs.pop('content_settings', None)
    source_authorization = kwargs.pop('source_authorization', None)
    source_token_intent = kwargs.pop('source_token_intent', None)
    if content_settings:
        kwargs['blob_http_headers'] = BlobHTTPHeaders(
            blob_cache_control=content_settings.cache_control,
            blob_content_type=content_settings.content_type,
            blob_content_md5=None,
            blob_content_encoding=content_settings.content_encoding,
            blob_content_language=content_settings.content_language,
            blob_content_disposition=content_settings.content_disposition
        )
    cpk = kwargs.pop('cpk', None)
    cpk_info = None
    if cpk:
        cpk_info = CpkInfo(encryption_key=cpk.key_value, encryption_key_sha256=cpk.key_hash,
                            encryption_algorithm=cpk.algorithm)

    options = {
        'copy_source_authorization': source_authorization,
        'file_request_intent': source_token_intent,
        'content_length': 0,
        'copy_source_blob_properties': kwargs.pop('include_source_blob_properties', True),
        'source_content_md5': kwargs.pop('source_content_md5', None),
        'copy_source': source_url,
        'modified_access_conditions': get_modify_conditions(kwargs),
        'blob_tags_string': serialize_blob_tags_header(kwargs.pop('tags', None)),
        'cls': return_response_headers,
        'lease_access_conditions': get_access_conditions(kwargs.pop('destination_lease', None)),
        'tier': tier.value if tier else None,
        'source_modified_access_conditions': get_source_conditions(kwargs),
        'cpk_info': cpk_info,
        'cpk_scope_info': get_cpk_scope_info(kwargs),
        'headers': headers,
    }
    options.update(kwargs)
    if not overwrite and not _any_conditions(**options):
        options['modified_access_conditions'].if_none_match = '*'
    return options

def _download_blob_options(
    blob_name: str,
    container_name: str,
    version_id: Optional[str],
    offset: Optional[int],
    length: Optional[int],
    encoding: Optional[str],
    encryption_options: Dict[str, Any],
    config: "StorageConfiguration",
    sdk_moniker: str,
    client: "AzureBlobStorage",
    **kwargs
) -> Dict[str, Any]:
    """Creates a dictionary containing the options for a download blob operation.

    :param str blob_name:
        The name of the blob.
    :param str container_name:
        The name of the container.
    :param Optional[str] version_id:
        The version id parameter is a value that, when present, specifies the version of the blob to download.
    :param Optional[int] offset:
        Start of byte range to use for downloading a section of the blob. Must be set if length is provided.
    :param Optional[int] length:
        Number of bytes to read from the stream. This is optional, but should be supplied for optimal performance.
    :param Optional[str] encoding:
        Encoding to decode the downloaded bytes. Default is None, i.e. no decoding.
    :param Dict[str, Any] encryption_options:
        The options for encryption, if enabled.
    :param StorageConfiguration config:
        The Storage configuration options.
    :param str sdk_moniker:
        The string representing the SDK package version.
    :param AzureBlobStorage client:
        The generated Blob Storage client.
    :return: A dictionary containing the download blob options.
    :rtype: Dict[str, Any]
    """
    if length is not None:
        if offset is None:
            raise ValueError("Offset must be provided if length is provided.")
        length = offset + length - 1  # Service actually uses an end-range inclusive index

    validate_content = kwargs.pop('validate_content', False)
    access_conditions = get_access_conditions(kwargs.pop('lease', None))
    mod_conditions = get_modify_conditions(kwargs)

    cpk = kwargs.pop('cpk', None)
    cpk_info = None
    if cpk:
        cpk_info = CpkInfo(encryption_key=cpk.key_value, encryption_key_sha256=cpk.key_hash,
                            encryption_algorithm=cpk.algorithm)

    # Add feature flag to user agent for encryption
    if encryption_options['key'] or encryption_options['resolver']:
        modify_user_agent_for_encryption(
            config.user_agent_policy.user_agent,
            sdk_moniker,
            encryption_options['version'],
            kwargs)

    options = {
        'clients': client,
        'config': config,
        'start_range': offset,
        'end_range': length,
        'version_id': version_id,
        'validate_content': validate_content,
        'encryption_options': {
            'required': encryption_options['required'],
            'key': encryption_options['key'],
            'resolver': encryption_options['resolver']},
        'lease_access_conditions': access_conditions,
        'modified_access_conditions': mod_conditions,
        'cpk_info': cpk_info,
        'download_cls': kwargs.pop('cls', None) or deserialize_blob_stream,
        'max_concurrency':kwargs.pop('max_concurrency', 1),
        'encoding': encoding,
        'timeout': kwargs.pop('timeout', None),
        'name': blob_name,
        'container': container_name}
    options.update(kwargs)
    return options

def _quick_query_options(snapshot: Optional[str], query_expression: str, **kwargs: Any ) -> Tuple[Dict[str, Any], str]:
    delimiter = '\n'
    input_format = kwargs.pop('blob_format', None)
    if input_format == QuickQueryDialect.DelimitedJson:
        input_format = DelimitedJsonDialect()
    if input_format == QuickQueryDialect.DelimitedText:
        input_format = DelimitedTextDialect()
    input_parquet_format = input_format == "ParquetDialect"
    if input_format and not input_parquet_format:
        try:
            delimiter = input_format.lineterminator
        except AttributeError:
            try:
                delimiter = input_format.delimiter
            except AttributeError as exc:
                raise ValueError("The Type of blob_format can only be DelimitedTextDialect or "
                                    "DelimitedJsonDialect or ParquetDialect") from exc
    output_format = kwargs.pop('output_format', None)
    if output_format == QuickQueryDialect.DelimitedJson:
        output_format = DelimitedJsonDialect()
    if output_format == QuickQueryDialect.DelimitedText:
        output_format = DelimitedTextDialect()
    if output_format:
        if output_format == "ParquetDialect":
            raise ValueError("ParquetDialect is invalid as an output format.")
        try:
            delimiter = output_format.lineterminator
        except AttributeError:
            try:
                delimiter = output_format.delimiter
            except AttributeError:
                pass
    else:
        output_format = input_format if not input_parquet_format else None
    query_request = QueryRequest(
        expression=query_expression,
        input_serialization=serialize_query_format(input_format),
        output_serialization=serialize_query_format(output_format)
    )
    access_conditions = get_access_conditions(kwargs.pop('lease', None))
    mod_conditions = get_modify_conditions(kwargs)

    cpk = kwargs.pop('cpk', None)
    cpk_info = None
    if cpk:
        cpk_info = CpkInfo(
            encryption_key=cpk.key_value,
            encryption_key_sha256=cpk.key_hash,
            encryption_algorithm=cpk.algorithm
        )
    options = {
        'query_request': query_request,
        'lease_access_conditions': access_conditions,
        'modified_access_conditions': mod_conditions,
        'cpk_info': cpk_info,
        'snapshot': snapshot,
        'timeout': kwargs.pop('timeout', None),
        'cls': return_headers_and_deserialized,
    }
    options.update({k: v for k, v in kwargs.items() if v is not None})
    return options, delimiter

def _generic_delete_blob_options(delete_snapshots: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]:
    access_conditions = get_access_conditions(kwargs.pop('lease', None))
    mod_conditions = get_modify_conditions(kwargs)
    if delete_snapshots:
        delete_snapshots = DeleteSnapshotsOptionType(delete_snapshots)
    options = {
        'timeout': kwargs.pop('timeout', None),
        'snapshot': kwargs.pop('snapshot', None),  # this is added for delete_blobs
        'delete_snapshots': delete_snapshots or None,
        'lease_access_conditions': access_conditions,
        'modified_access_conditions': mod_conditions}
    options.update(kwargs)
    return options

def _delete_blob_options(
    snapshot: Optional[str],
    version_id: Optional[str],
    delete_snapshots: Optional[str] = None,
    **kwargs: Any
) -> Dict[str, Any]:
    if snapshot and delete_snapshots:
        raise ValueError("The delete_snapshots option cannot be used with a specific snapshot.")
    options = _generic_delete_blob_options(delete_snapshots, **kwargs)
    options['snapshot'] = snapshot
    options['version_id'] = version_id
    options['blob_delete_type'] = kwargs.pop('blob_delete_type', None)
    return options

def _set_http_headers_options(content_settings: Optional["ContentSettings"] = None, **kwargs: Any) -> Dict[str, Any]:
    access_conditions = get_access_conditions(kwargs.pop('lease', None))
    mod_conditions = get_modify_conditions(kwargs)
    blob_headers = None
    if content_settings:
        blob_headers = BlobHTTPHeaders(
            blob_cache_control=content_settings.cache_control,
            blob_content_type=content_settings.content_type,
            blob_content_md5=content_settings.content_md5,
            blob_content_encoding=content_settings.content_encoding,
            blob_content_language=content_settings.content_language,
            blob_content_disposition=content_settings.content_disposition
        )
    options = {
        'timeout': kwargs.pop('timeout', None),
        'blob_http_headers': blob_headers,
        'lease_access_conditions': access_conditions,
        'modified_access_conditions': mod_conditions,
        'cls': return_response_headers}
    options.update(kwargs)
    return options

def _set_blob_metadata_options(metadata: Optional[Dict[str, str]] = None, **kwargs: Any):
    headers = kwargs.pop('headers', {})
    headers.update(add_metadata_headers(metadata))
    access_conditions = get_access_conditions(kwargs.pop('lease', None))
    mod_conditions = get_modify_conditions(kwargs)
    cpk_scope_info = get_cpk_scope_info(kwargs)

    cpk = kwargs.pop('cpk', None)
    cpk_info = None
    if cpk:
        cpk_info = CpkInfo(encryption_key=cpk.key_value, encryption_key_sha256=cpk.key_hash,
                            encryption_algorithm=cpk.algorithm)
    options = {
        'timeout': kwargs.pop('timeout', None),
        'lease_access_conditions': access_conditions,
        'modified_access_conditions': mod_conditions,
        'cpk_scope_info': cpk_scope_info,
        'cpk_info': cpk_info,
        'cls': return_response_headers,
        'headers': headers}
    options.update(kwargs)
    return options

def _create_page_blob_options(
    size: int,
    content_settings: Optional["ContentSettings"] = None,
    metadata: Optional[Dict[str, str]] = None,
    premium_page_blob_tier: Optional[Union[str, "PremiumPageBlobTier"]] = None,
    **kwargs: Any
) -> Dict[str, Any]:
    headers = kwargs.pop('headers', {})
    headers.update(add_metadata_headers(metadata))
    access_conditions = get_access_conditions(kwargs.pop('lease', None))
    mod_conditions = get_modify_conditions(kwargs)
    cpk_scope_info = get_cpk_scope_info(kwargs)
    blob_headers = None
    if content_settings:
        blob_headers = BlobHTTPHeaders(
            blob_cache_control=content_settings.cache_control,
            blob_content_type=content_settings.content_type,
            blob_content_md5=content_settings.content_md5,
            blob_content_encoding=content_settings.content_encoding,
            blob_content_language=content_settings.content_language,
            blob_content_disposition=content_settings.content_disposition
        )

    sequence_number = kwargs.pop('sequence_number', None)
    cpk = kwargs.pop('cpk', None)
    cpk_info = None
    if cpk:
        cpk_info = CpkInfo(encryption_key=cpk.key_value, encryption_key_sha256=cpk.key_hash,
                            encryption_algorithm=cpk.algorithm)

    immutability_policy = kwargs.pop('immutability_policy', None)
    if immutability_policy:
        kwargs['immutability_policy_expiry'] = immutability_policy.expiry_time
        kwargs['immutability_policy_mode'] = immutability_policy.policy_mode

    tier = None
    if premium_page_blob_tier:
        try:
            tier = premium_page_blob_tier.value  # type: ignore
        except AttributeError:
            tier = premium_page_blob_tier  # type: ignore

    blob_tags_string = serialize_blob_tags_header(kwargs.pop('tags', None))

    options = {
        'content_length': 0,
        'blob_content_length': size,
        'blob_sequence_number': sequence_number,
        'blob_http_headers': blob_headers,
        'timeout': kwargs.pop('timeout', None),
        'lease_access_conditions': access_conditions,
        'modified_access_conditions': mod_conditions,
        'cpk_scope_info': cpk_scope_info,
        'cpk_info': cpk_info,
        'blob_tags_string': blob_tags_string,
        'cls': return_response_headers,
        "tier": tier,
        'headers': headers}
    options.update(kwargs)
    return options

def _create_append_blob_options(
    content_settings: Optional["ContentSettings"] = None,
    metadata: Optional[Dict[str, str]] = None,
    **kwargs: Any
) -> Dict[str, Any]:
    headers = kwargs.pop('headers', {})
    headers.update(add_metadata_headers(metadata))
    access_conditions = get_access_conditions(kwargs.pop('lease', None))
    mod_conditions = get_modify_conditions(kwargs)
    cpk_scope_info = get_cpk_scope_info(kwargs)
    blob_headers = None
    if content_settings:
        blob_headers = BlobHTTPHeaders(
            blob_cache_control=content_settings.cache_control,
            blob_content_type=content_settings.content_type,
            blob_content_md5=content_settings.content_md5,
            blob_content_encoding=content_settings.content_encoding,
            blob_content_language=content_settings.content_language,
            blob_content_disposition=content_settings.content_disposition
        )

    cpk = kwargs.pop('cpk', None)
    cpk_info = None
    if cpk:
        cpk_info = CpkInfo(encryption_key=cpk.key_value, encryption_key_sha256=cpk.key_hash,
                            encryption_algorithm=cpk.algorithm)

    immutability_policy = kwargs.pop('immutability_policy', None)
    if immutability_policy:
        kwargs['immutability_policy_expiry'] = immutability_policy.expiry_time
        kwargs['immutability_policy_mode'] = immutability_policy.policy_mode

    blob_tags_string = serialize_blob_tags_header(kwargs.pop('tags', None))

    options = {
        'content_length': 0,
        'blob_http_headers': blob_headers,
        'timeout': kwargs.pop('timeout', None),
        'lease_access_conditions': access_conditions,
        'modified_access_conditions': mod_conditions,
        'cpk_scope_info': cpk_scope_info,
        'cpk_info': cpk_info,
        'blob_tags_string': blob_tags_string,
        'cls': return_response_headers,
        'headers': headers}
    options.update(kwargs)
    return options

def _create_snapshot_options(metadata: Optional[Dict[str, str]] = None, **kwargs: Any) -> Dict[str, Any]:
    headers = kwargs.pop('headers', {})
    headers.update(add_metadata_headers(metadata))
    access_conditions = get_access_conditions(kwargs.pop('lease', None))
    mod_conditions = get_modify_conditions(kwargs)
    cpk_scope_info = get_cpk_scope_info(kwargs)
    cpk = kwargs.pop('cpk', None)
    cpk_info = None
    if cpk:
        cpk_info = CpkInfo(encryption_key=cpk.key_value, encryption_key_sha256=cpk.key_hash,
                            encryption_algorithm=cpk.algorithm)

    options = {
        'timeout': kwargs.pop('timeout', None),
        'lease_access_conditions': access_conditions,
        'modified_access_conditions': mod_conditions,
        'cpk_scope_info': cpk_scope_info,
        'cpk_info': cpk_info,
        'cls': return_response_headers,
        'headers': headers}
    options.update(kwargs)
    return options

def _start_copy_from_url_options(  # pylint:disable=too-many-statements
    source_url: str,
    metadata: Optional[Dict[str, str]] = None,
    incremental_copy: bool = False,
    **kwargs: Any
) -> Dict[str, Any]:
    source_url = _encode_source_url(source_url=source_url)
    headers = kwargs.pop('headers', {})
    headers.update(add_metadata_headers(metadata))
    if 'source_lease' in kwargs:
        source_lease = kwargs.pop('source_lease')
        try:
            headers['x-ms-source-lease-id'] = source_lease.id
        except AttributeError:
            headers['x-ms-source-lease-id'] = source_lease

    tier = kwargs.pop('premium_page_blob_tier', None) or kwargs.pop('standard_blob_tier', None)
    tags = kwargs.pop('tags', None)

    # Options only available for sync copy
    requires_sync = kwargs.pop('requires_sync', None)
    encryption_scope_str = kwargs.pop('encryption_scope', None)
    source_authorization = kwargs.pop('source_authorization', None)
    source_token_intent = kwargs.pop('source_token_intent', None)
    # If tags is a str, interpret that as copy_source_tags
    copy_source_tags = isinstance(tags, str)

    if incremental_copy:
        if source_authorization:
            raise ValueError("Source authorization tokens are not applicable for incremental copying.")
        if copy_source_tags:
            raise ValueError("Copying source tags is not applicable for incremental copying.")

    # TODO: refactor start_copy_from_url api in _blob_client.py. Call _generated/_blob_operations.py copy_from_url
    #  when requires_sync=True is set.
    #  Currently both sync copy and async copy are calling _generated/_blob_operations.py start_copy_from_url.
    #  As sync copy diverges more from async copy, more problem will surface.
    if requires_sync is True:
        headers['x-ms-requires-sync'] = str(requires_sync)
        if encryption_scope_str:
            headers['x-ms-encryption-scope'] = encryption_scope_str
        if source_authorization:
            headers['x-ms-copy-source-authorization'] = source_authorization
        if source_token_intent:
            headers['x-ms-file-request-intent'] = source_token_intent
        if copy_source_tags:
            headers['x-ms-copy-source-tag-option'] = tags
    else:
        if encryption_scope_str:
            raise ValueError(
                "Encryption_scope is only supported for sync copy, please specify requires_sync=True")
        if source_authorization:
            raise ValueError(
                "Source authorization tokens are only supported for sync copy, please specify requires_sync=True")
        if source_token_intent:
            raise ValueError(
                "Source token intent is only supported for sync copy, please specify requires_sync=True")
        if copy_source_tags:
            raise ValueError(
                "Copying source tags is only supported for sync copy, please specify requires_sync=True")

    timeout = kwargs.pop('timeout', None)
    dest_mod_conditions = get_modify_conditions(kwargs)
    blob_tags_string = serialize_blob_tags_header(tags) if not copy_source_tags else None

    immutability_policy = kwargs.pop('immutability_policy', None)
    if immutability_policy:
        kwargs['immutability_policy_expiry'] = immutability_policy.expiry_time
        kwargs['immutability_policy_mode'] = immutability_policy.policy_mode

    options = {
        'copy_source': source_url,
        'timeout': timeout,
        'modified_access_conditions': dest_mod_conditions,
        'headers': headers,
        'cls': return_response_headers,
    }

    if not incremental_copy:
        source_mod_conditions = get_source_conditions(kwargs)
        dest_access_conditions = get_access_conditions(kwargs.pop('destination_lease', None))
        options['source_modified_access_conditions'] = source_mod_conditions
        options['lease_access_conditions'] = dest_access_conditions
        options['tier'] = tier.value if tier else None
        options['seal_blob'] = kwargs.pop('seal_destination_blob', None)
        options['blob_tags_string'] = blob_tags_string
    options.update(kwargs)
    return options

def _abort_copy_options(copy_id: Union[str, Dict[str, Any], BlobProperties], **kwargs: Any) -> Dict[str, Any]:
    access_conditions = get_access_conditions(kwargs.pop('lease', None))
    if isinstance(copy_id, BlobProperties):
        copy_id = copy_id.copy.id  # type: ignore [assignment]
    elif isinstance(copy_id, dict):
        copy_id = copy_id['copy_id']
    options = {
        'copy_id': copy_id,
        'lease_access_conditions': access_conditions,
        'timeout': kwargs.pop('timeout', None)}
    options.update(kwargs)
    return options

def _stage_block_options(
    block_id: str,
    data: Union[bytes, str, Iterable[AnyStr], IO[AnyStr]],
    length: Optional[int] = None,
    **kwargs: Any
) -> Dict[str, Any]:
    block_id = encode_base64(str(block_id))
    if isinstance(data, str):
        data = data.encode(kwargs.pop('encoding', 'UTF-8'))  # type: ignore
    access_conditions = get_access_conditions(kwargs.pop('lease', None))
    if length is None:
        length = get_length(data)
        if length is None:
            length, data = read_length(data)
    if isinstance(data, bytes):
        data = data[:length]

    validate_content = kwargs.pop('validate_content', False)
    cpk_scope_info = get_cpk_scope_info(kwargs)
    cpk = kwargs.pop('cpk', None)
    cpk_info = None
    if cpk:
        cpk_info = CpkInfo(encryption_key=cpk.key_value, encryption_key_sha256=cpk.key_hash,
                            encryption_algorithm=cpk.algorithm)

    options = {
        'block_id': block_id,
        'content_length': length,
        'body': data,
        'transactional_content_md5': None,
        'timeout': kwargs.pop('timeout', None),
        'lease_access_conditions': access_conditions,
        'validate_content': validate_content,
        'cpk_scope_info': cpk_scope_info,
        'cpk_info': cpk_info,
        'cls': return_response_headers,
    }
    options.update(kwargs)
    return options

def _stage_block_from_url_options(
    block_id: str,
    source_url: str,
    source_offset: Optional[int] = None,
    source_length: Optional[int] = None,
    source_content_md5: Optional[Union[bytes, bytearray]] = None,
    **kwargs: Any
) -> Dict[str, Any]:
    source_url = _encode_source_url(source_url=source_url)
    source_authorization = kwargs.pop('source_authorization', None)
    source_token_intent = kwargs.pop('source_token_intent', None)
    if source_length is not None and source_offset is None:
        raise ValueError("Source offset value must not be None if length is set.")
    if source_length is not None and source_offset is not None:
        source_length = source_offset + source_length - 1
    block_id = encode_base64(str(block_id))
    access_conditions = get_access_conditions(kwargs.pop('lease', None))
    range_header = None
    if source_offset is not None:
        range_header, _ = validate_and_format_range_headers(source_offset, source_length)

    cpk_scope_info = get_cpk_scope_info(kwargs)
    cpk = kwargs.pop('cpk', None)
    cpk_info = None
    if cpk:
        cpk_info = CpkInfo(encryption_key=cpk.key_value, encryption_key_sha256=cpk.key_hash,
                            encryption_algorithm=cpk.algorithm)
    options = {
        'copy_source_authorization': source_authorization,
        'file_request_intent': source_token_intent,
        'block_id': block_id,
        'content_length': 0,
        'source_url': source_url,
        'source_range': range_header,
        'source_content_md5': bytearray(source_content_md5) if source_content_md5 else None,
        'timeout': kwargs.pop('timeout', None),
        'lease_access_conditions': access_conditions,
        'cpk_scope_info': cpk_scope_info,
        'cpk_info': cpk_info,
        'cls': return_response_headers,
    }
    options.update(kwargs)
    return options

def _get_block_list_result(blocks: BlockList) -> Tuple[List[BlobBlock], List[BlobBlock]]:
    committed = []
    uncommitted = []
    if blocks.committed_blocks:
        committed = [BlobBlock._from_generated(b) for b in blocks.committed_blocks]  # pylint: disable=protected-access
    if blocks.uncommitted_blocks:
        uncommitted = [BlobBlock._from_generated(b) for b in blocks.uncommitted_blocks]  # pylint: disable=protected-access
    return committed, uncommitted

def _commit_block_list_options(
    block_list: List[BlobBlock],
    content_settings: Optional["ContentSettings"] = None,
    metadata: Optional[Dict[str, str]] = None,
    **kwargs: Any
) -> Dict[str, Any]:
    block_lookup = BlockLookupList(committed=[], uncommitted=[], latest=[])
    for block in block_list:
        if isinstance(block, BlobBlock):
            if block.state.value == 'committed':
                cast(List[str], block_lookup.committed).append(encode_base64(str(block.id)))
            elif block.state.value == 'uncommitted':
                cast(List[str], block_lookup.uncommitted).append(encode_base64(str(block.id)))
            elif block_lookup.latest is not None:
                block_lookup.latest.append(encode_base64(str(block.id)))
        else:
            block_lookup.latest.append(encode_base64(str(block)))
    headers = kwargs.pop('headers', {})
    headers.update(add_metadata_headers(metadata))
    blob_headers = None
    access_conditions = get_access_conditions(kwargs.pop('lease', None))
    mod_conditions = get_modify_conditions(kwargs)
    if content_settings:
        blob_headers = BlobHTTPHeaders(
            blob_cache_control=content_settings.cache_control,
            blob_content_type=content_settings.content_type,
            blob_content_md5=content_settings.content_md5,
            blob_content_encoding=content_settings.content_encoding,
            blob_content_language=content_settings.content_language,
            blob_content_disposition=content_settings.content_disposition
        )

    validate_content = kwargs.pop('validate_content', False)
    cpk_scope_info = get_cpk_scope_info(kwargs)
    cpk = kwargs.pop('cpk', None)
    cpk_info = None
    if cpk:
        cpk_info = CpkInfo(encryption_key=cpk.key_value, encryption_key_sha256=cpk.key_hash,
                            encryption_algorithm=cpk.algorithm)

    immutability_policy = kwargs.pop('immutability_policy', None)
    if immutability_policy:
        kwargs['immutability_policy_expiry'] = immutability_policy.expiry_time
        kwargs['immutability_policy_mode'] = immutability_policy.policy_mode

    tier = kwargs.pop('standard_blob_tier', None)
    blob_tags_string = serialize_blob_tags_header(kwargs.pop('tags', None))

    options = {
        'blocks': block_lookup,
        'blob_http_headers': blob_headers,
        'lease_access_conditions': access_conditions,
        'timeout': kwargs.pop('timeout', None),
        'modified_access_conditions': mod_conditions,
        'cls': return_response_headers,
        'validate_content': validate_content,
        'cpk_scope_info': cpk_scope_info,
        'cpk_info': cpk_info,
        'tier': tier.value if tier else None,
        'blob_tags_string': blob_tags_string,
        'headers': headers
    }
    options.update(kwargs)
    return options

def _set_blob_tags_options(
    version_id: Optional[str],
    tags: Optional[Dict[str, str]] = None,
    **kwargs: Any
)-> Dict[str, Any]:
    serialized_tags = serialize_blob_tags(tags)
    access_conditions = get_access_conditions(kwargs.pop('lease', None))
    mod_conditions = get_modify_conditions(kwargs)

    options = {
        'tags': serialized_tags,
        'lease_access_conditions': access_conditions,
        'modified_access_conditions': mod_conditions,
        'version_id': version_id,
        'cls': return_response_headers}
    options.update(kwargs)
    return options

def _get_blob_tags_options(version_id: Optional[str], snapshot: Optional[str], **kwargs: Any) -> Dict[str, Any]:
    access_conditions = get_access_conditions(kwargs.pop('lease', None))
    mod_conditions = get_modify_conditions(kwargs)

    options = {
        'version_id': version_id,
        'snapshot': snapshot,
        'lease_access_conditions': access_conditions,
        'modified_access_conditions': mod_conditions,
        'timeout': kwargs.pop('timeout', None),
        'cls': return_headers_and_deserialized}
    return options

def _get_page_ranges_options(
    snapshot: Optional[str],
    offset: Optional[int] = None,
    length: Optional[int] = None,
    previous_snapshot_diff: Optional[Union[str, Dict[str, Any]]] = None,
    **kwargs: Any
) -> Dict[str, Any]:
    access_conditions = get_access_conditions(kwargs.pop('lease', None))
    mod_conditions = get_modify_conditions(kwargs)
    if length is not None and offset is None:
        raise ValueError("Offset value must not be None if length is set.")
    if length is not None and offset is not None:
        length = offset + length - 1  # Reformat to an inclusive range index
    page_range, _ = validate_and_format_range_headers(
        offset, length, start_range_required=False, end_range_required=False, align_to_page=True
    )
    options = {
        'snapshot': snapshot,
        'lease_access_conditions': access_conditions,
        'modified_access_conditions': mod_conditions,
        'timeout': kwargs.pop('timeout', None),
        'range': page_range}
    if previous_snapshot_diff:
        try:
            options['prevsnapshot'] = previous_snapshot_diff.snapshot # type: ignore
        except AttributeError:
            try:
                options['prevsnapshot'] = previous_snapshot_diff['snapshot'] # type: ignore
            except TypeError:
                options['prevsnapshot'] = previous_snapshot_diff
    options.update(kwargs)
    return options

def _set_sequence_number_options(
    sequence_number_action: str,
    sequence_number: Optional[str] = None,
    **kwargs: Any
) -> Dict[str, Any]:
    access_conditions = get_access_conditions(kwargs.pop('lease', None))
    mod_conditions = get_modify_conditions(kwargs)
    if sequence_number_action is None:
        raise ValueError("A sequence number action must be specified")
    options = {
        'sequence_number_action': sequence_number_action,
        'timeout': kwargs.pop('timeout', None),
        'blob_sequence_number': sequence_number,
        'lease_access_conditions': access_conditions,
        'modified_access_conditions': mod_conditions,
        'cls': return_response_headers}
    options.update(kwargs)
    return options

def _resize_blob_options(size: int, **kwargs: Any) -> Dict[str, Any]:
    access_conditions = get_access_conditions(kwargs.pop('lease', None))
    mod_conditions = get_modify_conditions(kwargs)
    if size is None:
        raise ValueError("A content length must be specified for a Page Blob.")

    cpk = kwargs.pop('cpk', None)
    cpk_info = None
    if cpk:
        cpk_info = CpkInfo(encryption_key=cpk.key_value, encryption_key_sha256=cpk.key_hash,
                            encryption_algorithm=cpk.algorithm)
    options = {
        'blob_content_length': size,
        'timeout': kwargs.pop('timeout', None),
        'lease_access_conditions': access_conditions,
        'modified_access_conditions': mod_conditions,
        'cpk_info': cpk_info,
        'cls': return_response_headers}
    options.update(kwargs)
    return options

def _upload_page_options(
    page: bytes,
    offset: int,
    length: int,
    **kwargs: Any
) -> Dict[str, Any]:
    if isinstance(page, str):
        page = page.encode(kwargs.pop('encoding', 'UTF-8'))
    if offset is None or offset % 512 != 0:
        raise ValueError("offset must be an integer that aligns with 512 page size")
    if length is None or length % 512 != 0:
        raise ValueError("length must be an integer that aligns with 512 page size")
    end_range = offset + length - 1  # Reformat to an inclusive range index
    content_range = f'bytes={offset}-{end_range}' # type: ignore
    access_conditions = get_access_conditions(kwargs.pop('lease', None))
    seq_conditions = SequenceNumberAccessConditions(
        if_sequence_number_less_than_or_equal_to=kwargs.pop('if_sequence_number_lte', None),
        if_sequence_number_less_than=kwargs.pop('if_sequence_number_lt', None),
        if_sequence_number_equal_to=kwargs.pop('if_sequence_number_eq', None)
    )
    mod_conditions = get_modify_conditions(kwargs)
    cpk_scope_info = get_cpk_scope_info(kwargs)
    validate_content = kwargs.pop('validate_content', False)
    cpk = kwargs.pop('cpk', None)
    cpk_info = None
    if cpk:
        cpk_info = CpkInfo(encryption_key=cpk.key_value, encryption_key_sha256=cpk.key_hash,
                            encryption_algorithm=cpk.algorithm)
    options = {
        'body': page[:length],
        'content_length': length,
        'transactional_content_md5': None,
        'timeout': kwargs.pop('timeout', None),
        'range': content_range,
        'lease_access_conditions': access_conditions,
        'sequence_number_access_conditions': seq_conditions,
        'modified_access_conditions': mod_conditions,
        'validate_content': validate_content,
        'cpk_scope_info': cpk_scope_info,
        'cpk_info': cpk_info,
        'cls': return_response_headers}
    options.update(kwargs)
    return options

def _upload_pages_from_url_options(
    source_url: str,
    offset: int,
    length: int,
    source_offset: int,
    **kwargs: Any
) -> Dict[str, Any]:
    source_url = _encode_source_url(source_url=source_url)
    # TODO: extract the code to a method format_range
    if offset is None or offset % 512 != 0:
        raise ValueError("offset must be an integer that aligns with 512 page size")
    if length is None or length % 512 != 0:
        raise ValueError("length must be an integer that aligns with 512 page size")
    if source_offset is None or offset % 512 != 0:
        raise ValueError("source_offset must be an integer that aligns with 512 page size")

    # Format range
    end_range = offset + length - 1
    destination_range = f'bytes={offset}-{end_range}'
    source_range = f'bytes={source_offset}-{source_offset + length - 1}'  # should subtract 1 here?

    seq_conditions = SequenceNumberAccessConditions(
        if_sequence_number_less_than_or_equal_to=kwargs.pop('if_sequence_number_lte', None),
        if_sequence_number_less_than=kwargs.pop('if_sequence_number_lt', None),
        if_sequence_number_equal_to=kwargs.pop('if_sequence_number_eq', None)
    )
    source_authorization = kwargs.pop('source_authorization', None)
    source_token_intent = kwargs.pop('source_token_intent', None)
    access_conditions = get_access_conditions(kwargs.pop('lease', None))
    mod_conditions = get_modify_conditions(kwargs)
    source_mod_conditions = get_source_conditions(kwargs)
    cpk_scope_info = get_cpk_scope_info(kwargs)
    source_content_md5 = kwargs.pop('source_content_md5', None)
    cpk = kwargs.pop('cpk', None)
    cpk_info = None
    if cpk:
        cpk_info = CpkInfo(encryption_key=cpk.key_value, encryption_key_sha256=cpk.key_hash,
                            encryption_algorithm=cpk.algorithm)

    options = {
        'copy_source_authorization': source_authorization,
        'file_request_intent': source_token_intent,
        'source_url': source_url,
        'content_length': 0,
        'source_range': source_range,
        'range': destination_range,
        'source_content_md5': bytearray(source_content_md5) if source_content_md5 else None,
        'timeout': kwargs.pop('timeout', None),
        'lease_access_conditions': access_conditions,
        'sequence_number_access_conditions': seq_conditions,
        'modified_access_conditions': mod_conditions,
        'source_modified_access_conditions': source_mod_conditions,
        'cpk_scope_info': cpk_scope_info,
        'cpk_info': cpk_info,
        'cls': return_response_headers}
    options.update(kwargs)
    return options

def _clear_page_options(
    offset: int,
    length: int,
    **kwargs: Any
) -> Dict[str, Any]:
    access_conditions = get_access_conditions(kwargs.pop('lease', None))
    seq_conditions = SequenceNumberAccessConditions(
        if_sequence_number_less_than_or_equal_to=kwargs.pop('if_sequence_number_lte', None),
        if_sequence_number_less_than=kwargs.pop('if_sequence_number_lt', None),
        if_sequence_number_equal_to=kwargs.pop('if_sequence_number_eq', None)
    )
    mod_conditions = get_modify_conditions(kwargs)
    if offset is None or offset % 512 != 0:
        raise ValueError("offset must be an integer that aligns with 512 page size")
    if length is None or length % 512 != 0:
        raise ValueError("length must be an integer that aligns with 512 page size")
    end_range = length + offset - 1  # Reformat to an inclusive range index
    content_range = f'bytes={offset}-{end_range}'

    cpk = kwargs.pop('cpk', None)
    cpk_info = None
    if cpk:
        cpk_info = CpkInfo(encryption_key=cpk.key_value, encryption_key_sha256=cpk.key_hash,
                            encryption_algorithm=cpk.algorithm)

    options = {
        'content_length': 0,
        'timeout': kwargs.pop('timeout', None),
        'range': content_range,
        'lease_access_conditions': access_conditions,
        'sequence_number_access_conditions': seq_conditions,
        'modified_access_conditions': mod_conditions,
        'cpk_info': cpk_info,
        'cls': return_response_headers}
    options.update(kwargs)
    return options

def _append_block_options(
    data: Union[bytes, str, Iterable[AnyStr], IO[AnyStr]],
    length: Optional[int] = None,
    **kwargs: Any
) -> Dict[str, Any]:
    if isinstance(data, str):
        data = data.encode(kwargs.pop('encoding', 'UTF-8'))
    if length is None:
        length = get_length(data)
        if length is None:
            length, data = read_length(data)
    if length == 0:
        return {}
    if isinstance(data, bytes):
        data = data[:length]

    appendpos_condition = kwargs.pop('appendpos_condition', None)
    maxsize_condition = kwargs.pop('maxsize_condition', None)
    validate_content = kwargs.pop('validate_content', False)
    append_conditions = None
    if maxsize_condition or appendpos_condition is not None:
        append_conditions = AppendPositionAccessConditions(
            max_size=maxsize_condition,
            append_position=appendpos_condition
        )
    access_conditions = get_access_conditions(kwargs.pop('lease', None))
    mod_conditions = get_modify_conditions(kwargs)
    cpk_scope_info = get_cpk_scope_info(kwargs)
    cpk = kwargs.pop('cpk', None)
    cpk_info = None
    if cpk:
        cpk_info = CpkInfo(encryption_key=cpk.key_value, encryption_key_sha256=cpk.key_hash,
                            encryption_algorithm=cpk.algorithm)
    options = {
        'body': data,
        'content_length': length,
        'timeout': kwargs.pop('timeout', None),
        'transactional_content_md5': None,
        'lease_access_conditions': access_conditions,
        'append_position_access_conditions': append_conditions,
        'modified_access_conditions': mod_conditions,
        'validate_content': validate_content,
        'cpk_scope_info': cpk_scope_info,
        'cpk_info': cpk_info,
        'cls': return_response_headers}
    options.update(kwargs)
    return options

def _append_block_from_url_options(
    copy_source_url: str,
    source_offset: Optional[int] = None,
    source_length: Optional[int] = None,
    **kwargs: Any
) -> Dict[str, Any]:
    copy_source_url = _encode_source_url(source_url=copy_source_url)
    # If end range is provided, start range must be provided
    if source_length is not None and source_offset is None:
        raise ValueError("source_offset should also be specified if source_length is specified")
    # Format based on whether length is present
    source_range = None
    if source_length is not None and source_offset is not None:
        end_range = source_offset + source_length - 1
        source_range = f'bytes={source_offset}-{end_range}'
    elif source_offset is not None:
        source_range = f"bytes={source_offset}-"

    appendpos_condition = kwargs.pop('appendpos_condition', None)
    maxsize_condition = kwargs.pop('maxsize_condition', None)
    source_content_md5 = kwargs.pop('source_content_md5', None)
    append_conditions = None
    if maxsize_condition or appendpos_condition is not None:
        append_conditions = AppendPositionAccessConditions(
            max_size=maxsize_condition,
            append_position=appendpos_condition
        )
    source_authorization = kwargs.pop('source_authorization', None)
    source_token_intent = kwargs.pop('source_token_intent', None)
    access_conditions = get_access_conditions(kwargs.pop('lease', None))
    mod_conditions = get_modify_conditions(kwargs)
    source_mod_conditions = get_source_conditions(kwargs)
    cpk_scope_info = get_cpk_scope_info(kwargs)
    cpk = kwargs.pop('cpk', None)
    cpk_info = None
    if cpk:
        cpk_info = CpkInfo(encryption_key=cpk.key_value, encryption_key_sha256=cpk.key_hash,
                            encryption_algorithm=cpk.algorithm)

    options = {
        'copy_source_authorization': source_authorization,
        'file_request_intent': source_token_intent,
        'source_url': copy_source_url,
        'content_length': 0,
        'source_range': source_range,
        'source_content_md5': source_content_md5,
        'transactional_content_md5': None,
        'lease_access_conditions': access_conditions,
        'append_position_access_conditions': append_conditions,
        'modified_access_conditions': mod_conditions,
        'source_modified_access_conditions': source_mod_conditions,
        'cpk_scope_info': cpk_scope_info,
        'cpk_info': cpk_info,
        'cls': return_response_headers,
        'timeout': kwargs.pop('timeout', None)}
    options.update(kwargs)
    return options

def _seal_append_blob_options(**kwargs: Any) -> Dict[str, Any]:
    appendpos_condition = kwargs.pop('appendpos_condition', None)
    append_conditions = None
    if appendpos_condition is not None:
        append_conditions = AppendPositionAccessConditions(
            append_position=appendpos_condition
        )
    access_conditions = get_access_conditions(kwargs.pop('lease', None))
    mod_conditions = get_modify_conditions(kwargs)

    options = {
        'timeout': kwargs.pop('timeout', None),
        'lease_access_conditions': access_conditions,
        'append_position_access_conditions': append_conditions,
        'modified_access_conditions': mod_conditions,
        'cls': return_response_headers}
    options.update(kwargs)
    return options

def _from_blob_url(
    blob_url: str,
    snapshot: Optional[Union[BlobProperties, str, Dict[str, Any]]]
) -> Tuple[str, str, str, Optional[str]]:
    try:
        if not blob_url.lower().startswith('http'):
            blob_url = "https://" + blob_url
    except AttributeError as exc:
        raise ValueError("Blob URL must be a string.") from exc
    parsed_url = urlparse(blob_url.rstrip('/'))

    if not parsed_url.netloc:
        raise ValueError(f"Invalid URL: {blob_url}")

    account_path = ""
    if ".core." in parsed_url.netloc:
        # .core. is indicating non-customized url. Blob name with directory info can also be parsed.
        path_blob = parsed_url.path.lstrip('/').split('/', maxsplit=1)
    elif "localhost" in parsed_url.netloc or "127.0.0.1" in parsed_url.netloc:
        path_blob = parsed_url.path.lstrip('/').split('/', maxsplit=2)
        account_path += '/' + path_blob[0]
    else:
        # for customized url. blob name that has directory info cannot be parsed.
        path_blob = parsed_url.path.lstrip('/').split('/')
        if len(path_blob) > 2:
            account_path = "/" + "/".join(path_blob[:-2])

    account_url = f"{parsed_url.scheme}://{parsed_url.netloc.rstrip('/')}{account_path}?{parsed_url.query}"

    msg_invalid_url = "Invalid URL. Provide a blob_url with a valid blob and container name."
    if len(path_blob) <= 1:
        raise ValueError(msg_invalid_url)
    container_name, blob_name = unquote(path_blob[-2]), unquote(path_blob[-1])
    if not container_name or not blob_name:
        raise ValueError(msg_invalid_url)

    path_snapshot, _ = parse_query(parsed_url.query)
    if snapshot:
        if isinstance(snapshot, BlobProperties):
            path_snapshot = snapshot.snapshot
        elif isinstance(snapshot, dict):
            path_snapshot = snapshot['snapshot']
        else:
            path_snapshot = snapshot
    return (account_url, container_name, blob_name, path_snapshot)
