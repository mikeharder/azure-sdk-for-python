# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
# pylint: disable=too-few-public-methods, too-many-instance-attributes
# pylint: disable=super-init-not-called, too-many-lines

from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union, TYPE_CHECKING

from azure.core import CaseInsensitiveEnumMeta
from azure.core.paging import PageIterator
from azure.core.exceptions import HttpResponseError

from ._shared import decode_base64_to_bytes
from ._shared.response_handlers import return_context_and_deserialized, process_storage_error
from ._shared.models import DictMixin, get_enum_value
from ._generated.models import AccessPolicy as GenAccessPolicy
from ._generated.models import ArrowField
from ._generated.models import CorsRule as GeneratedCorsRule
from ._generated.models import Logging as GeneratedLogging
from ._generated.models import Metrics as GeneratedMetrics
from ._generated.models import RetentionPolicy as GeneratedRetentionPolicy
from ._generated.models import StaticWebsite as GeneratedStaticWebsite

if TYPE_CHECKING:
    from datetime import datetime
    from ._generated.models import PageList

# Parse a generated PageList into a single list of PageRange sorted by start.
def parse_page_list(page_list: "PageList") -> List["PageRange"]:

    page_ranges = page_list.page_range
    clear_ranges = page_list.clear_range

    if page_ranges is None:
        raise ValueError("PageList's 'page_range' is malformed or None.")
    if clear_ranges is None:
        raise ValueError("PageList's 'clear_ranges' is malformed or None.")

    ranges = []
    p_i, c_i = 0, 0

    # Combine page ranges and clear ranges into single list, sorted by start
    while p_i < len(page_ranges) and c_i < len(clear_ranges):
        p, c = page_ranges[p_i], clear_ranges[c_i]

        if p.start < c.start:
            ranges.append(
                PageRange(start=p.start, end=p.end, cleared=False)
            )
            p_i += 1
        else:
            ranges.append(
                PageRange(start=c.start, end=c.end, cleared=True)
            )
            c_i += 1

    # Grab remaining elements in either list
    ranges += [PageRange(start=r.start, end=r.end, cleared=False) for r in page_ranges[p_i:]]
    ranges += [PageRange(start=r.start, end=r.end, cleared=True) for r in clear_ranges[c_i:]]

    return ranges


class BlobType(str, Enum, metaclass=CaseInsensitiveEnumMeta):

    BLOCKBLOB = "BlockBlob"
    PAGEBLOB = "PageBlob"
    APPENDBLOB = "AppendBlob"


class BlockState(str, Enum, metaclass=CaseInsensitiveEnumMeta):
    """Block blob block types."""

    COMMITTED = 'Committed'  #: Committed blocks.
    LATEST = 'Latest'  #: Latest blocks.
    UNCOMMITTED = 'Uncommitted'  #: Uncommitted blocks.


class StandardBlobTier(str, Enum, metaclass=CaseInsensitiveEnumMeta):
    """
    Specifies the blob tier to set the blob to. This is only applicable for
    block blobs on standard storage accounts.
    """

    ARCHIVE = 'Archive'  #: Archive
    COOL = 'Cool'  #: Cool
    COLD = 'Cold'  #: Cold
    HOT = 'Hot'  #: Hot


class PremiumPageBlobTier(str, Enum, metaclass=CaseInsensitiveEnumMeta):
    """
    Specifies the page blob tier to set the blob to. This is only applicable to page
    blobs on premium storage accounts. Please take a look at:
    https://learn.microsoft.com/azure/storage/storage-premium-storage#scalability-and-performance-targets
    for detailed information on the corresponding IOPS and throughput per PageBlobTier.
    """

    P4 = 'P4'  #: P4 Tier
    P6 = 'P6'  #: P6 Tier
    P10 = 'P10'  #: P10 Tier
    P15 = 'P15'  #: P15 Tier
    P20 = 'P20'  #: P20 Tier
    P30 = 'P30'  #: P30 Tier
    P40 = 'P40'  #: P40 Tier
    P50 = 'P50'  #: P50 Tier
    P60 = 'P60'  #: P60 Tier


class QuickQueryDialect(str, Enum, metaclass=CaseInsensitiveEnumMeta):
    """Specifies the quick query input/output dialect."""

    DELIMITEDTEXT = 'DelimitedTextDialect'
    DELIMITEDJSON = 'DelimitedJsonDialect'
    PARQUET = 'ParquetDialect'


class SequenceNumberAction(str, Enum, metaclass=CaseInsensitiveEnumMeta):
    """Sequence number actions."""

    INCREMENT = 'increment'
    """
    Increments the value of the sequence number by 1. If specifying this option,
    do not include the x-ms-blob-sequence-number header.
    """

    MAX = 'max'
    """
    Sets the sequence number to be the higher of the value included with the
    request and the value currently stored for the blob.
    """

    UPDATE = 'update'
    """Sets the sequence number to the value included with the request."""


class PublicAccess(str, Enum, metaclass=CaseInsensitiveEnumMeta):
    """
    Specifies whether data in the container may be accessed publicly and the level of access.
    """

    OFF = 'off'
    """
    Specifies that there is no public read access for both the container and blobs within the container.
    Clients cannot enumerate the containers within the storage account as well as the blobs within the container.
    """

    BLOB = 'blob'
    """
    Specifies public read access for blobs. Blob data within this container can be read
    via anonymous request, but container data is not available. Clients cannot enumerate
    blobs within the container via anonymous request.
    """

    CONTAINER = 'container'
    """
    Specifies full public read access for container and blob data. Clients can enumerate
    blobs within the container via anonymous request, but cannot enumerate containers
    within the storage account.
    """


class BlobImmutabilityPolicyMode(str, Enum, metaclass=CaseInsensitiveEnumMeta):
    """
    Specifies the immutability policy mode to set on the blob.
    "Mutable" can only be returned by service, don't set to "Mutable".
    """

    UNLOCKED = "Unlocked"
    LOCKED = "Locked"
    MUTABLE = "Mutable"


class RetentionPolicy(GeneratedRetentionPolicy):
    """The retention policy which determines how long the associated data should
    persist.

    :param bool enabled:
        Indicates whether a retention policy is enabled for the storage service.
        The default value is False.
    :param Optional[int] days:
        Indicates the number of days that metrics or logging or
        soft-deleted data should be retained. All data older than this value will
        be deleted. If enabled=True, the number of days must be specified.
    """

    enabled: bool = False
    days: Optional[int] = None

    def __init__(self, enabled: bool = False, days: Optional[int] = None) -> None:
        super(RetentionPolicy, self).__init__(enabled=enabled, days=days, allow_permanent_delete=None)
        if self.enabled and (self.days is None):
            raise ValueError("If policy is enabled, 'days' must be specified.")

    @classmethod
    def _from_generated(cls, generated):
        if not generated:
            return cls()
        return cls(
            enabled=generated.enabled,
            days=generated.days,
        )


