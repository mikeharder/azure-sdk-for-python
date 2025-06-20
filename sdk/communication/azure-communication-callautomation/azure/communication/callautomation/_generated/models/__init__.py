# coding=utf-8
# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is regenerated.
# --------------------------------------------------------------------------
# pylint: disable=wrong-import-position

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._patch import *  # pylint: disable=unused-wildcard-import


from ._models import (  # type: ignore
    AddParticipantFailed,
    AddParticipantRequest,
    AddParticipantResponse,
    AddParticipantSucceeded,
    AnswerCallRequest,
    AnswerFailed,
    AzureOpenAIDialog,
    AzureOpenAIDialogUpdate,
    BaseDialog,
    CallConnected,
    CallConnectionProperties,
    CallDisconnected,
    CallIntelligenceOptions,
    CallLocator,
    CallParticipant,
    CallTransferAccepted,
    CallTransferFailed,
    CancelAddParticipantFailed,
    CancelAddParticipantRequest,
    CancelAddParticipantResponse,
    CancelAddParticipantSucceeded,
    ChannelAffinity,
    Choice,
    ChoiceResult,
    CommunicationError,
    CommunicationErrorResponse,
    CommunicationIdentifierModel,
    CommunicationUserIdentifierModel,
    ConnectFailed,
    ConnectRequest,
    ContinuousDtmfRecognitionRequest,
    ContinuousDtmfRecognitionStopped,
    ContinuousDtmfRecognitionToneFailed,
    ContinuousDtmfRecognitionToneReceived,
    CreateCallFailed,
    CreateCallRequest,
    CustomCallingContext,
    DialogCompleted,
    DialogConsent,
    DialogFailed,
    DialogHangup,
    DialogLanguageChange,
    DialogSensitivityUpdate,
    DialogStarted,
    DialogStateResponse,
    DialogTransfer,
    DialogUpdateBase,
    DialogUpdated,
    DtmfOptions,
    DtmfResult,
    Error,
    ExternalStorage,
    FileSource,
    HoldAudioCompleted,
    HoldAudioPaused,
    HoldAudioResumed,
    HoldAudioStarted,
    HoldFailed,
    HoldRequest,
    IncomingCall,
    InterruptAudioAndAnnounceRequest,
    MediaStreamingFailed,
    MediaStreamingOptions,
    MediaStreamingStarted,
    MediaStreamingStopped,
    MediaStreamingSubscription,
    MediaStreamingUpdate,
    MicrosoftTeamsAppIdentifierModel,
    MicrosoftTeamsUserIdentifierModel,
    MoveParticipantFailed,
    MoveParticipantSucceeded,
    MoveParticipantsRequest,
    MoveParticipantsResponse,
    MuteParticipantsRequest,
    MuteParticipantsResult,
    ParticipantsUpdated,
    PhoneNumberIdentifierModel,
    PlayCanceled,
    PlayCompleted,
    PlayFailed,
    PlayOptions,
    PlayPaused,
    PlayRequest,
    PlayResumed,
    PlaySource,
    PlayStarted,
    PostProcessingOptions,
    PowerVirtualAgentsDialog,
    RecognizeCanceled,
    RecognizeCompleted,
    RecognizeFailed,
    RecognizeOptions,
    RecognizeRequest,
    RecordingChunkStorageInfo,
    RecordingResultResponse,
    RecordingStateChanged,
    RecordingStateResponse,
    RecordingStorageInfo,
    RedirectCallRequest,
    RejectCallRequest,
    RemoveParticipantFailed,
    RemoveParticipantRequest,
    RemoveParticipantResponse,
    RemoveParticipantSucceeded,
    ResultInformation,
    SendDtmfTonesCompleted,
    SendDtmfTonesFailed,
    SendDtmfTonesRequest,
    SendDtmfTonesResult,
    SpeechOptions,
    SpeechResult,
    SsmlSource,
    StartCallRecordingRequest,
    StartDialogRequest,
    StartMediaStreamingRequest,
    StartRecordingFailed,
    StartTranscriptionRequest,
    StopMediaStreamingRequest,
    StopTranscriptionRequest,
    Summarization,
    TeamsExtensionUserIdentifierModel,
    TeamsPhoneCallDetails,
    TeamsPhoneCallerDetails,
    TeamsPhoneSourceDetails,
    TextSource,
    Transcription,
    TranscriptionFailed,
    TranscriptionOptions,
    TranscriptionStarted,
    TranscriptionStopped,
    TranscriptionSubscription,
    TranscriptionUpdate,
    TranscriptionUpdated,
    TransferCallResponse,
    TransferToParticipantRequest,
    UnholdRequest,
    UnmuteParticipantsRequest,
    UnmuteParticipantsResponse,
    UpdateDialogRequest,
    UpdateTranscriptionRequest,
    UserConsent,
)

