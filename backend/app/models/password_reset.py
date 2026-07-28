import uuid

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class PasswordResetToken(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """忘記密碼的重設token。

    只儲存 token 的 SHA-256 雜湊：資料庫外洩時無法反推出可用的重設連結。
    每筆單次使用（`consumed_at`），並有有效期限。
    """

    __tablename__ = "password_reset_token"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_password_reset_token_user_created", "user_id", "created_at"),
    )
