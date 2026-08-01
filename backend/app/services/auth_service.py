import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core import mailer
from app.core.config import settings
from app.core.errors import AppError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import AppUser
from app.repositories import (
    email_verification_repository,
    password_reset_repository,
    user_repository,
)
from app.schemas.user import (
    LoginRequest,
    PasswordResetRequest,
    PasswordResetRequestResponse,
    RegisterRequest,
    ResetPasswordRequest,
    SendVerificationCodeRequest,
    SendVerificationCodeResponse,
)


logger = logging.getLogger(__name__)


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def send_verification_code(
    db: Session, payload: SendVerificationCodeRequest
) -> SendVerificationCodeResponse:
    """寄送註冊用 Email 驗證碼。

    已註冊的 Email 直接拒絕——註冊本來就會回報 EMAIL_ALREADY_EXISTS，
    這裡提早擋住可以避免對已註冊者寄出無意義的驗證信。
    """
    email = payload.email
    if user_repository.get_by_email(db, email) is not None:
        raise AppError(409, "EMAIL_ALREADY_EXISTS", "此 Email 已被註冊。")

    now = datetime.now(timezone.utc)

    latest = email_verification_repository.get_latest(db, email)
    if latest is not None:
        elapsed = (now - _as_utc(latest.created_at)).total_seconds()
        interval = settings.verification_code_resend_interval_seconds
        if elapsed < interval:
            raise AppError(
                429,
                "VERIFICATION_CODE_TOO_FREQUENT",
                f"驗證碼寄送過於頻繁，請於 {int(interval - elapsed)} 秒後再試。",
            )

    sent_today = email_verification_repository.count_since(db, email, now - timedelta(days=1))
    if sent_today >= settings.verification_code_daily_limit:
        raise AppError(
            429,
            "VERIFICATION_CODE_DAILY_LIMIT_REACHED",
            "今日驗證碼寄送次數已達上限，請明天再試。",
        )

    code = f"{secrets.randbelow(1_000_000):06d}"
    ttl_minutes = settings.verification_code_ttl_minutes

    email_verification_repository.invalidate_unconsumed(db, email, now)
    email_verification_repository.create(
        db, email, _hash_code(code), now + timedelta(minutes=ttl_minutes), now
    )

    try:
        mailer.send_verification_code(email, code, ttl_minutes)
    except Exception as error:  # noqa: BLE001 — 寄信失敗要回報給使用者而非讓 500 洩漏細節
        # 一定要記 traceback：包成 AppError 之後就走 app_error_handler，
        # 不會留下任何線索。線上曾因此只能靠回應時間推斷 Render 封鎖了 SMTP。
        logger.exception("驗證碼寄送失敗，收件人=%s", email)
        raise AppError(
            502, "VERIFICATION_CODE_SEND_FAILED", "驗證碼寄送失敗，請稍後再試。"
        ) from error

    return SendVerificationCodeResponse(
        email=email,
        expires_in_seconds=ttl_minutes * 60,
        resend_available_in_seconds=settings.verification_code_resend_interval_seconds,
    )


def _as_utc(value: datetime) -> datetime:
    """資料庫取回的時間可能沒有 tzinfo，統一補上 UTC 再做運算。"""
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _consume_verification_code(db: Session, email: str, code: str) -> None:
    now = datetime.now(timezone.utc)
    record = email_verification_repository.get_latest_usable(db, email, now)
    if record is None:
        raise AppError(
            400, "VERIFICATION_CODE_INVALID", "驗證碼不存在或已失效，請重新取得驗證碼。"
        )

    if record.attempt_count >= settings.verification_code_max_attempts:
        raise AppError(
            400, "VERIFICATION_CODE_INVALID", "驗證碼錯誤次數過多，請重新取得驗證碼。"
        )

    if not secrets.compare_digest(record.code_hash, _hash_code(code)):
        email_verification_repository.mark_attempt(db, record)
        raise AppError(400, "VERIFICATION_CODE_INVALID", "驗證碼錯誤，請重新確認。")

    # 與建立帳號同一個 Transaction，註冊失敗時驗證碼不會被消耗
    email_verification_repository.mark_consumed(db, record)