class BlobAnalyticsLogging(GeneratedLogging):
    """Azure Analytics Logging settings.

    :keyword str version:
        The version of Storage Analytics to configure. The default value is 1.0.
    :keyword bool delete:
        Indicates whether all delete requests should be logged. The default value is `False`.
    :keyword bool read:
        Indicates whether all read requests should be logged. The default value is `False`.
    :keyword bool write:
        Indicates whether all write requests should be logged. The default value is `False`.
    :keyword ~azure.storage.blob.RetentionPolicy retention_policy:
        Determines how long the associated data should persist. If not specified the retention
        policy will be disabled by default.
    """

    version: str = '1.0'
    """The version of Storage Analytics to configure."""
    delete: bool = False
    """Indicates whether all delete requests should be logged."""
    read: bool = False
    """Indicates whether all read requests should be logged."""
    write: bool = False
    """Indicates whether all write requests should be logged."""
    retention_policy: RetentionPolicy = RetentionPolicy()
    """Determines how long the associated data should persist."""

    def __init__(self, **kwargs: Any) -> None:
        self.version = kwargs.get('version', '1.0')
        self.delete = kwargs.get('delete', False)
        self.read = kwargs.get('read', False)
        self.write = kwargs.get('write', False)
        self.retention_policy = kwargs.get('retention_policy') or RetentionPolicy()

    @classmethod
    def _from_generated(cls, generated):
        if not generated:
            return cls()
        return cls(
            version=generated.version,
            delete=generated.delete,
            read=generated.read,
            write=generated.write,
            retention_policy=RetentionPolicy._from_generated(generated.retention_policy)  # pylint: disable=protected-access
        )


class Metrics(GeneratedMetrics):
    """A summary of request statistics grouped by API in hour or minute aggregates
    for blobs.

    :keyword str version:
        The version of Storage Analytics to configure. The default value is 1.0.
    :keyword bool enabled:
        Indicates whether metrics are enabled for the Blob service.
        The default value is `False`.
    :keyword bool include_apis:
        Indicates whether metrics should generate summary statistics for called API operations.
    :keyword ~azure.storage.blob.RetentionPolicy retention_policy:
        Determines how long the associated data should persist. If not specified the retention
        policy will be disabled by default.
    """

    version: str = '1.0'
    """The version of Storage Analytics to configure."""
    enabled: bool = False
    """Indicates whether metrics are enabled for the Blob service."""
    include_apis: Optional[bool]
    """Indicates whether metrics should generate summary statistics for called API operations."""
    retention_policy: RetentionPolicy = RetentionPolicy()
    """Determines how long the associated data should persist."""

    def __init__(self, **kwargs: Any) -> None:
        self.version = kwargs.get('version', '1.0')
        self.enabled = kwargs.get('enabled', False)
        self.include_apis = kwargs.get('include_apis')
        self.retention_policy = kwargs.get('retention_policy') or RetentionPolicy()

    @classmethod
    def _from_generated(cls, generated):
        if not generated:
            return cls()
        return cls(
            version=generated.version,
            enabled=generated.enabled,
            include_apis=generated.include_apis,
            retention_policy=RetentionPolicy._from_generated(generated.retention_policy)  # pylint: disable=protected-access
        )


class StaticWebsite(GeneratedStaticWebsite):
    """The properties that enable an account to host a static website.

    :keyword bool enabled:
        Indicates whether this account is hosting a static website.
        The default value is `False`.
    :keyword str index_document:
        The default name of the index page under each directory.
    :keyword str error_document404_path:
        The absolute path of the custom 404 page.
    :keyword str default_index_document_path:
        Absolute path of the default index page.
    """

    enabled: bool = False
    """Indicates whether this account is hosting a static website."""
    index_document: Optional[str]
    """The default name of the index page under each directory."""
    error_document404_path: Optional[str]
    """The absolute path of the custom 404 page."""
    default_index_document_path: Optional[str]
    """Absolute path of the default index page."""

    def __init__(self, **kwargs: Any) -> None:
        self.enabled = kwargs.get('enabled', False)
        if self.enabled:
            self.index_document = kwargs.get('index_document')
            self.error_document404_path = kwargs.get('error_document404_path')
            self.default_index_document_path = kwargs.get('default_index_document_path')
        else:
            self.index_document = None
            self.error_document404_path = None
            self.default_index_document_path = None

    @classmethod
    def _from_generated(cls, generated):
        if not generated:
            return cls()
        return cls(
            enabled=generated.enabled,
            index_document=generated.index_document,
            error_document404_path=generated.error_document404_path,
            default_index_document_path=generated.default_index_document_path
        )


class CorsRule(GeneratedCorsRule):
    """CORS is an HTTP feature that enables a web application running under one
    domain to access resources in another domain. Web browsers implement a
    security restriction known as same-origin policy that prevents a web page
    from calling APIs in a different domain; CORS provides a secure way to
    allow one domain (the origin domain) to call APIs in another domain.

    :param list(str) allowed_origins:
        A list of origin domains that will be allowed via CORS, or "*" to allow
        all domains. The list of must contain at least one entry. Limited to 64
        origin domains. Each allowed origin can have up to 256 characters.
    :param list(str) allowed_methods:
        A list of HTTP methods that are allowed to be executed by the origin.
        The list of must contain at least one entry. For Azure Storage,
        permitted methods are DELETE, GET, HEAD, MERGE, POST, OPTIONS or PUT.
    :keyword list(str) allowed_headers:
        Defaults to an empty list. A list of headers allowed to be part of
        the cross-origin request. Limited to 64 defined headers and 2 prefixed
        headers. Each header can be up to 256 characters.
    :keyword list(str) exposed_headers:
        Defaults to an empty list. A list of response headers to expose to CORS
        clients. Limited to 64 defined headers and two prefixed headers. Each
        header can be up to 256 characters.
    :keyword int max_age_in_seconds:
        The number of seconds that the client/browser should cache a
        preflight response.
    """

    allowed_origins: str
    """The comma-delimited string representation of the list of origin domains that will be allowed via
        CORS, or "*" to allow all domains."""
    allowed_methods: str
    """The comma-delimited string representation of the list HTTP methods that are allowed to be executed
        by the origin."""
    exposed_headers: str
    """The comma-delimited string representation of the list of response headers to expose to CORS clients."""
    allowed_headers: str
    """The comma-delimited string representation of the list of headers allowed to be part of the cross-origin
        request."""
    max_age_in_seconds: int
    """The number of seconds that the client/browser should cache a pre-flight response."""

    def __init__(self, allowed_origins: List[str], allowed_methods: List[str], **kwargs: Any) -> None:
        self.allowed_origins = ','.join(allowed_origins)
        self.allowed_methods = ','.join(allowed_methods)
        self.allowed_headers = ','.join(kwargs.get('allowed_headers', []))
        self.exposed_headers = ','.join(kwargs.get('exposed_headers', []))
        self.max_age_in_seconds = kwargs.get('max_age_in_seconds', 0)

    @staticmethod
    def _to_generated(rules: Optional[List["CorsRule"]]) -> Optional[List[GeneratedCorsRule]]:
        if rules is None:
            return rules

        generated_cors_list = []
        for cors_rule in rules:
            generated_cors = GeneratedCorsRule(
                allowed_origins=cors_rule.allowed_origins,
                allowed_methods=cors_rule.allowed_methods,
                allowed_headers=cors_rule.allowed_headers,
                exposed_headers=cors_rule.exposed_headers,
                max_age_in_seconds=cors_rule.max_age_in_seconds
            )
            generated_cors_list.append(generated_cors)

        return generated_cors_list

    @classmethod
    def _from_generated(cls, generated):
        return cls(
            [generated.allowed_origins],
            [generated.allowed_methods],
            allowed_headers=[generated.allowed_headers],
            exposed_headers=[generated.exposed_headers],
            max_age_in_seconds=generated.max_age_in_seconds,
        )


