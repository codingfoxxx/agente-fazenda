from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import delete
from typing import Any

from ..db import get_db
from ..models_estoque import EstoqueAtual
from .security import require_worker_key

router = APIRouter(
    prefix="/estoque",
    tags=["estoque"],
    dependencies=[Depends(require_worker_key)],
)


@router.post("/snapshot")
def salvar_snapshot(body: dict[str, Any], db: Session = Depends(get_db)):
    """
    Worker envia snapshot completo da planilha.
    Substitui todos os dados da fazenda enviada.
    """
    fazenda = body.get("fazenda")
    piquetes = body.get("piquetes", [])

    # Deleta estoque atual da fazenda
    db.execute(delete(EstoqueAtual).where(EstoqueAtual.fazenda == fazenda))

    # Insere dados novos
    for piquete_data in piquetes:
        piquete = piquete_data.get("piquete")
        for cat_data in piquete_data.get("categorias", []):
            db.add(EstoqueAtual(
                fazenda=fazenda,
                piquete=piquete,
                categoria=cat_data["categoria"],
                quantidade=cat_data["quantidade"],
            ))

    db.commit()
    return {"status": "ok", "fazenda": fazenda, "piquetes": len(piquetes)}


@router.get("/fazenda/{fazenda}")
def get_estoque_fazenda(fazenda: str, db: Session = Depends(get_db)):
    """Retorna estoque atual de uma fazenda."""
    rows = (
        db.query(EstoqueAtual)
        .filter(EstoqueAtual.fazenda == fazenda.upper())
        .filter(EstoqueAtual.quantidade > 0)
        .order_by(EstoqueAtual.piquete, EstoqueAtual.categoria)
        .all()
    )

    # Agrupa por piquete
    piquetes = {}
    for row in rows:
        if row.piquete not in piquetes:
            piquetes[row.piquete] = []
        piquetes[row.piquete].append({
            "categoria": row.categoria,
            "quantidade": row.quantidade
        })

    return {
        "fazenda": fazenda.upper(),
        "piquetes": [
            {"piquete": p, "categorias": cats}
            for p, cats in piquetes.items()
        ]
    }


@router.get("/resumo")
def get_resumo(db: Session = Depends(get_db)):
    """Retorna total de animais por fazenda."""
    from sqlalchemy import func as sqlfunc
    rows = (
        db.query(EstoqueAtual.fazenda, sqlfunc.sum(EstoqueAtual.quantidade).label("total"))
        .group_by(EstoqueAtual.fazenda)
        .order_by(EstoqueAtual.fazenda)
        .all()
    )
    return {
        "fazendas": [{"fazenda": r.fazenda, "total": r.total} for r in rows]
    }
