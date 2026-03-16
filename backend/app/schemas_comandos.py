from datetime import datetime
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class CriarComandoRequest(BaseModel):
    tipo: Literal[
        "EDITAR_QUANTIDADE",
        "ADICIONAR_QUANTIDADE",
        "TRANSFERIR_PIQUETE",
        "TRANSFERIR_FAZENDA",
        "AVANCAR_CATEGORIA",
        "VOLTAR_CATEGORIA",
        "EXECUTAR_AGORA",
    
    ]
    payload: dict[str, Any]
    mensagem_original: Optional[str] = None
    origem: str = "bot"


class ConfirmarComandoRequest(BaseModel):
    sucesso: bool
    erro_detalhe: Optional[str] = None


class ComandoResponse(BaseModel):
    id: int
    tipo: str
    payload: dict[str, Any]
    status: str
    origem: str
    mensagem_original: Optional[str]
    erro_detalhe: Optional[str]
    tentativas: int
    created_at: datetime
    updated_at: datetime
    executed_at: Optional[datetime]


class ListaComandosResponse(BaseModel):
    total: int
    comandos: list[ComandoResponse]