class ContainerProperties(DictMixin):
    """Blob container's properties class.

    Returned ``ContainerProperties`` instances expose these values through a
    dictionary interface, for example: ``container_props["last_modified"]``.
    Additionally, the container name is available as ``container_props["name"]``."""

    name: str
    """Name of the container."""
    last_modified: "datetime"
    """A datetime object representing the last time the container was modified."""
    etag: str
    """The ETag contains a value that you can use to perform operations conditionally."""
    lease: "LeaseProperties"
    """Stores all the lease information for the container."""
    public_access: Optional[str]
    """Specifies whether data in the container may be accessed publicly and the level of access."""
    has_immutability_policy: bool
    """Represents whether the container has an immutability policy."""
    has_legal_hold: bool
    """Represents whether the container has a legal hold."""
    immutable_storage_with_versioning_enabled: bool
    """Represents whether immutable storage with versioning enabled on the container."""
    metadata: Dict[str, Any]
    """A dict with name-value pairs to associate with the container as metadata."""
    encryption_scope: Optional["ContainerEncryptionScope"]
    """The default encryption scope configuration for the container."""
    deleted: Optional[bool]
    """Whether this container was deleted."""
    version: Optional[str]
    """The version of a deleted container."""

    def __init__(self, **kwargs: Any) -> None:
        self.name = None  # type: ignore [assignment]
        self.last_modified = kwargs.get('Last-Modified')  # type: ignore [assignment]
        self.etag = kwargs.get('ETag')  # type: ignore [assignment]
        self.lease = LeaseProperties(**kwargs)
        self.public_access = kwargs.get('x-ms-blob-public-access')
        self.has_immutability_policy = kwargs.get('x-ms-has-immutability-policy')  # type: ignore [assignment]
        self.deleted = None
        self.version = None
        self.has_legal_hold = kwargs.get('x-ms-has-legal-hold')  # type: ignore [assignment]
        self.metadata = kwargs.get('metadata')  # type: ignore [assignment]
        self.encryption_scope = None
        self.immutable_storage_with_versioning_enabled = kwargs.get('x-ms-immutable-storage-with-versioning-enabled')  # type: ignore [assignment]  # pylint: disable=name-too-long
        default_encryption_scope = kwargs.get('x-ms-default-encryption-scope')
        if default_encryption_scope:
            self.encryption_scope = ContainerEncryptionScope(
                default_encryption_scope=default_encryption_scope,
                prevent_encryption_scope_override=kwargs.get('x-ms-deny-encryption-scope-override', False)
            )

    @classmethod
    def _from_generated(cls, generated):
        props = cls()
        props.name = generated.name
        props.last_modified = generated.properties.last_modified
        props.etag = generated.properties.etag
        props.lease = LeaseProperties._from_generated(generated)  # pylint: disable=protected-access
        props.public_access = generated.properties.public_access
        props.has_immutability_policy = generated.properties.has_immutability_policy
        props.immutable_storage_with_versioning_enabled = generated.properties.is_immutable_storage_with_versioning_enabled  # pylint: disable=line-too-long, name-too-long
        props.deleted = generated.deleted
        props.version = generated.version
        props.has_legal_hold = generated.properties.has_legal_hold
        props.metadata = generated.metadata
        props.encryption_scope = ContainerEncryptionScope._from_generated(generated)  #pylint: disable=protected-access
        return props


class ContainerPropertiesPaged(PageIterator):
    """An Iterable of Container properties.

    :param Callable command: Function to retrieve the next page of items.
    :param Optional[str] prefix: Filters the results to return only containers whose names
        begin with the specified prefix.
    :param Optional[int] results_per_page: The maximum number of container names to retrieve per call.
    :param Optional[str] continuation_token: An opaque continuation token.
    """

    service_endpoint: Optional[str]
    """The service URL."""
    prefix: Optional[str]
    """A container name prefix being used to filter the list."""
    marker: Optional[str]
    """The continuation token of the current page of results."""
    results_per_page: Optional[int]
    """The maximum number of results retrieved per API call."""
    continuation_token: Optional[str]
    """The continuation token to retrieve the next page of results."""
    location_mode: Optional[str]
    """The location mode being used to list results."""
    current_page: List["ContainerProperties"]
    """The current page of listed results."""

    def __init__(
        self, command: Callable,
        prefix: Optional[str] = None,
        results_per_page: Optional[int] = None,
        continuation_token: Optional[str] = None
    ) -> None:
        super(ContainerPropertiesPaged, self).__init__(
            get_next=self._get_next_cb,
            extract_data=self._extract_data_cb,
            continuation_token=continuation_token or ""
        )
        self._command = command
        self.service_endpoint = None
        self.prefix = prefix
        self.marker = None
        self.results_per_page = results_per_page
        self.location_mode = None
        self.current_page = []

    def _get_next_cb(self, continuation_token):
        try:
            return self._command(
                marker=continuation_token or None,
                maxresults=self.results_per_page,
                cls=return_context_and_deserialized,
                use_location=self.location_mode)
        except HttpResponseError as error:
            process_storage_error(error)

    def _extract_data_cb(self, get_next_return):
        self.location_mode, self._response = get_next_return
        self.service_endpoint = self._response.service_endpoint
        self.prefix = self._response.prefix
        self.marker = self._response.marker
        self.results_per_page = self._response.max_results
        self.current_page = [self._build_item(item) for item in self._response.container_items]

        return self._response.next_marker or None, self.current_page

    @staticmethod
    def _build_item(item):
        return ContainerProperties._from_generated(item)  # pylint: disable=protected-access


class ImmutabilityPolicy(DictMixin):
    """Optional parameters for setting the immutability policy of a blob, blob snapshot or blob version.

    .. versionadded:: 12.10.0
        This was introduced in API version '2020-10-02'.

    :keyword ~datetime.datetime expiry_time:
        Specifies the date time when the blobs immutability policy is set to expire.
    :keyword str or ~azure.storage.blob.BlobImmutabilityPolicyMode policy_mode:
        Specifies the immutability policy mode to set on the blob.
        Possible values to set include: "Locked", "Unlocked".
        "Mutable" can only be returned by service, don't set to "Mutable".
    """

    expiry_time: Optional["datetime"] = None
    """Specifies the date time when the blobs immutability policy is set to expire."""
    policy_mode: Optional[str] = None
    """Specifies the immutability policy mode to set on the blob."""

    def __init__(self, **kwargs: Any) -> None:
        self.expiry_time = kwargs.pop('expiry_time', None)
        self.policy_mode = kwargs.pop('policy_mode', None)

    @classmethod
    def _from_generated(cls, generated):
        immutability_policy = cls()
        immutability_policy.expiry_time = generated.properties.immutability_policy_expires_on
        immutability_policy.policy_mode = generated.properties.immutability_policy_mode
        return immutability_policy


