"""測試資料庫隔離（specs/002-test-db-isolation）：guard 檢查與 test engine。

只有 pytest（conftest.py、安全測試）與 scripts/build_test_schema.py 使用本模組；
應用程式（app/）任何執行路徑都不得 import。

隔離方式為同一 Supabase 專案內的獨立 schema（軟隔離）：
- 連線走 Session pooler（5432）——SET search_path 是 session 狀態，
  transaction pooler（6543）不保證跨語句存活，session pooler 實測可靠。
- 每條新連線以 connect 事件把 search_path 釘在測試 schema，且不含 public，
  測試 schema 缺表時寧可報錯也不能靜默回退主庫。
"""

from sqlalchemy import Engine, create_engine, event, text

from app.core.config import settings

MAIN_SCHEMA = "public"


class IsolationConfigError(Exception):
    """測試資料庫隔離設定不合格；訊息需說明原因與修正方式。"""


def validate_test_db_settings(url: str, schema: str) -> None:
    """G1／G2：純設定值檢查，不連線。不合格即 raise IsolationConfigError。"""
    if not url or not url.strip():
        raise IsolationConfigError(
            "未設定 TEST_DATABASE_URL：測試不會退回使用 DATABASE_URL（主要資料庫）。\n"
            "請在 backend/.env 加入 TEST_DATABASE_URL（Supabase Session pooler 5432，"
            "格式同 ALEMBIC_DATABASE_URL），再執行 scripts/build_test_schema.py 建立測試 schema。"
        )
    normalized = (schema or "").strip()
    if not normalized:
        raise IsolationConfigError(
            "TEST_DATABASE_SCHEMA 為空白：測試必須指定獨立的測試 schema，"
            "不得落在預設的主要資料區。"
        )
    if normalized.lower() == MAIN_SCHEMA:
        raise IsolationConfigError(
            "TEST_DATABASE_SCHEMA 不得為 public：public 是網站正式運作的主要資料區，"
            "測試禁止指向它。請改用獨立的測試 schema（預設 wuwa_test）。"
        )


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def create_test_engine(url: str, schema: str) -> Engine:
    """建立測試專用 engine：NullPool＋每條連線 SET search_path TO 測試 schema。

    先跑 G1／G2 再建 engine，保證不可能拿到指向 public 的 test engine。
    """
    validate_test_db_settings(url, schema)
    # 小型常駐池而非 NullPool：資料庫在 ap-south-1，每次重建連線要付
    # TCP+TLS 握手成本，數百個測試累積會差出數十分鐘（實測 NullPool 版
    # 跑不完）。單一連線重用即可，測試是序列執行；連線歸還時 pool 只做
    # rollback、不重置 session 狀態，search_path 得以保留。
    engine = create_engine(
        url,
        pool_size=1,
        max_overflow=2,
        pool_pre_ping=True,
        future=True,
        connect_args={"prepare_threshold": None},
    )

    @event.listens_for(engine, "connect")
    def _pin_search_path(dbapi_connection, connection_record):  # noqa: ANN001
        # 必須在 autocommit 下執行：SET（非 LOCAL）是交易性的，若在隱式交易內
        # 執行，連線歸還連線池時的 rollback 會把 search_path 撤銷，重用的連線
        # 就會落回預設（public）——這正是隔離要防的事故，安全測試會抓。
        dbapi_connection.autocommit = True
        cursor = dbapi_connection.cursor()
        # 不含 public：測試 schema 缺表時要直接報錯，不可回退主庫
        cursor.execute(f"SET search_path TO {_quote_ident(schema)}")
        cursor.close()
        dbapi_connection.autocommit = False

    return engine


def assert_isolated_connection(engine: Engine, schema: str) -> None:
    """G3／G4：實連驗證 search_path 生效且測試 schema 存在。"""
    with engine.connect() as conn:
        exists = conn.execute(
            text("SELECT count(*) FROM pg_namespace WHERE nspname = :schema"),
            {"schema": schema},
        ).scalar()
        if not exists:
            raise IsolationConfigError(
                f"測試 schema「{schema}」不存在。"
                "請先執行 backend/scripts/build_test_schema.py 建立測試 schema。"
            )
        current = conn.execute(text("SELECT current_schema()")).scalar()
        if current != schema:
            raise IsolationConfigError(
                f"search_path 未生效：current_schema() 為「{current}」，"
                f"預期為測試 schema「{schema}」。測試連線視同指向主要資料區，中止執行。"
            )


_engine: Engine | None = None


def get_test_engine() -> Engine:
    """惰性單例：第一次取得時執行 G1／G2 並建立 engine。"""
    global _engine
    if _engine is None:
        _engine = create_test_engine(
            settings.test_database_url, settings.test_database_schema
        )
    return _engine
