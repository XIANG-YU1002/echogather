"""重建測試 schema（specs/002-test-db-isolation，FR-007）。

用法（於 backend/ 目錄）：
    venv\\Scripts\\python scripts\\build_test_schema.py

流程：guard 檢查（同 pytest 的 G1／G2）→ DROP/CREATE 測試 schema →
以 search_path 綁定的連線執行 alembic upgrade head → 回報驗證結果。
可重複執行：每次都整個 schema 打掉重建，不留舊測試資料。

對主要資料區（public）保證唯讀：本腳本所有 DDL 都以測試 schema 為
search_path 首位，且 DROP/CREATE 目標為帶引號的測試 schema 名稱。
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.config import settings  # noqa: E402
from tests._isolation import _quote_ident, create_test_engine  # noqa: E402

# 建置期 search_path 尾巴：migration 的 DDL 需要解析
# gin_trgm_ops（pg_trgm，實測位於 public）與 extensions 下的函式；
# 全新 schema 從 0001 依序建表，未限定的表引用永遠先命中測試 schema，
# 所以 public 在此僅供函式／operator class 解析（見 research.md R4）。
# 測試「執行期」的 search_path 仍只有測試 schema（tests/_isolation.py）。
BUILD_SEARCH_PATH_TAIL = '"extensions", "public"'


def main() -> None:
    schema = settings.test_database_schema
    # create_test_engine 內含 G1／G2 guard：未設定或指向 public 時直接中止
    engine = create_test_engine(settings.test_database_url, schema)
    q = _quote_ident(schema)

    print(f"重建測試 schema {schema} ...")
    with engine.begin() as conn:
        conn.execute(text(f"DROP SCHEMA IF EXISTS {q} CASCADE"))
        conn.execute(text(f"CREATE SCHEMA {q}"))

    with engine.connect() as conn:
        conn.execute(text(f"SET search_path TO {q}, {BUILD_SEARCH_PATH_TAIL}"))
        conn.commit()

        cfg = Config(str(BACKEND_DIR / "alembic.ini"))
        cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
        cfg.attributes["connection"] = conn
        cfg.attributes["version_table_schema"] = schema
        command.upgrade(cfg, "head")

        # 驗證：資料表數、alembic 版本、search_path 落點
        table_count = conn.execute(
            text(
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_schema = :s AND table_type = 'BASE TABLE'"
            ),
            {"s": schema},
        ).scalar()
        version = conn.execute(
            text(f"SELECT version_num FROM {q}.alembic_version")
        ).scalar()
        current = conn.execute(text("SELECT current_schema()")).scalar()

    print(f"完成：{schema} 內建立 {table_count} 個資料表（含 alembic_version）")
    print(f"alembic head: {version}")
    print(f"current_schema(): {current}")


if __name__ == "__main__":
    main()
