from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

"""
連線走 Supabase Transaction pooler（port 6543）。

兩個必要設定：
1. prepare_threshold=None —— transaction mode 每次交易可能落在不同的後端連線上，
   psycopg3 預設會自動把重複執行的語句轉成 prepared statement，在這種模式下會
   出現「prepared statement 已存在／不存在」的錯誤，必須整個關掉。
2. 連線池仍然保留（省下建立連線的往返），但不需要開大：transaction mode 下
   連線是共用的，真正的併發上限由 Supabase 端決定，不是這裡的 pool_size。
"""
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,
    connect_args={"prepare_threshold": None},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
