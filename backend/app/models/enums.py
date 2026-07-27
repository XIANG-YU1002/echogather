import enum


class UserRole(str, enum.Enum):
    MEMBER = "member"
    ADMIN = "admin"


class GroupLeaderApplicationStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ActivityStatus(str, enum.Enum):
    OPEN = "open"
    ENDED = "ended"


class GroupBuyStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"


class PaymentMethod(str, enum.Enum):
    BANK_TRANSFER = "bank_transfer"
    CASH_ON_DELIVERY = "cash_on_delivery"


class ContactPlatform(str, enum.Enum):
    FACEBOOK = "facebook"
    DISCORD = "discord"
    LINE = "line"


class OrderStatus(str, enum.Enum):
    PENDING_CONFIRMATION = "pending_confirmation"
    PENDING_PAYMENT = "pending_payment"
    PAID = "paid"
    SHIPPED = "shipped"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class CancellationStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class AnnouncementType(str, enum.Enum):
    PLATFORM = "platform"
    GROUP_LEADER = "group_leader"


class AnnouncementAudienceScope(str, enum.Enum):
    LEADER_UNFINISHED = "leader_unfinished"
    GROUP_BUY_UNFINISHED = "group_buy_unfinished"


class NotificationType(str, enum.Enum):
    SYSTEM = "system"
    GROUP_LEADER = "group_leader"


class Currency(str, enum.Enum):
    """擴充 Enum：僅用於 product.official_currency（見需求追蹤矩陣衝突解法 #2）。
    團主售價 group_buy_product.unit_price 與訂單金額固定 TWD，不使用此 Enum。
    """

    TWD = "TWD"
    CNY = "CNY"
    JPY = "JPY"
    KRW = "KRW"
    USD = "USD"