class FilteredBlob(DictMixin):
    """Blob info from a Filter Blobs API call."""

    name: str
    """Blob name"""
    container_name: Optional[str]
    """Container name."""
    tags: Optional[Dict[str, str]]
    """Key value pairs of blob tags."""

    def __init__(self, **kwargs: Any) -> None:
        self.name = kwargs.get('name', None)
        self.container_name = kwargs.get('container_name', None)
        self.tags = kwargs.get('tags', None)


class LeaseProperties(DictMixin):
    """Blob Lease Properties."""

    status: str
    """The lease status of the blob. Possible values: locked|unlocked"""
    state: str
    """Lease state of the blob. Possible values: available|leased|expired|breaking|broken"""
    duration: Optional[str]
    """When a blob is leased, specifies whether the lease is of infinite or fixed duration."""

    def __init__(self, **kwargs: Any) -> None:
        self.status = get_enum_value(kwargs.get('x-ms-lease-status'))
        self.state = get_enum_value(kwargs.get('x-ms-lease-state'))
        self.duration = get_enum_value(kwargs.get('x-ms-lease-duration'))

    @classmethod
    def _from_generated(cls, generated):
        lease = cls()
        lease.status = get_enum_value(generated.properties.lease_status)
        lease.state = get_enum_value(generated.properties.lease_state)
        lease.duration = get_enum_value(generated.properties.lease_duration)
        return lease


class ContentSettings(DictMixin):
    """The content settings of a blob.

    :param Optional[str] content_type:
        The content type specified for the blob. If no content type was
        specified, the default content type is application/octet-stream.
    :param Optional[str] content_encoding:
        If the content_encoding has previously been set
        for the blob, that value is stored.
    :param Optional[str] content_language:
        If the content_language has previously been set
        for the blob, that value is stored.
    :param Optional[str] content_disposition:
        content_disposition conveys additional information about how to
        process the response payload, and also can be used to attach
        additional metadata. If content_disposition has previously been set
        for the blob, that value is stored.
    :param Optional[str] cache_control:
        If the cache_control has previously been set for
        the blob, that value is stored.
    :param Optional[bytearray] content_md5:
        If the content_md5 has been set for the blob, this response
        header is stored so that the client can check for message content
        integrity.
    """

    content_type: Optional[str] = None
    """The content type specified for the blob."""
    content_encoding: Optional[str] = None
    """The content encoding specified for the blob."""
    content_language: Optional[str] = None
    """The content language specified for the blob."""
    content_disposition: Optional[str] = None
    """The content disposition specified for the blob."""
    cache_control: Optional[str] = None
    """The cache control specified for the blob."""
    content_md5: Optional[bytearray] = None
    """The content md5 specified for the blob."""

    def __init__(
        self, content_type: Optional[str] = None,
        content_encoding: Optional[str] = None,
        content_language: Optional[str] = None,
        content_disposition: Optional[str] = None,
        cache_control: Optional[str] = None,
        content_md5: Optional[bytearray] = None,
        **kwargs: Any
    ) -> None:

        self.content_type = content_type or kwargs.get('Content-Type')
        self.content_encoding = content_encoding or kwargs.get('Content-Encoding')
        self.content_language = content_language or kwargs.get('Content-Language')
        self.content_md5 = content_md5 or kwargs.get('Content-MD5')
        self.content_disposition = content_disposition or kwargs.get('Content-Disposition')
        self.cache_control = cache_control or kwargs.get('Cache-Control')

    @classmethod
    def _from_generated(cls, generated):
        settings = cls()
        settings.content_type = generated.properties.content_type or None
        settings.content_encoding = generated.properties.content_encoding or None
        settings.content_language = generated.properties.content_language or None
        settings.content_md5 = generated.properties.content_md5 or None
        settings.content_disposition = generated.properties.content_disposition or None
        settings.cache_control = generated.properties.cache_control or None
        return settings


class CopyProperties(DictMixin):
    """Blob Copy Properties.

    These properties will be `None` if this blob has never been the destination
    in a Copy Blob operation, or if this blob has been modified after a concluded
    Copy Blob operation, for example, using Set Blob Properties, Upload Blob, or Commit Block List.
    """

    id: Optional[str]
    """String identifier for the last attempted Copy Blob operation where this blob
        was the destination blob."""
    source: Optional[str]
    """URL up to 2 KB in length that specifies the source blob used in the last attempted
        Copy Blob operation where this blob was the destination blob."""
    status: Optional[str]
    """State of the copy operation identified by Copy ID, with these values:
    success: Copy completed successfully.
    pending: Copy is in progress. Check copy_status_description if intermittent, non-fatal errors impede copy progress
    but don't cause failure.
    aborted: Copy was ended by Abort Copy Blob.
    failed: Copy failed. See copy_status_description for failure details."""
    progress: Optional[str]
    """Contains the number of bytes copied and the total bytes in the source in the last
        attempted Copy Blob operation where this blob was the destination blob. Can show
        between 0 and Content-Length bytes copied."""
    completion_time: Optional["datetime"]
    """Conclusion time of the last attempted Copy Blob operation where this blob was the
        destination blob. This value can specify the time of a completed, aborted, or
        failed copy attempt."""
    status_description: Optional[str]
    """Only appears when x-ms-copy-status is failed or pending. Describes cause of fatal
        or non-fatal copy operation failure."""
    incremental_copy: Optional[bool]
    """Copies the snapshot of the source page blob to a destination page blob.
        The snapshot is copied such that only the differential changes between
        the previously copied snapshot are transferred to the destination."""
    destination_snapshot: Optional["datetime"]
    """Included if the blob is incremental copy blob or incremental copy snapshot,
        if x-ms-copy-status is success. Snapshot time of the last successful
        incremental copy snapshot for this blob."""

    def __init__(self, **kwargs: Any) -> None:
        self.id = kwargs.get('x-ms-copy-id')
        self.source = kwargs.get('x-ms-copy-source')
        self.status = get_enum_value(kwargs.get('x-ms-copy-status'))
        self.progress = kwargs.get('x-ms-copy-progress')
        self.completion_time = kwargs.get('x-ms-copy-completion-time')
        self.status_description = kwargs.get('x-ms-copy-status-description')
        self.incremental_copy = kwargs.get('x-ms-incremental-copy')
        self.destination_snapshot = kwargs.get('x-ms-copy-destination-snapshot')

    @classmethod
    def _from_generated(cls, generated):
        copy = cls()
        copy.id = generated.properties.copy_id or None
        copy.status = get_enum_value(generated.properties.copy_status) or None
        copy.source = generated.properties.copy_source or None
        copy.progress = generated.properties.copy_progress or None
        copy.completion_time = generated.properties.copy_completion_time or None
        copy.status_description = generated.properties.copy_status_description or None
        copy.incremental_copy = generated.properties.incremental_copy or None
        copy.destination_snapshot = generated.properties.destination_snapshot or None
        return copy