def register(db: Session, payload: RegisterRequest) -> AppUser:
    """依 Business Rules §6：Email 不可重複、密碼安全雜湊、註冊後不自動登入。

    另依使用者需求要求通過 Email 驗證碼（規格外擴充）。
    """
    if user_repository.get_by_email(db, payload.email) is not None:
        raise AppError(409, "EMAIL_ALREADY_EXISTS", "此 Email 已被註冊。")

    _consume_verification_code(db, payload.email, payload.verification_code)

    user = AppUser(
        email=payload.email,
        password_hash=hash_password(payload.password),
        nickname=payload.nickname,
        facebook_contact=payload.facebook_contact,
        discord_contact=payload.discord_contact,
        line_contact=payload.line_contact,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def request_password_reset(
    db: Session, payload: PasswordResetRequest
) -> PasswordResetRequestResponse:
    """寄送重設密碼連結。

    找不到該 Email 時「照樣回報成功」而不是回 404：否則這支 API 會變成
    帳號列舉工具，任何人都能逐一測出哪些 Email 有註冊。
    這也是為什麼前端提示語只說「若這個 Email 已註冊，我們已寄出信件」。
    """
    ttl_minutes = settings.password_reset_ttl_minutes
    response = PasswordResetRequestResponse(
        email=payload.email, expires_in_seconds=ttl_minutes * 60
    )

    user = user_repository.get_by_email(db, payload.email)
    if user is None:
        return response

    now = datetime.now(timezone.utc)
    latest = password_reset_repository.get_latest_by_user(db, user.id)
    if latest is not None:
        elapsed = (now - _as_utc(latest.created_at)).total_seconds()
        interval = settings.password_reset_resend_interval_seconds
        if elapsed < interval:
            raise AppError(
                429,
                "PASSWORD_RESET_TOO_FREQUENT",
                f"重設信件寄送過於頻繁，請於 {int(interval - elapsed)} 秒後再試。",
            )

    # token 進網址，用 URL-safe 隨機字串；資料庫只留雜湊
    token = secrets.token_urlsafe(32)
    password_reset_repository.invalidate_unconsumed(db, user.id, now)
    password_reset_repository.create(
        db, user.id, _hash_code(token), now + timedelta(minutes=ttl_minutes), now
    )

    reset_url = f"{settings.frontend_base_url.rstrip('/')}/reset-password?token={token}"
    try:
        mailer.send_password_reset(user.email, user.nickname, reset_url, ttl_minutes)
    except Exception as error:  # noqa: BLE001 — 寄信失敗要回報給使用者而非 500
        logger.exception("重設密碼信寄送失敗，收件人=%s", user.email)
        raise AppError(
            502, "PASSWORD_RESET_SEND_FAILED", "重設信件寄送失敗，請稍後再試。"
        ) from error

    return response


def reset_password(db: Session, payload: ResetPasswordRequest) -> None:
    """以信件中的 token 設定新密碼；token 單次使用。"""
    now = datetime.now(timezone.utc)
    record = password_reset_repository.get_usable_by_hash(db, _hash_code(payload.token), now)
    if record is None:
        raise AppError(
            400,
            "PASSWORD_RESET_TOKEN_INVALID",
            "重設連結無效或已過期，請重新申請。",
        )

    user = user_repository.get_by_id(db, record.user_id)
    if user is None:
        raise AppError(
            400,
            "PASSWORD_RESET_TOKEN_INVALID",
            "重設連結無效或已過期，請重新申請。",
        )

    # 標記已使用與更新密碼在同一個 Transaction，避免只完成其中一半
    user.password_hash = hash_password(payload.password)
    password_reset_repository.mark_consumed(db, record, now)
    db.commit()


def verify_password_reset_token(db: Session, token: str) -> bool:
    """供前端在顯示表單前先確認連結是否還有效。"""
    now = datetime.now(timezone.utc)
    return password_reset_repository.get_usable_by_hash(db, _hash_code(token), now) is not None


def login(db: Session, payload: LoginRequest) -> tuple[str, int]:
    """依 Business Rules §6.3/§6.5：登入失敗不得透露 Email 是否存在，成功回傳 Access Token。

    同一個 Email 可能同時有管理員與一般用戶兩個帳號（使用者 2026-07-31 裁決：
    兩者是分開的身分），因此逐一比對密碼，由密碼決定登入哪一個。
    list_by_email 讓管理員排在前面，兩邊密碼相同時登入管理員，既有管理員帳號
    的行為不會因為別人用同 Email 註冊而改變。
    """
    for user in user_repository.list_by_email(db, payload.email):
        if verify_password(payload.password, user.password_hash):
            return create_access_token(user.id)

    raise AppError(401, "AUTH_INVALID_CREDENTIALS", "Email 或密碼錯誤。")
