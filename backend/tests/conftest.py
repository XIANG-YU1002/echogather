import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Stage 2 起，API 整合測試需要真正的 PostgreSQL 連線（依使用者決議直接使用現有 Supabase
# 專案，見 docs/目前進度.txt），因此需要本機存在有效的 backend/.env。
# 每個測試都在一個交易內執行，測試結束後 rollback，不會在 Supabase 留下任何資料。

from app.core.config import settings  # noqa: E402
from app.core.database import get_db  # noqa: E402
from app.main import app  # noqa: E402
from tests._isolation import (  # noqa: E402
    IsolationConfigError,
    assert_isolated_connection,
    get_test_engine,
)


def pytest_configure(config):
    """測試資料庫隔離 guard（specs/002-test-db-isolation）。

    在收集／執行任何測試之前檢查：
    G1 已設定 TEST_DATABASE_URL（絕不退回 DATABASE_URL）、
    G2 測試 schema 不是 public、
    G3/G4 實連確認 search_path 生效且測試 schema 存在。
    任一不通過即中止整個 pytest session（已執行案例數 0）。
    """
    try:
        test_engine = get_test_engine()
        assert_isolated_connection(test_engine, settings.test_database_schema)
    except IsolationConfigError as exc:
        raise pytest.UsageError(f"\n[測試資料庫隔離] {exc}") from exc


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
    # 002-test-db-isolation：連線一律走測試專用 engine（search_path 釘在測試
    # schema、不含 public），絕不使用 app.core.database.engine（主要資料庫）。
    connection = get_test_engine().connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def admin_headers(client, db_session: Session):
    """已登入 Admin 的授權標頭（specs/003-admin-permission-hardening）。

    沿用既有 factories/utils 的建立方式，只是把 role 設為 admin；
    各 admin API 測試檔內既有的 _admin_headers helper 不受影響。
    """
    from app.models.enums import UserRole
    from tests.factories import create_user
    from tests.utils import auth_headers, login

    admin = create_user(db_session, role=UserRole.ADMIN)
    return auth_headers(login(client, admin.email, "Passw0rd1"))


@pytest.fixture()
def client(db_session: Session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
