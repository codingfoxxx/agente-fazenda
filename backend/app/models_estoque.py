from datetime import datetime
from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base


class EstoqueAtual(Base):
    __tablename__ = "estoque_atual"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fazenda: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    piquete: Mapped[str] = mapped_column(String(200), nullable=False)
    categoria: Mapped[str] = mapped_column(String(100), nullable=False)
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
