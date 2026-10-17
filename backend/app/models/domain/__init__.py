from .base import Base, TimestampMixin, UniversalUUID, TIMESTAMPTZ, BigIntPK
from .user import User
from .match_and_chat import Swipe, Match, Message
from .monetization import (
    AdRewardLedger,
    ProcessedAdTransaction,
    InAppPurchase,
    PendingWebEntitlement,
)
from .revelation import (
    ContactRevealToken,
    PhotoRevealConsent,
)
from .blind_date import (
    BlindDateQueue,
    BlindDateSession,
    BlindDateMessage,
)
from .legal import (
    UnderageQuarantineRegistry,
    DataNominee,
    DataExportRequest,
    ConsentAuditLog,
    GrievanceDossier,
    BlockedUser,
    WebDeletionToken,
    ConsumedMagicToken,
)
from .admin_telemetry import (
    AdminKycEscalation,
    DeviceFcmToken,
    AdminAuditLog,
)

__all__ = [
    "Base",
    "TimestampMixin",
    # 24 Domain Models
    "User",
    "Swipe",
    "Match",
    "Message",
    "AdRewardLedger",
    "ProcessedAdTransaction",
    "InAppPurchase",
    "PendingWebEntitlement",
    "ContactRevealToken",
    "PhotoRevealConsent",
    "BlindDateQueue",
    "BlindDateSession",
    "BlindDateMessage",
    "UnderageQuarantineRegistry",
    "DataNominee",
    "DataExportRequest",
    "ConsentAuditLog",
    "GrievanceDossier",
    "BlockedUser",
    "WebDeletionToken",
    "ConsumedMagicToken",
    "AdminKycEscalation",
    "DeviceFcmToken",
    "AdminAuditLog",
]