class BlobBlock(DictMixin):
    """BlockBlob Block class.

    :param str block_id:
        Block id.
    :param BlockState state:
        Block state. Possible values: BlockState.COMMITTED | BlockState.UNCOMMITTED
    """

    block_id: str
    """Block id."""
    state: BlockState
    """Block state."""
    size: int
    """Block size."""

    def __init__(self, block_id: str, state: BlockState = BlockState.LATEST) -> None:
        self.id = block_id
        self.state = state
        self.size = None  # type: ignore [assignment]

    @classmethod
    def _from_generated(cls, generated):
        try:
            decoded_bytes = decode_base64_to_bytes(generated.name)
            block_id = decoded_bytes.decode('utf-8')
        # this is to fix a bug. When large blocks are uploaded through upload_blob the block id isn't base64 encoded
        # while service expected block id is base64 encoded, so when we get block_id if we cannot base64 decode, it
        # means we didn't base64 encode it when stage the block, we want to use the returned block_id directly.
        except UnicodeDecodeError:
            block_id = generated.name
        block = cls(block_id)
        block.size = generated.size
        return block


class PageRange(DictMixin):
    """Page Range for page blob.

    :param int start:
        Start of page range in bytes.
    :param int end:
        End of page range in bytes.
    """

    start: Optional[int] = None
    """Start of page range in bytes."""
    end: Optional[int] = None
    """End of page range in bytes."""
    cleared: bool
    """Whether the range has been cleared."""

    def __init__(self, start: Optional[int] = None, end: Optional[int] = None, *, cleared: bool = False) -> None:
        self.start = start
        self.end = end
        self.cleared = cleared


class PageRangePaged(PageIterator):
    def __init__(self, command, results_per_page=None, continuation_token=None):
        super(PageRangePaged, self).__init__(
            get_next=self._get_next_cb,
            extract_data=self._extract_data_cb,
            continuation_token=continuation_token or ""
        )
        self._command = command
        self.results_per_page = results_per_page
        self.location_mode = None
        self.current_page = []

    def _get_next_cb(self, continuation_token):
        try:
            return self._command(
                marker=continuation_token or None,
                maxresults=self.results_per_page,
                cls=return_context_and_deserialized,
                use_location=self.location_mode)
        except HttpResponseError as error:
            process_storage_error(error)

    def _extract_data_cb(self, get_next_return):
        self.location_mode, self._response = get_next_return
        self.current_page = self._build_page(self._response)

        return self._response.next_marker or None, self.current_page

    @staticmethod
    def _build_page(response):
        if not response:
            raise StopIteration

        return parse_page_list(response)


class ContainerSasPermissions(object):
    """ContainerSasPermissions class to be used with the
    :func:`~azure.storage.blob.generate_container_sas` function and
    for the AccessPolicies used with
    :func:`~azure.storage.blob.ContainerClient.set_container_access_policy`.

    :param bool read:
        Read the content, properties, metadata or block list of any blob in the
        container. Use any blob in the container as the source of a copy operation.
    :param bool write:
        For any blob in the container, create or write content, properties,
        metadata, or block list. Snapshot or lease the blob. Resize the blob
        (page blob only). Use the blob as the destination of a copy operation
        within the same account. Note: You cannot grant permissions to read or
        write container properties or metadata, nor to lease a container, with
        a container SAS. Use an account SAS instead.
    :param bool delete:
        Delete any blob in the container. Note: You cannot grant permissions to
        delete a container with a container SAS. Use an account SAS instead.
    :param bool delete_previous_version:
        Delete the previous blob version for the versioning enabled storage account.
    :param bool list:
        List blobs in the container.
    :param bool tag:
        Set or get tags on the blobs in the container.
    :keyword bool add:
        Add a block to an append blob.
    :keyword bool create:
        Write a new blob, snapshot a blob, or copy a blob to a new blob.
    :keyword bool permanent_delete:
        To enable permanent delete on the blob is permitted.
    :keyword bool filter_by_tags:
        To enable finding blobs by tags.
    :keyword bool move:
        Move a blob or a directory and its contents to a new location.
    :keyword bool execute:
        Get the system properties and, if the hierarchical namespace is enabled for the storage account,
        get the POSIX ACL of a blob.
    :keyword bool set_immutability_policy:
        To enable operations related to set/delete immutability policy.
        To get immutability policy, you just need read permission.
    """

    read: bool = False
    """The read permission for container SAS."""
    write: bool = False
    """The write permission for container SAS."""
    delete: bool = False
    """The delete permission for container SAS."""
    delete_previous_version: bool = False
    """Permission to delete previous blob version for versioning enabled
        storage accounts."""
    list: bool = False
    """The list permission for container SAS."""
    tag: bool = False
    """Set or get tags on the blobs in the container."""
    add: Optional[bool]
    """Add a block to an append blob."""
    create: Optional[bool]
    """Write a new blob, snapshot a blob, or copy a blob to a new blob."""
    permanent_delete: Optional[bool]
    """To enable permanent delete on the blob is permitted."""
    move: Optional[bool]
    """Move a blob or a directory and its contents to a new location."""
    execute: Optional[bool]
    """Get the system properties and, if the hierarchical namespace is enabled for the storage account,
        get the POSIX ACL of a blob."""
    set_immutability_policy: Optional[bool]
    """To get immutability policy, you just need read permission."""

    def __init__(
        self, read: bool = False,
        write: bool = False,
        delete: bool = False,
        list: bool = False,
        delete_previous_version: bool = False,
        tag: bool = False,
        **kwargs: Any
    ) -> None:
        self.read = read
        self.add = kwargs.pop('add', False)
        self.create = kwargs.pop('create', False)
        self.write = write
        self.delete = delete
        self.delete_previous_version = delete_previous_version
        self.permanent_delete = kwargs.pop('permanent_delete', False)
        self.list = list
        self.tag = tag
        self.filter_by_tags = kwargs.pop('filter_by_tags', False)
        self.move = kwargs.pop('move', False)
        self.execute = kwargs.pop('execute', False)
        self.set_immutability_policy = kwargs.pop('set_immutability_policy', False)
        self._str = (('r' if self.read else '') +
                     ('a' if self.add else '') +
                     ('c' if self.create else '') +
                     ('w' if self.write else '') +
                     ('d' if self.delete else '') +
                     ('x' if self.delete_previous_version else '') +
                     ('y' if self.permanent_delete else '') +
                     ('l' if self.list else '') +
                     ('t' if self.tag else '') +
                     ('f' if self.filter_by_tags else '') +
                     ('m' if self.move else '') +
                     ('e' if self.execute else '') +
                     ('i' if self.set_immutability_policy else ''))

    def __str__(self):
        return self._str

    @classmethod
    def from_string(cls, permission: str) -> "ContainerSasPermissions":
        """Create a ContainerSasPermissions from a string.

        To specify read, write, delete, or list permissions you need only to
        include the first letter of the word in the string. E.g. For read and
        write permissions, you would provide a string "rw".

        :param str permission: The string which dictates the read, write, delete,
            and list permissions.
        :return: A ContainerSasPermissions object
        :rtype: ~azure.storage.blob.ContainerSasPermissions
        """
        p_read = 'r' in permission
        p_add = 'a' in permission
        p_create = 'c' in permission
        p_write = 'w' in permission
        p_delete = 'd' in permission
        p_delete_previous_version = 'x' in permission
        p_permanent_delete = 'y' in permission
        p_list = 'l' in permission
        p_tag = 't' in permission
        p_filter_by_tags = 'f' in permission
        p_move = 'm' in permission
        p_execute = 'e' in permission
        p_set_immutability_policy = 'i' in permission
        parsed = cls(read=p_read, write=p_write, delete=p_delete, list=p_list,
                     delete_previous_version=p_delete_previous_version, tag=p_tag, add=p_add,
                     create=p_create, permanent_delete=p_permanent_delete, filter_by_tags=p_filter_by_tags,
                     move=p_move, execute=p_execute, set_immutability_policy=p_set_immutability_policy)

        return parsed


