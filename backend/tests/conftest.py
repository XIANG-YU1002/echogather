import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Stage 2 起，API 整合測試需要真正的 PostgreSQL 連線（依使用者決議直接使用現有 Supabase
# 專案，見 docs/目前進度.txt），因此需要本機存在有效的 backend/.env。
# 每個測試都在一個交易內執行，測試結束後 rollback，不會在 Supabase 留下任何資料。

from app.core.config import settings  # noqa: E402
from app.core.database import engine, get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def _never_send_real_email(monkeypatch):
    """測試絕不寄真信。

    backend/.env 填了寄信憑證之後，註冊驗證碼與重設密碼的測試會真的寄信到
    測試用的假信箱（會退信，也可能觸發 Gmail 的濫用限制）。
    這裡把兩條寄信管道的憑證都清空，讓 mailer.send_email 走「未設定寄信管道」
    的分支改寫 log——與 .env 沒有任何寄信設定時的既有測試行為一致。

    兩個都要清：mailer 會優先走 Gmail API，只清 smtp_user 攔不住它。
    """
    monkeypatch.setattr(settings, "smtp_user", "")
    monkeypatch.setattr(settings, "gmail_refresh_token", "")


@pytest.fixture()
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db_session: Session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
