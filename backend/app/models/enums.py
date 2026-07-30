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
    # 被合併進另一張訂單的來源訂單（使用者 2026-07-30 裁決）。前台會員端與團主端
    # 一律不顯示這種訂單，資料完整保留以供拆單還原；不佔用庫存、不計入任何統計。
    # 刻意不沿用 cancelled——否則會被算進「已取消」的頁籤數字，且每個查詢都得記得排除。
    MERGED = "merged"


class GroupBuyListSort(str, enum.Enum):
    """圖 21 我的開團的排序下拉。

    參考圖寫的是「活動時間」，但 activity 沒有起訖日期欄位（使用者裁決不新增），
    因此改以開團建立時間排序——同一活動的多輪開團本來就是依建立時間分第 N 團，
    語意一致。
    """

    CREATED_DESC = "created_desc"
    CREATED_ASC = "created_asc"


class GroupLeaderOrderStatusFilter(str, enum.Enum):
    """團主訂單列表的 status 篩選值。

    除了 OrderStatus 的各個實際狀態，另外提供複合值 pending＝「待處理」，
    同時涵蓋待確認與待付款——依使用者 2026-07-29 說明，這兩種都是團主要處理的，
    圖 20 統計卡的「待處理訂單」就是兩者合計，點卡片必須能看到完整清單。
    這裡刻意逐項列出而不動態生成，讓 OpenAPI 與編輯器都看得到完整選項。
    """

    PENDING = "pending"
    PENDING_CONFIRMATION = "pending_confirmation"
    PENDING_PAYMENT = "pending_payment"
    PAID = "paid"
    SHIPPED = "shipped"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

    def to_order_statuses(self) -> list[OrderStatus]:
        """展開成實際的訂單狀態清單。"""
        if self is GroupLeaderOrderStatusFilter.PENDING:
            return list(PENDING_ORDER_STATUSES)
        return [OrderStatus(self.value)]


# 「待處理」的組成。團主端統計與篩選都以此為單一來源，避免兩處各寫一份而不同步。
PENDING_ORDER_STATUSES = (OrderStatus.PENDING_CONFIRMATION, OrderStatus.PENDING_PAYMENT)

# 合併後仍可拆回的訂單狀態（使用者 2026-07-30）。已出貨之後不再拆，已取消／已拒絕沒有意義。
# 與可合併狀態刻意一致。放在 enums 是因為訂單、通知、團主三個 service 都要判斷，
# 而 notification_service 不能 import order_service（會形成循環匯入）。
UNMERGE_ALLOWED_STATUSES = (
    OrderStatus.PENDING_CONFIRMATION,
    OrderStatus.PENDING_PAYMENT,
    OrderStatus.PAID,
)


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