class AccessPolicy(GenAccessPolicy):
    """Access Policy class used by the set and get access policy methods in each service.

    A stored access policy can specify the start time, expiry time, and
    permissions for the Shared Access Signatures with which it's associated.
    Depending on how you want to control access to your resource, you can
    specify all of these parameters within the stored access policy, and omit
    them from the URL for the Shared Access Signature. Doing so permits you to
    modify the associated signature's behavior at any time, as well as to revoke
    it. Or you can specify one or more of the access policy parameters within
    the stored access policy, and the others on the URL. Finally, you can
    specify all of the parameters on the URL. In this case, you can use the
    stored access policy to revoke the signature, but not to modify its behavior.

    Together the Shared Access Signature and the stored access policy must
    include all fields required to authenticate the signature. If any required
    fields are missing, the request will fail. Likewise, if a field is specified
    both in the Shared Access Signature URL and in the stored access policy, the
    request will fail with status code 400 (Bad Request).

    :param permission:
        The permissions associated with the shared access signature. The
        user is restricted to operations allowed by the permissions.
        Required unless an id is given referencing a stored access policy
        which contains this field. This field must be omitted if it has been
        specified in an associated stored access policy.
    :type permission: Optional[Union[ContainerSasPermissions, str]]
    :param expiry:
        The time at which the shared access signature becomes invalid.
        Required unless an id is given referencing a stored access policy
        which contains this field. This field must be omitted if it has
        been specified in an associated stored access policy. Azure will always
        convert values to UTC. If a date is passed in without timezone info, it
        is assumed to be UTC.
    :paramtype expiry: Optional[Union[str, datetime]]
    :param start:
        The time at which the shared access signature becomes valid. If
        omitted, start time for this call is assumed to be the time when the
        storage service receives the request. Azure will always convert values
        to UTC. If a date is passed in without timezone info, it is assumed to
        be UTC.
    :paramtype start: Optional[Union[str, datetime]]
    """

    permission: Optional[Union[ContainerSasPermissions, str]]  # type: ignore [assignment]
    """The permissions associated with the shared access signature. The user is restricted to
        operations allowed by the permissions."""
    expiry: Optional[Union["datetime", str]]  # type: ignore [assignment]
    """The time at which the shared access signature becomes invalid."""
    start: Optional[Union["datetime", str]]  # type: ignore [assignment]
    """The time at which the shared access signature becomes valid."""

    def __init__(
        self, permission: Optional[Union["ContainerSasPermissions", str]] = None,
        expiry: Optional[Union[str, "datetime"]] = None,
        start: Optional[Union[str, "datetime"]] = None
    ) -> None:
        self.start = start
        self.expiry = expiry
        self.permission = permission


class BlobSasPermissions(object):
    """BlobSasPermissions class to be used with the
    :func:`~azure.storage.blob.generate_blob_sas` function.

    :param bool read:
        Read the content, properties, metadata and block list. Use the blob as
        the source of a copy operation.
    :param bool add:
        Add a block to an append blob.
    :param bool create:
        Write a new blob, snapshot a blob, or copy a blob to a new blob.
    :param bool write:
        Create or write content, properties, metadata, or block list. Snapshot
        or lease the blob. Resize the blob (page blob only). Use the blob as the
        destination of a copy operation within the same account.
    :param bool delete:
        Delete the blob.
    :param bool delete_previous_version:
        Delete the previous blob version for the versioning enabled storage account.
    :param bool tag:
        Set or get tags on the blob.
    :keyword bool permanent_delete:
        To enable permanent delete on the blob is permitted.
    :keyword bool move:
        Move a blob or a directory and its contents to a new location.
    :keyword bool execute:
        Get the system properties and, if the hierarchical namespace is enabled for the storage account,
        get the POSIX ACL of a blob.
    :keyword bool set_immutability_policy:
        To enable operations related to set/delete immutability policy.
        To get immutability policy, you just need read permission.
    """

    read: bool = False
    """The read permission for Blob SAS."""
    add: Optional[bool]
    """The add permission for Blob SAS."""
    create: Optional[bool]
    """Write a new blob, snapshot a blob, or copy a blob to a new blob."""
    write: bool = False
    """The write permission for Blob SAS."""
    delete: bool = False
    """The delete permission for Blob SAS."""
    delete_previous_version: bool = False
    """Permission to delete previous blob version for versioning enabled
        storage accounts."""
    tag: bool = False
    """Set or get tags on the blobs in the Blob."""
    permanent_delete: Optional[bool]
    """To enable permanent delete on the blob is permitted."""
    move: Optional[bool]
    """Move a blob or a directory and its contents to a new location."""
    execute: Optional[bool]
    """Get the system properties and, if the hierarchical namespace is enabled for the storage account,
        get the POSIX ACL of a blob."""
    set_immutability_policy: Optional[bool]
    """To get immutability policy, you just need read permission."""

    def __init__(
        self, read: bool = False,
        add: bool = False,
        create: bool = False,
        write: bool = False,
        delete: bool = False,
        delete_previous_version: bool = False,
        tag: bool = False,
        **kwargs: Any
    ) -> None:
        self.read = read
        self.add = add
        self.create = create
        self.write = write
        self.delete = delete
        self.delete_previous_version = delete_previous_version
        self.permanent_delete = kwargs.pop('permanent_delete', False)
        self.tag = tag
        self.move = kwargs.pop('move', False)
        self.execute = kwargs.pop('execute', False)
        self.set_immutability_policy = kwargs.pop('set_immutability_policy', False)
        self._str = (('r' if self.read else '') +
                     ('a' if self.add else '') +
                     ('c' if self.create else '') +
                     ('w' if self.write else '') +
                     ('d' if self.delete else '') +
                     ('x' if self.delete_previous_version else '') +
                     ('y' if self.permanent_delete else '') +
                     ('t' if self.tag else '') +
                     ('m' if self.move else '') +
                     ('e' if self.execute else '') +
                     ('i' if self.set_immutability_policy else ''))

    def __str__(self):
        return self._str

    @classmethod
    def from_string(cls, permission: str) -> "BlobSasPermissions":
        """Create a BlobSasPermissions from a string.

        To specify read, add, create, write, or delete permissions you need only to
        include the first letter of the word in the string. E.g. For read and
        write permissions, you would provide a string "rw".

        :param str permission: The string which dictates the read, add, create,
            write, or delete permissions.
        :return: A BlobSasPermissions object
        :rtype: ~azure.storage.blob.BlobSasPermissions
        """
        p_read = 'r' in permission
        p_add = 'a' in permission
        p_create = 'c' in permission
        p_write = 'w' in permission
        p_delete = 'd' in permission
        p_delete_previous_version = 'x' in permission
        p_permanent_delete = 'y' in permission
        p_tag = 't' in permission
        p_move = 'm' in permission
        p_execute = 'e' in permission
        p_set_immutability_policy = 'i' in permission

        parsed = cls(read=p_read, add=p_add, create=p_create, write=p_write, delete=p_delete,
                     delete_previous_version=p_delete_previous_version, tag=p_tag, permanent_delete=p_permanent_delete,
                     move=p_move, execute=p_execute, set_immutability_policy=p_set_immutability_policy)

        return parsed


