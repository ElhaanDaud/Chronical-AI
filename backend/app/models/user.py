from datetime import datetime

from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTableUUID
from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.cluster import Base


class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "users"

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
