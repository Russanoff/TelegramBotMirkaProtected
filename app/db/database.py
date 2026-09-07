from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models.user import User
from app.db.models.payment import Payment
from app.db.models.vpn_clients import Subscription

DATABASE_URL = "sqlite+aiosqlite:///./database.db"

engine = create_async_engine(DATABASE_URL, echo=True)

AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


def _add_missing_columns(sync_conn):
    # create_all() не добавляет колонки в уже существующие таблицы,
    # поэтому новые поля на уже развёрнутой БД нужно доливать вручную.
    inspector = inspect(sync_conn)
    if "users" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("users")}
    if "referrer_id" not in existing:
        sync_conn.execute(text("ALTER TABLE users ADD COLUMN referrer_id INTEGER"))
    if "referral_bonus_granted" not in existing:
        sync_conn.execute(text("ALTER TABLE users ADD COLUMN referral_bonus_granted BOOLEAN DEFAULT 0"))


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_add_missing_columns)