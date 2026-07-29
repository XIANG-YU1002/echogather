import re
import uuid

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.enums import GroupLeaderApplicationStatus, UserRole
from app.schemas.common import (
    FACEBOOK_URL_ERROR,
    UTCDateTime,
    is_facebook_url,
    normalize_optional_text,
)

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PASSWORD_HAS_LETTER = re.compile(r"[A-Za-z]")
_PASSWORD_HAS_DIGIT = re.compile(r"\d")


def validate_password_strength(value: str) -> str:
    """密碼規則。註冊與重設密碼共用，兩邊規則必須一致。"""
    if not value:
        raise ValueError("請輸入密碼。")
    if not 8 <= len(value) <= 72:
        raise ValueError("密碼長度需為 8 至 72 個字元。")
    if not _PASSWORD_HAS_LETTER.search(value) or not _PASSWORD_HAS_DIGIT.search(value):
        raise ValueError("密碼至少需包含一個英文字母及一個數字。")
    return value


class ContactFieldsMixin(BaseModel):
    facebook_contact: str | None = None
    discord_contact: str | None = None
    line_contact: str | None = None

    @field_validator("facebook_contact", "discord_contact", "line_contact", mode="before")
    @classmethod
    def _normalize_contacts(cls, value: str | None) -> str | None:
        return normalize_optional_text(value)

    @field_validator("facebook_contact")
    @classmethod
    def _validate_facebook_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not is_facebook_url(value):
            raise ValueError(FACEBOOK_URL_ERROR)
        return value


class SendVerificationCodeRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        trimmed = value.strip().lower()
        if not _EMAIL_PATTERN.match(trimmed):
            raise ValueError("請輸入有效的 Email。")
        return trimmed


class SendVerificationCodeResponse(BaseModel):
    email: str
    expires_in_seconds: int
    resend_available_in_seconds: int


class PasswordResetRequest(BaseModel):
    """申請重設密碼（寄送重設連結）。"""

    email: str

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        trimmed = value.strip().lower()
        if not trimmed:
            raise ValueError("請輸入 Email。")
        if not _EMAIL_PATTERN.match(trimmed):
            raise ValueError("請輸入有效的 Email。")
        return trimmed


class PasswordResetRequestResponse(BaseModel):
    """一律回報成功，不透露該 Email 是否存在（避免帳號列舉）。"""

    email: str
    expires_in_seconds: int


class ResetPasswordRequest(BaseModel):
    """以信件中的 token 設定新密碼。密碼規則與註冊相同。"""

    token: str
    password: str
    password_confirmation: str

    @field_validator("token")
    @classmethod
    def _validate_token(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("重設連結無效，請重新申請。")
        return trimmed

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        return validate_password_strength(value)

    @field_validator("password_confirmation")
    @classmethod
    def _validate_password_confirmation(cls, value: str) -> str:
        if not value:
            raise ValueError("請再次輸入密碼。")
        return value

    @model_validator(mode="after")
    def _validate_passwords_match(self) -> "ResetPasswordRequest":
        if self.password != self.password_confirmation:
            raise ValueError("密碼與密碼確認不一致。")
        return self


class RegisterRequest(ContactFieldsMixin):
    email: str
    # 長度不用 Field(min_length=...)，那會回傳 pydantic 的英文內建訊息；
    # 改在 validator 內檢查以輸出中文提示。
    password: str
    password_confirmation: str
    nickname: str
    verification_code: str

    @field_validator("verification_code")
    @classmethod
    def _normalize_verification_code(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("請輸入 Email 驗證碼。")
        return trimmed

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        trimmed = value.strip().lower()
        # 未填與格式錯誤分開提示，否則使用者根本沒填卻被講格式不對
        if not trimmed:
            raise ValueError("請輸入 Email。")
        if not _EMAIL_PATTERN.match(trimmed):
            raise ValueError("請輸入有效的 Email。")
        return trimmed

    @field_validator("nickname")
    @classmethod
    def _validate_nickname(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("請輸入暱稱。")
        return trimmed

    @field_validator("password_confirmation")
    @classmethod
    def _validate_password_confirmation(cls, value: str) -> str:
        if not value:
            raise ValueError("請再次輸入密碼。")
        return value

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        return validate_password_strength(value)

    @model_validator(mode="after")
    def _validate_cross_field_rules(self) -> "RegisterRequest":
        """跨欄位檢查集中在同一個 validator。

        pydantic 的多個 model_validator 是依序執行、第一個拋錯就中止，
        分開寫會讓使用者一次只看到一項問題。這裡收集完再一起回報，
        多筆訊息以換行分隔，由 validation_error_handler 拆成多筆。
        """
        errors = []
        if self.password != self.password_confirmation:
            errors.append("密碼與密碼確認不一致。")
        if not (self.facebook_contact or self.discord_contact or self.line_contact):
            errors.append("至少需要提供一項聯絡方式。")
        if errors:
            raise ValueError("\n".join(errors))
        return self


class RegisterResponse(BaseModel):
    id: uuid.UUID
    email: str
    nickname: str
    avatar_url: str | None
    created_at: UTCDateTime


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class GroupLeaderSessionSummary(BaseModel):
    id: uuid.UUID
    display_name: str | None
    is_profile_complete: bool


class PermissionsSummary(BaseModel):
    is_admin: bool
    has_group_leader_profile: bool
    can_manage_group_buys: bool


class CurrentSessionResponse(BaseModel):
    id: uuid.UUID
    email: str
    nickname: str
    avatar_url: str | None
    role: UserRole
    group_leader: GroupLeaderSessionSummary | None
    permissions: PermissionsSummary


class LatestApplicationSummary(BaseModel):
    id: uuid.UUID
    status: GroupLeaderApplicationStatus
    created_at: UTCDateTime
    reviewed_at: UTCDateTime | None


class GroupLeaderProfileSummary(BaseModel):
    id: uuid.UUID
    display_name: str | None
    is_profile_complete: bool


class UserProfileResponse(BaseModel):
    id: uuid.UUID
    email: str
    nickname: str
    avatar_url: str | None
    facebook_contact: str | None
    discord_contact: str | None
    line_contact: str | None
    role: UserRole
    created_at: UTCDateTime
    latest_group_leader_application: LatestApplicationSummary | None
    group_leader_profile: GroupLeaderProfileSummary | None


class UpdateProfileRequest(BaseModel):
    nickname: str | None = None
    avatar_url: str | None = None

    @field_validator("nickname")
    @classmethod
    def _validate_nickname(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("暱稱不可為空。")
        return trimmed

    @model_validator(mode="after")
    def _validate_at_least_one_field(self) -> "UpdateProfileRequest":
        if self.nickname is None and self.avatar_url is None:
            raise ValueError("至少需要提供一個欄位。")
        return self


class UpdateContactsRequest(ContactFieldsMixin):
    pass
