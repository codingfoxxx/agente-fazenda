from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    data_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    usuario: Mapped[str] = mapped_column(String(128), nullable=False)
    acao: Mapped[str] = mapped_column(String(255), nullable=False)

    fazenda_origem: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fazenda_destino: Mapped[str | None] = mapped_column(String(255), nullable=True)
    categoria: Mapped[str | None] = mapped_column(String(128), nullable=True)
    qtd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    piq_origem: Mapped[str | None] = mapped_column(String(128), nullable=True)
    piq_destino: Mapped[str | None] = mapped_column(String(128), nullable=True)
    obs: Mapped[str | None] = mapped_column(Text, nullable=True)

    status_sync: Mapped[str | None] = mapped_column(String(64), nullable=True)
    id_comando_backend: Mapped[str | None] = mapped_column(String(128), nullable=True)

    hash_evento: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
        index=True,
    )

    origem: Mapped[str] = mapped_column(String(64), nullable=False, default="excel")
    linha_excel: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_linha: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
