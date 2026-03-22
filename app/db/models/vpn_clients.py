from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    client_id: Mapped[str] = mapped_column(String(260), default=False)
    server_name: Mapped[str] = mapped_column(String(10))
    sub_id: Mapped[str] = mapped_column(String(20))
    sub_link: Mapped[str] = mapped_column(String(50))
    starts_at: Mapped[datetime]
    is_trial: Mapped[bool] = mapped_column(default=False)
    is_active: Mapped[bool] = mapped_column(default=True)