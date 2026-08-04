"""FR-008 安全測試：驗證測試資料庫隔離的防呆本身（specs/002-test-db-isolation）。

單元測試直接打 guard 純函式（G1／G2），不需要真的錯連主庫；
整合測試確認目前測試連線真的落在測試 schema、而不是 public。
"""

import pytest
from sqlalchemy import text

from app.core.config import settings
from tests._isolation import (
    MAIN_SCHEMA,
    IsolationConfigError,
    create_test_engine,
    get_test_engine,
    validate_test_db_settings,
)

VALID_URL = "postgresql+psycopg://user:pw@example.invalid:5432/postgres"


class TestValidateTestDbSettings:
    def test_未設定連線時拒絕(self):
        with pytest.raises(IsolationConfigError, match="TEST_DATABASE_URL"):
            validate_test_db_settings("", "wuwa_test")

    def test_連線為空白時拒絕(self):
        with pytest.raises(IsolationConfigError, match="TEST_DATABASE_URL"):
            validate_test_db_settings("   ", "wuwa_test")

    @pytest.mark.parametrize("schema", ["public", "Public", "PUBLIC", " public "])
    def test_指向主要資料區時拒絕(self, schema):
        with pytest.raises(IsolationConfigError, match="public"):
            validate_test_db_settings(VALID_URL, schema)

    @pytest.mark.parametrize("schema", ["", "   "])
    def test_未指定測試schema時拒絕(self, schema):
        with pytest.raises(IsolationConfigError, match="TEST_DATABASE_SCHEMA"):
            validate_test_db_settings(VALID_URL, schema)

    def test_合法設定通過(self):
        validate_test_db_settings(VALID_URL, "wuwa_test")

    def test_create_test_engine同樣套用檢查(self):
        with pytest.raises(IsolationConfigError):
            create_test_engine(VALID_URL, MAIN_SCHEMA)


class TestIsolatedConnection:
    def test_測試連線落在測試schema而非public(self):
        engine = get_test_engine()
        with engine.connect() as conn:
            current = conn.execute(text("SELECT current_schema()")).scalar()
        assert current == settings.test_database_schema
        assert current != MAIN_SCHEMA

    def test_search_path不含public(self):
        engine = get_test_engine()
        with engine.connect() as conn:
            search_path = conn.execute(text("SHOW search_path")).scalar()
        assert MAIN_SCHEMA not in search_path

    def test_連線歸還池再重用後search_path仍在測試schema(self):
        """回歸測試：SET search_path 若在隱式交易內執行，歸還池時的 rollback
        會把它撤銷，重用連線就落回 public。必須以 autocommit 設定才能存活。"""
        engine = get_test_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        # 離開 with → rollback → 歸還池；pool_size=1 下一次 connect 重用同一條
        with engine.connect() as conn:
            current = conn.execute(text("SELECT current_schema()")).scalar()
        assert current == settings.test_database_schema
        assert current != MAIN_SCHEMA
