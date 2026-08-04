from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.models import Base

config = context.config
# 應用程式走 Transaction pooler（6543）以支撐併發，但 DDL 走 Session pooler（5432）
# 比較穩定；ALEMBIC_DATABASE_URL 沒設定時退回 DATABASE_URL。
config.set_main_option(
    "sqlalchemy.url", settings.alembic_database_url or settings.database_url
)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # 外部（scripts/build_test_schema.py）可透過 config.attributes 傳入現成連線，
    # 讓 migration 跑在該連線的 search_path（測試 schema）上；
    # 正常 CLI 流程不設 attributes，行為與原本完全相同。
    connection = config.attributes.get("connection")
    if connection is not None:
        # version_table_schema 必須明確指定：建置測試 schema 時 search_path 內
        # 含 public（供 extension 解析），若讓 alembic 用未限定名稱找版本表，
        # 會誤中 public.alembic_version 而以為已在 head。
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=config.attributes.get("version_table_schema"),
        )
        with context.begin_transaction():
            context.run_migrations()
        return

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