class CustomerProvidedEncryptionKey(object):
    """
    All data in Azure Storage is encrypted at-rest using an account-level encryption key.
    In versions 2018-06-17 and newer, you can manage the key used to encrypt blob contents
    and application metadata per-blob by providing an AES-256 encryption key in requests to the storage service.

    When you use a customer-provided key, Azure Storage does not manage or persist your key.
    When writing data to a blob, the provided key is used to encrypt your data before writing it to disk.
    A SHA-256 hash of the encryption key is written alongside the blob contents,
    and is used to verify that all subsequent operations against the blob use the same encryption key.
    This hash cannot be used to retrieve the encryption key or decrypt the contents of the blob.
    When reading a blob, the provided key is used to decrypt your data after reading it from disk.
    In both cases, the provided encryption key is securely discarded
    as soon as the encryption or decryption process completes.

    :param str key_value:
        Base64-encoded AES-256 encryption key value.
    :param str key_hash:
        Base64-encoded SHA256 of the encryption key.
    """

    key_value: str
    """Base64-encoded AES-256 encryption key value."""
    key_hash: str
    """Base64-encoded SHA256 of the encryption key."""
    algorithm: str
    """Specifies the algorithm to use when encrypting data using the given key. Must be AES256."""

    def __init__(self, key_value: str, key_hash: str) -> None:
        self.key_value = key_value
        self.key_hash = key_hash
        self.algorithm = 'AES256'


class ContainerEncryptionScope(object):
    """The default encryption scope configuration for a container.

    This scope is used implicitly for all future writes within the container,
    but can be overridden per blob operation.

    .. versionadded:: 12.2.0

    :param str default_encryption_scope:
        Specifies the default encryption scope to set on the container and use for
        all future writes.
    :param bool prevent_encryption_scope_override:
        If true, prevents any request from specifying a different encryption scope than the scope
        set on the container. Default value is false.
    """

    default_encryption_scope: str
    """Specifies the default encryption scope to set on the container and use for
        all future writes."""
    prevent_encryption_scope_override: bool
    """If true, prevents any request from specifying a different encryption scope than the scope
        set on the container."""

    def __init__(self, default_encryption_scope: str, **kwargs: Any) -> None:
        self.default_encryption_scope = default_encryption_scope
        self.prevent_encryption_scope_override = kwargs.get('prevent_encryption_scope_override', False)

    @classmethod
    def _from_generated(cls, generated):
        if generated.properties.default_encryption_scope:
            scope = cls(
                generated.properties.default_encryption_scope,
                prevent_encryption_scope_override=generated.properties.prevent_encryption_scope_override or False
            )
            return scope
        return None


class DelimitedJsonDialect(DictMixin):
    """Defines the input or output JSON serialization for a blob data query.

    :keyword str delimiter: The line separator character, default value is '\\\\n'.
    """

    def __init__(self, **kwargs: Any) -> None:
        self.delimiter = kwargs.pop('delimiter', '\n')


class DelimitedTextDialect(DictMixin):
    """Defines the input or output delimited (CSV) serialization for a blob query request.

    :keyword str delimiter:
        Column separator, defaults to ','.
    :keyword str quotechar:
        Field quote, defaults to '"'.
    :keyword str lineterminator:
        Record separator, defaults to '\\\\n'.
    :keyword str escapechar:
        Escape char, defaults to empty.
    :keyword bool has_header:
        Whether the blob data includes headers in the first line. The default value is False, meaning that the
        data will be returned inclusive of the first line. If set to True, the data will be returned exclusive
        of the first line.
    """

    def __init__(self, **kwargs: Any) -> None:
        self.delimiter = kwargs.pop('delimiter', ',')
        self.quotechar = kwargs.pop('quotechar', '"')
        self.lineterminator = kwargs.pop('lineterminator', '\n')
        self.escapechar = kwargs.pop('escapechar', "")
        self.has_header = kwargs.pop('has_header', False)


class ArrowDialect(ArrowField):
    """field of an arrow schema.

    All required parameters must be populated in order to send to Azure.

    :param ~azure.storage.blob.ArrowType type: Arrow field type.
    :keyword str name: The name of the field.
    :keyword int precision: The precision of the field.
    :keyword int scale: The scale of the field.
    """

    def __init__(self, type, **kwargs: Any) -> None:   # pylint: disable=redefined-builtin
        super(ArrowDialect, self).__init__(type=type, **kwargs)


class ArrowType(str, Enum, metaclass=CaseInsensitiveEnumMeta):

    INT64 = "int64"
    BOOL = "bool"
    TIMESTAMP_MS = "timestamp[ms]"
    STRING = "string"
    DOUBLE = "double"
    DECIMAL = 'decimal'


class ObjectReplicationRule(DictMixin):
    """Policy id and rule ids applied to a blob."""

    rule_id: str
    """Rule id."""
    status: str
    """The status of the rule. It could be "Complete" or "Failed" """

    def __init__(self, **kwargs: Any) -> None:
        self.rule_id = kwargs.pop('rule_id', None)  # type: ignore [assignment]
        self.status = kwargs.pop('status', None)  # type: ignore [assignment]


class ObjectReplicationPolicy(DictMixin):
    """Policy id and rule ids applied to a blob."""

    policy_id: str
    """Policy id for the blob. A replication policy gets created (policy id) when creating a source/destination pair."""
    rules: List[ObjectReplicationRule]
    """Within each policy there may be multiple replication rules.
        e.g. rule 1= src/container/.pdf to dst/container2/; rule2 = src/container1/.jpg to dst/container3"""

    def __init__(self, **kwargs: Any) -> None:
        self.policy_id = kwargs.pop('policy_id', None)  # type: ignore [assignment]
        self.rules = kwargs.pop('rules', [])


