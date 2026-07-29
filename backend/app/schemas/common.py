import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated

from pydantic import PlainSerializer


def _serialize_money(value: Decimal) -> str:
    return f"{value:.2f}"


def _serialize_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


Money = Annotated[Decimal, PlainSerializer(_serialize_money, return_type=str)]
UTCDateTime = Annotated[datetime, PlainSerializer(_serialize_datetime, return_type=str)]


def normalize_optional_text(value: str | None) -> str | None:
    """依 Business Rules §2.3：Trim 後空字串／純空白正規化為 None。"""
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed if trimmed else None


# Facebook 聯絡方式填的是個人頁連結。https:// 與 www. 皆可省略（既有資料就有
# facebook.com/xxx 這種寫法），但不接受只填帳號名稱。
_FACEBOOK_URL_PATTERN = re.compile(
    r"^(https?://)?([\w-]+\.)?(facebook\.com|fb\.com|fb\.me)/\S+$", re.IGNORECASE
)

FACEBOOK_URL_ERROR = "請輸入 Facebook 連結（例如 https://www.facebook.com/yourname）。"


def is_facebook_url(value: str) -> bool:
    """Facebook 聯絡方式是否為連結。

    會員聯絡欄位、團主公開聯絡方式、開團的主要聯絡方式共用同一套規則——
    只有會員端做驗證的話，同一個平台在不同頁面會有不同標準。
    """
    return bool(_FACEBOOK_URL_PATTERN.match(value))
