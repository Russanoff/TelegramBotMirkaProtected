from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column


from app.db.base import Base


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    amount: Mapped[int]
    days: Mapped[int]
    currency: Mapped[str] = mapped_column(String(10))
    provider: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20))
    payment_id: Mapped[str] = mapped_column(String(60))
    create_payment: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow())