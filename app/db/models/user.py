from datetime import datetime, timedelta
from sqlalchemy import BigInteger, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    accepted_terms: Mapped[bool] = mapped_column(Boolean, default=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    trial_used: Mapped[bool] = mapped_column(Boolean, default=False)
    create_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow())
