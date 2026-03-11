from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..db import get_db
from ..models_comandos import ComandoPendente
from ..schemas_comandos import (
    CriarComandoRequest,
    ConfirmarComandoRequest,
    ComandoResponse,
    ListaComandosResponse,
)
from .security import require_worker_key
from datetime import datetime, timezone

router = APIRouter(
    prefix="/comandos",
    tags=["comandos"],
    dependencies=[Depends(require_worker_key)],
)


def _to_response(c: ComandoPendente) -> ComandoResponse:
    return ComandoResponse(
        id=c.id,
        tipo=c.tipo,
        payload=c.payload,
        status=c.status,
        origem=c.origem,
        mensagem_original=c.mensagem_original,
        erro_detalhe=c.erro_detalhe,
        tentativas=c.tentativas,
        created_at=c.created_at,
        updated_at=c.updated_at,
        executed_at=c.executed_at,
    )


@router.post("/criar", response_model=ComandoResponse)
def criar_comando(body: CriarComandoRequest, db: Session = Depends(get_db)):
    """
    Bot envia um comando para ser executado na planilha.
    Ex: {"tipo": "EDITAR_QUANTIDADE", "payload": {"fazenda": "LIMÃO", "piquete": "Cava de Vinhaça 1", "categoria": "BOI", "quantidade": 15}}
    """
    cmd = ComandoPendente(
        tipo=body.tipo,
        payload=body.payload,
        status="pendente",
        origem=body.origem,
        mensagem_original=body.mensagem_original,
    )
    db.add(cmd)
    db.commit()
    db.refresh(cmd)
    return _to_response(cmd)


@router.get("/pendentes", response_model=ListaComandosResponse)
def listar_pendentes(db: Session = Depends(get_db)):
    """
    Worker puxa os comandos pendentes para executar.
    """
    rows = (
        db.query(ComandoPendente)
        .filter(ComandoPendente.status == "pendente")
        .order_by(ComandoPendente.created_at.asc())
        .all()
    )
    return ListaComandosResponse(total=len(rows), comandos=[_to_response(r) for r in rows])


@router.post("/{comando_id}/confirmar", response_model=ComandoResponse)
def confirmar_comando(
    comando_id: int,
    body: ConfirmarComandoRequest,
    db: Session = Depends(get_db),
):
    """
    Worker confirma se o comando foi executado com sucesso ou falhou.
    """
    cmd = db.get(ComandoPendente, comando_id)
    if not cmd:
        raise HTTPException(status_code=404, detail="Comando não encontrado")

    if body.sucesso:
        cmd.status = "concluido"
        cmd.executed_at = datetime.now(timezone.utc)
        cmd.erro_detalhe = None
    else:
        cmd.status = "erro"
        cmd.erro_detalhe = body.erro_detalhe
        cmd.tentativas += 1

    db.commit()
    db.refresh(cmd)
    return _to_response(cmd)


@router.get("/historico", response_model=ListaComandosResponse)
def historico_comandos(limit: int = 50, db: Session = Depends(get_db)):
    """
    Retorna histórico de comandos executados.
    """
    rows = (
        db.query(ComandoPendente)
        .order_by(ComandoPendente.created_at.desc())
        .limit(limit)
        .all()
    )
    return ListaComandosResponse(total=len(rows), comandos=[_to_response(r) for r in rows])