class BlobProperties(DictMixin):
    """Blob Properties."""

    name: str
    """The name of the blob."""
    container: str
    """The container in which the blob resides."""
    snapshot: Optional[str]
    """Datetime value that uniquely identifies the blob snapshot."""
    blob_type: "BlobType"
    """String indicating this blob's type."""
    metadata: Dict[str, str]
    """Name-value pairs associated with the blob as metadata."""
    last_modified: "datetime"
    """A datetime object representing the last time the blob was modified."""
    etag: str
    """The ETag contains a value that you can use to perform operations
        conditionally."""
    size: int
    """The size of the content returned. If the entire blob was requested,
        the length of blob in bytes. If a subset of the blob was requested, the
        length of the returned subset."""
    content_range: Optional[str]
    """Indicates the range of bytes returned in the event that the client
        requested a subset of the blob."""
    append_blob_committed_block_count: Optional[int]
    """(For Append Blobs) Number of committed blocks in the blob."""
    is_append_blob_sealed: Optional[bool]
    """Indicate if the append blob is sealed or not."""
    page_blob_sequence_number: Optional[int]
    """(For Page Blobs) Sequence number for page blob used for coordinating
        concurrent writes."""
    server_encrypted: bool
    """Set to true if the blob is encrypted on the server."""
    copy: "CopyProperties"
    """Stores all the copy properties for the blob."""
    content_settings: ContentSettings
    """Stores all the content settings for the blob."""
    lease: LeaseProperties
    """Stores all the lease information for the blob."""
    blob_tier: Optional[StandardBlobTier]
    """Indicates the access tier of the blob. The hot tier is optimized
        for storing data that is accessed frequently. The cool storage tier
        is optimized for storing data that is infrequently accessed and stored
        for at least a month. The archive tier is optimized for storing
        data that is rarely accessed and stored for at least six months
        with flexible latency requirements."""
    rehydrate_priority: Optional[str]
    """Indicates the priority with which to rehydrate an archived blob"""
    blob_tier_change_time: Optional["datetime"]
    """Indicates when the access tier was last changed."""
    blob_tier_inferred: Optional[bool]
    """Indicates whether the access tier was inferred by the service.
        If false, it indicates that the tier was set explicitly."""
    deleted: Optional[bool]
    """Whether this blob was deleted."""
    deleted_time: Optional["datetime"]
    """A datetime object representing the time at which the blob was deleted."""
    remaining_retention_days: Optional[int]
    """The number of days that the blob will be retained before being permanently deleted by the service."""
    creation_time: "datetime"
    """Indicates when the blob was created, in UTC."""
    archive_status: Optional[str]
    """Archive status of blob."""
    encryption_key_sha256: Optional[str]
    """The SHA-256 hash of the provided encryption key."""
    encryption_scope: Optional[str]
    """A predefined encryption scope used to encrypt the data on the service. An encryption
        scope can be created using the Management API and referenced here by name. If a default
        encryption scope has been defined at the container, this value will override it if the
        container-level scope is configured to allow overrides. Otherwise an error will be raised."""
    request_server_encrypted: Optional[bool]
    """Whether this blob is encrypted."""
    object_replication_source_properties: Optional[List[ObjectReplicationPolicy]]
    """Only present for blobs that have policy ids and rule ids applied to them."""
    object_replication_destination_policy: Optional[str]
    """Represents the Object Replication Policy Id that created this blob."""
    last_accessed_on: Optional["datetime"]
    """Indicates when the last Read/Write operation was performed on a Blob."""
    tag_count: Optional[int]
    """Tags count on this blob."""
    tags: Optional[Dict[str, str]]
    """Key value pair of tags on this blob."""
    has_versions_only: Optional[bool]
    """A true value indicates the root blob is deleted"""
    immutability_policy: ImmutabilityPolicy
    """Specifies the immutability policy of a blob, blob snapshot or blob version."""
    has_legal_hold: Optional[bool]
    """Specified if a legal hold should be set on the blob.
        Currently this parameter of upload_blob() API is for BlockBlob only."""

    def __init__(self, **kwargs: Any) -> None:
        self.name = kwargs.get('name')  # type: ignore [assignment]
        self.container = None  # type: ignore [assignment]
        self.snapshot = kwargs.get('x-ms-snapshot')
        self.version_id = kwargs.get('x-ms-version-id')
        self.is_current_version = kwargs.get('x-ms-is-current-version')
        self.blob_type = BlobType(kwargs['x-ms-blob-type']) if (
            kwargs.get('x-ms-blob-type')) else None  # type: ignore [assignment]
        self.metadata = kwargs.get('metadata')  # type: ignore [assignment]
        self.encrypted_metadata = kwargs.get('encrypted_metadata')
        self.last_modified = kwargs.get('Last-Modified')  # type: ignore [assignment]
        self.etag = kwargs.get('ETag')  # type: ignore [assignment]
        self.size = kwargs.get('Content-Length')  # type: ignore [assignment]
        self.content_range = kwargs.get('Content-Range')
        self.append_blob_committed_block_count = kwargs.get('x-ms-blob-committed-block-count')
        self.is_append_blob_sealed = kwargs.get('x-ms-blob-sealed')
        self.page_blob_sequence_number = kwargs.get('x-ms-blob-sequence-number')
        self.server_encrypted = kwargs.get('x-ms-server-encrypted')  # type: ignore [assignment]
        self.copy = CopyProperties(**kwargs)
        self.content_settings = ContentSettings(**kwargs)
        self.lease = LeaseProperties(**kwargs)
        self.blob_tier = kwargs.get('x-ms-access-tier')
        self.rehydrate_priority = kwargs.get('x-ms-rehydrate-priority')
        self.blob_tier_change_time = kwargs.get('x-ms-access-tier-change-time')
        self.blob_tier_inferred = kwargs.get('x-ms-access-tier-inferred')
        self.deleted = False
        self.deleted_time = None
        self.remaining_retention_days = None
        self.creation_time = kwargs.get('x-ms-creation-time')  # type: ignore [assignment]
        self.archive_status = kwargs.get('x-ms-archive-status')
        self.encryption_key_sha256 = kwargs.get('x-ms-encryption-key-sha256')
        self.encryption_scope = kwargs.get('x-ms-encryption-scope')
        self.request_server_encrypted = kwargs.get('x-ms-server-encrypted')
        self.object_replication_source_properties = kwargs.get('object_replication_source_properties')
        self.object_replication_destination_policy = kwargs.get('x-ms-or-policy-id')
        self.last_accessed_on = kwargs.get('x-ms-last-access-time')
        self.tag_count = kwargs.get('x-ms-tag-count')
        self.tags = None
        self.immutability_policy = ImmutabilityPolicy(expiry_time=kwargs.get('x-ms-immutability-policy-until-date'),
                                                      policy_mode=kwargs.get('x-ms-immutability-policy-mode'))
        self.has_legal_hold = kwargs.get('x-ms-legal-hold')
        self.has_versions_only = None


class BlobQueryError(object):
    """The error happened during quick query operation."""

    error: Optional[str]
    """The name of the error."""
    is_fatal: bool
    """If true, this error prevents further query processing. More result data may be returned,
        but there is no guarantee that all of the original data will be processed.
        If false, this error does not prevent further query processing."""
    description: Optional[str]
    """A description of the error."""
    position: Optional[int]
    """The blob offset at which the error occurred."""

    def __init__(
        self, error: Optional[str] = None,
        is_fatal: bool = False,
        description: Optional[str] = None,
        position: Optional[int] = None
    ) -> None:
        self.error = error
        self.is_fatal = is_fatal
        self.description = description
        self.position = position