from ._enums import (  # type: ignore
    AudioFormat,
    CallConnectionState,
    CallLocatorKind,
    CallRejectReason,
    CallSessionEndReason,
    ChunkEndReason,
    CommunicationCloudEnvironmentModel,
    CommunicationIdentifierModelKind,
    DialogInputType,
    DtmfTone,
    MediaStreamingAudioChannelType,
    MediaStreamingContentType,
    MediaStreamingStatus,
    MediaStreamingStatusDetails,
    MediaStreamingSubscriptionState,
    MediaStreamingTransportType,
    PlaySourceType,
    RecognitionType,
    RecognizeInputType,
    RecordingChannel,
    RecordingContent,
    RecordingFormat,
    RecordingKind,
    RecordingState,
    RecordingStorageKind,
    TranscriptionResultType,
    TranscriptionStatus,
    TranscriptionStatusDetails,
    TranscriptionSubscriptionState,
    TranscriptionTransportType,
    VoiceKind,
)
from ._patch import __all__ as _patch_all
from ._patch import *
from ._patch import patch_sdk as _patch_sdk

__all__ = [
    "AddParticipantFailed",
    "AddParticipantRequest",
    "AddParticipantResponse",
    "AddParticipantSucceeded",
    "AnswerCallRequest",
    "AnswerFailed",
    "AzureOpenAIDialog",
    "AzureOpenAIDialogUpdate",
    "BaseDialog",
    "CallConnected",
    "CallConnectionProperties",
    "CallDisconnected",
    "CallIntelligenceOptions",
    "CallLocator",
    "CallParticipant",
    "CallTransferAccepted",
    "CallTransferFailed",
    "CancelAddParticipantFailed",
    "CancelAddParticipantRequest",
    "CancelAddParticipantResponse",
    "CancelAddParticipantSucceeded",
    "ChannelAffinity",
    "Choice",
    "ChoiceResult",
    "CommunicationError",
    "CommunicationErrorResponse",
    "CommunicationIdentifierModel",
    "CommunicationUserIdentifierModel",
    "ConnectFailed",
    "ConnectRequest",
    "ContinuousDtmfRecognitionRequest",
    "ContinuousDtmfRecognitionStopped",
    "ContinuousDtmfRecognitionToneFailed",
    "ContinuousDtmfRecognitionToneReceived",
    "CreateCallFailed",
    "CreateCallRequest",
    "CustomCallingContext",
    "DialogCompleted",
    "DialogConsent",
    "DialogFailed",
    "DialogHangup",
    "DialogLanguageChange",
    "DialogSensitivityUpdate",
    "DialogStarted",
    "DialogStateResponse",
    "DialogTransfer",
    "DialogUpdateBase",
    "DialogUpdated",
    "DtmfOptions",
    "DtmfResult",
    "Error",
    "ExternalStorage",
    "FileSource",
    "HoldAudioCompleted",
    "HoldAudioPaused",
    "HoldAudioResumed",
    "HoldAudioStarted",
    "HoldFailed",
    "HoldRequest",
    "IncomingCall",
    "InterruptAudioAndAnnounceRequest",
    "MediaStreamingFailed",
    "MediaStreamingOptions",
    "MediaStreamingStarted",
    "MediaStreamingStopped",
    "MediaStreamingSubscription",
    "MediaStreamingUpdate",
    "MicrosoftTeamsAppIdentifierModel",
    "MicrosoftTeamsUserIdentifierModel",
    "MoveParticipantFailed",
    "MoveParticipantSucceeded",
    "MoveParticipantsRequest",
    "MoveParticipantsResponse",
    "MuteParticipantsRequest",
    "MuteParticipantsResult",
    "ParticipantsUpdated",
    "PhoneNumberIdentifierModel",
    "PlayCanceled",
    "PlayCompleted",
    "PlayFailed",
    "PlayOptions",
    "PlayPaused",
    "PlayRequest",
    "PlayResumed",
    "PlaySource",
    "PlayStarted",
    "PostProcessingOptions",
    "PowerVirtualAgentsDialog",
    "RecognizeCanceled",
    "RecognizeCompleted",
    "RecognizeFailed",
    "RecognizeOptions",
    "RecognizeRequest",
    "RecordingChunkStorageInfo",
    "RecordingResultResponse",
    "RecordingStateChanged",
    "RecordingStateResponse",
    "RecordingStorageInfo",
    "RedirectCallRequest",
    "RejectCallRequest",
    "RemoveParticipantFailed",
    "RemoveParticipantRequest",
    "RemoveParticipantResponse",
    "RemoveParticipantSucceeded",
    "ResultInformation",
    "SendDtmfTonesCompleted",
    "SendDtmfTonesFailed",
    "SendDtmfTonesRequest",
    "SendDtmfTonesResult",
    "SpeechOptions",
    "SpeechResult",
    "SsmlSource",
    "StartCallRecordingRequest",
    "StartDialogRequest",
    "StartMediaStreamingRequest",
    "StartRecordingFailed",
    "StartTranscriptionRequest",
    "StopMediaStreamingRequest",
    "StopTranscriptionRequest",
    "Summarization",
    "TeamsExtensionUserIdentifierModel",
    "TeamsPhoneCallDetails",
    "TeamsPhoneCallerDetails",
    "TeamsPhoneSourceDetails",
    "TextSource",
    "Transcription",
    "TranscriptionFailed",
    "TranscriptionOptions",
    "TranscriptionStarted",
    "TranscriptionStopped",
    "TranscriptionSubscription",
    "TranscriptionUpdate",
    "TranscriptionUpdated",
    "TransferCallResponse",
    "TransferToParticipantRequest",
    "UnholdRequest",
    "UnmuteParticipantsRequest",
    "UnmuteParticipantsResponse",
    "UpdateDialogRequest",
    "UpdateTranscriptionRequest",
    "UserConsent",
    "AudioFormat",
    "CallConnectionState",
    "CallLocatorKind",
    "CallRejectReason",
    "CallSessionEndReason",
    "ChunkEndReason",
    "CommunicationCloudEnvironmentModel",
    "CommunicationIdentifierModelKind",
    "DialogInputType",
    "DtmfTone",
    "MediaStreamingAudioChannelType",
    "MediaStreamingContentType",
    "MediaStreamingStatus",
    "MediaStreamingStatusDetails",
    "MediaStreamingSubscriptionState",
    "MediaStreamingTransportType",
    "PlaySourceType",
    "RecognitionType",
    "RecognizeInputType",
    "RecordingChannel",
    "RecordingContent",
    "RecordingFormat",
    "RecordingKind",
    "RecordingState",
    "RecordingStorageKind",
    "TranscriptionResultType",
    "TranscriptionStatus",
    "TranscriptionStatusDetails",
    "TranscriptionSubscriptionState",
    "TranscriptionTransportType",
    "VoiceKind",
]
__all__.extend([p for p in _patch_all if p not in __all__])  # pyright: ignore
_patch_sdk()
