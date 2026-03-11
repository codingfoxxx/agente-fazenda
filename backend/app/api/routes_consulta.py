from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import AuditLog
from .security import require_worker_key

router = APIRouter(
    prefix="/consulta",
    tags=["consulta"],
    dependencies=[Depends(require_worker_key)],
)

# Acoes que representam movimentacao interna (nao alteram estoque total da fazenda)
ACOES_INTERNAS = {"TRANSFERIR_PIQUETE", "MOVER_CATEGORIA", "AVANCAR_CATEGORIA", "VOLTAR_CATEGORIA"}


# ---------------------------------------------------------------------------
# GET /consulta/resumo
# Retorna total de animais por fazenda e categoria
# ---------------------------------------------------------------------------

@router.get("/resumo")
def resumo_fazendas(db: Session = Depends(get_db)):
    """
    Retorna o estoque total atual por fazenda e categoria.
    Calculado somando qtd de todos os eventos (exceto movimentacoes internas).
    """
    rows = (
        db.query(
            AuditLog.fazenda_origem.label("fazenda"),
            AuditLog.categoria,
            func.sum(AuditLog.qtd).label("total"),
            func.max(AuditLog.data_hora).label("ultima_movimentacao"),
        )
        .filter(AuditLog.fazenda_origem.isnot(None))
        .filter(AuditLog.categoria.isnot(None))
        .filter(AuditLog.acao.notin_(ACOES_INTERNAS))
        .group_by(AuditLog.fazenda_origem, AuditLog.categoria)
        .order_by(AuditLog.fazenda_origem, AuditLog.categoria)
        .all()
    )

    # Agrupa por fazenda
    fazendas: dict = {}
    for row in rows:
        fazenda = row.fazenda
        if fazenda not in fazendas:
            fazendas[fazenda] = {
                "fazenda": fazenda,
                "categorias": [],
                "total_geral": 0,
                "ultima_movimentacao": None,
            }

        total = int(row.total or 0)
        ultima = row.ultima_movimentacao

        fazendas[fazenda]["categorias"].append({
            "categoria": row.categoria,
            "total": total,
            "ultima_movimentacao": ultima.isoformat() if ultima else None,
        })
        fazendas[fazenda]["total_geral"] += total

        if ultima and (
            fazendas[fazenda]["ultima_movimentacao"] is None
            or ultima > datetime.fromisoformat(fazendas[fazenda]["ultima_movimentacao"])
        ):
            fazendas[fazenda]["ultima_movimentacao"] = ultima.isoformat()

    return {
        "fazendas": list(fazendas.values()),
        "total_fazendas": len(fazendas),
    }


# ---------------------------------------------------------------------------
# GET /consulta/movimentacoes
# Retorna ultimas N movimentacoes com filtros opcionais
# ---------------------------------------------------------------------------

