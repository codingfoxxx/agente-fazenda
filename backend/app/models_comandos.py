from datetime import datetime
from sqlalchemy import DateTime, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base


class ComandoPendente(Base):
    __tablename__ = "comandos_pendentes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    tipo: Mapped[str] = mapped_column(String(64), nullable=False)
    # EDITAR_QUANTIDADE, TRANSFERIR_PIQUETE, TRANSFERIR_FAZENDA, AVANCAR_CATEGORIA, VOLTAR_CATEGORIA

    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    # Dados específicos do comando — varia por tipo

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pendente")
    # pendente, executando, concluido, erro

    origem: Mapped[str] = mapped_column(String(64), nullable=False, default="bot")
    # quem criou: bot, manual, etc

    mensagem_original: Mapped[str | None] = mapped_column(Text, nullable=True)
    # texto original que o pai mandou no Telegram

    erro_detalhe: Mapped[str | None] = mapped_column(Text, nullable=True)
    # detalhes do erro se falhou

    tentativas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
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
    executed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
