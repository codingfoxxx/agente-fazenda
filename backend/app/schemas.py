from datetime import datetime, timezone
from typing import Any, Literal
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class LogEventIn(BaseModel):
    data_hora: datetime
    usuario: str = Field(min_length=1, max_length=128)
    acao: str = Field(min_length=1, max_length=255)

    fazenda_origem: str | None = None
    fazenda_destino: str | None = None
    categoria: str | None = None
    qtd: Optional[int] = None
    piq_origem: str | None = None
    piq_destino: str | None = None
    obs: str | None = None

    status_sync: str | None = None
    id_comando_backend: str | None = None

    hash_evento: str = Field(min_length=16, max_length=128)
    origem: str = Field(default="excel", max_length=64)

    linha_excel: int | None = Field(default=None, ge=1)
    raw_linha: dict[str, Any] | None = None

    @field_validator("data_hora", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @field_validator(
        "usuario", "acao", "fazenda_origem", "fazenda_destino", "categoria",
        "piq_origem", "piq_destino", "obs", "status_sync", "id_comando_backend",
        "hash_evento", "origem",
        mode="before",
    )
    @classmethod
    def normalize_text(cls, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            text = value.strip()
            return text or None
        return value


class ImportItemResult(BaseModel):
    hash_evento: str
    status: Literal["inserido", "duplicado", "erro"]
    id_log: int | None = None
    detalhe: str | None = None


class ImportLogsResponse(BaseModel):
    recebidos: int
    inseridos: int
    duplicados: int
    erros: int
    resultados: list[ImportItemResult]


class HashStatusQuery(BaseModel):
    hashes: list[str] = Field(min_length=1, max_length=2000)

    @field_validator("hashes")
    @classmethod
    def normalize_hashes(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values if value and value.strip()]
        if not cleaned:
            raise ValueError("Lista de hashes vazia.")
        return cleaned


class HashStatusItem(BaseModel):
    hash_evento: str
    sincronizado: bool
    id_log: int | None = None
    received_at: datetime | None = None


class HashStatusResponse(BaseModel):
    total: int
    encontrados: int
    itens: list[HashStatusItem]