@router.get("/movimentacoes")
def listar_movimentacoes(
    fazenda: Optional[str] = Query(default=None, description="Filtrar por fazenda"),
    categoria: Optional[str] = Query(default=None, description="Filtrar por categoria (BOI, VACA...)"),
    acao: Optional[str] = Query(default=None, description="Filtrar por acao (EDICAO_MANUAL, TRANSFERIR_FAZENDA...)"),
    data_inicio: Optional[str] = Query(default=None, description="Data inicio (YYYY-MM-DD)"),
    data_fim: Optional[str] = Query(default=None, description="Data fim (YYYY-MM-DD)"),
    limit: int = Query(default=50, le=500, description="Quantidade de registros"),
    db: Session = Depends(get_db),
):
    """
    Retorna movimentacoes com filtros opcionais.
    Util para o bot responder: 'o que aconteceu essa semana?'
    """
    query = db.query(AuditLog)

    if fazenda:
        query = query.filter(
            (AuditLog.fazenda_origem.ilike(f"%{fazenda}%")) |
            (AuditLog.fazenda_destino.ilike(f"%{fazenda}%"))
        )
    if categoria:
        query = query.filter(AuditLog.categoria.ilike(f"%{categoria}%"))
    if acao:
        query = query.filter(AuditLog.acao.ilike(f"%{acao}%"))
    if data_inicio:
        try:
            dt_inicio = datetime.strptime(data_inicio, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            query = query.filter(AuditLog.data_hora >= dt_inicio)
        except ValueError:
            pass
    if data_fim:
        try:
            dt_fim = datetime.strptime(data_fim, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            query = query.filter(AuditLog.data_hora <= dt_fim)
        except ValueError:
            pass

    rows = query.order_by(AuditLog.data_hora.desc()).limit(limit).all()

    return {
        "total": len(rows),
        "movimentacoes": [
            {
                "id": r.id,
                "data_hora": r.data_hora.isoformat(),
                "usuario": r.usuario,
                "acao": r.acao,
                "fazenda_origem": r.fazenda_origem,
                "fazenda_destino": r.fazenda_destino,
                "categoria": r.categoria,
                "qtd": r.qtd,
                "piq_origem": r.piq_origem,
                "piq_destino": r.piq_destino,
                "obs": r.obs,
            }
            for r in rows
        ],
    }


# ---------------------------------------------------------------------------
# GET /consulta/estoque
# Retorna estoque atual por fazenda, piquete e categoria
# ---------------------------------------------------------------------------

@router.get("/estoque")
def estoque_atual(
    fazenda: Optional[str] = Query(default=None, description="Filtrar por fazenda"),
    categoria: Optional[str] = Query(default=None, description="Filtrar por categoria"),
    piquete: Optional[str] = Query(default=None, description="Filtrar por piquete"),
    db: Session = Depends(get_db),
):
    """
    Retorna estoque atual por fazenda/piquete/categoria.
    Util para o bot responder: 'quantos animais no piquete 3 da Fazenda Norte?'
    """
    query = (
        db.query(
            AuditLog.fazenda_origem.label("fazenda"),
            AuditLog.piq_origem.label("piquete"),
            AuditLog.categoria,
            func.sum(AuditLog.qtd).label("total"),
        )
        .filter(AuditLog.fazenda_origem.isnot(None))
        .filter(AuditLog.piq_origem.isnot(None))
        .filter(AuditLog.categoria.isnot(None))
        .filter(AuditLog.acao.notin_(ACOES_INTERNAS))
        .group_by(AuditLog.fazenda_origem, AuditLog.piq_origem, AuditLog.categoria)
    )

    if fazenda:
        query = query.filter(AuditLog.fazenda_origem.ilike(f"%{fazenda}%"))
    if categoria:
        query = query.filter(AuditLog.categoria.ilike(f"%{categoria}%"))
    if piquete:
        query = query.filter(AuditLog.piq_origem.ilike(f"%{piquete}%"))

    rows = query.order_by(AuditLog.fazenda_origem, AuditLog.piq_origem, AuditLog.categoria).all()

    # Agrupa por fazenda > piquete > categoria
    fazendas: dict = {}
    for row in rows:
        faz = row.fazenda
        piq = row.piquete
        total = int(row.total or 0)

        if faz not in fazendas:
            fazendas[faz] = {"fazenda": faz, "piquetes": {}}
        if piq not in fazendas[faz]["piquetes"]:
            fazendas[faz]["piquetes"][piq] = {"piquete": piq, "categorias": [], "total": 0}

        fazendas[faz]["piquetes"][piq]["categorias"].append({
            "categoria": row.categoria,
            "total": total,
        })
        fazendas[faz]["piquetes"][piq]["total"] += total

    # Converte piquetes de dict para list
    result = []
    for faz_data in fazendas.values():
        result.append({
            "fazenda": faz_data["fazenda"],
            "piquetes": list(faz_data["piquetes"].values()),
        })

    return {"estoque": result}


# ---------------------------------------------------------------------------
# GET /sync/status
# Retorna status de sincronizacao
# ---------------------------------------------------------------------------

@router.get("/sync/status", dependencies=[Depends(require_worker_key)])
def sync_status(db: Session = Depends(get_db)):
    """
    Retorna status geral de sincronizacao.
    Util para o bot responder: 'esta tudo em dia?'
    """
    total = db.query(func.count(AuditLog.id)).scalar() or 0

    ultimo = (
        db.query(AuditLog.data_hora, AuditLog.received_at)
        .order_by(AuditLog.received_at.desc())
        .first()
    )

    return {
        "total_eventos": total,
        "ultimo_evento_data_hora": ultimo.data_hora.isoformat() if ultimo else None,
        "ultimo_evento_recebido_em": ultimo.received_at.isoformat() if ultimo else None,
        "status": "ok" if total > 0 else "sem_dados",
    }
