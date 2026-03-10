from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import TypeAdapter, ValidationError
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import get_db
from ..schemas import (
    HashStatusQuery,
    HashStatusResponse,
    ImportLogsResponse,
    LogEventIn,
)
from ..services.log_importer import consultar_status_hashes, importar_eventos
from .security import require_worker_key


router = APIRouter(
    prefix="/logs",
    tags=["logs"],
    dependencies=[Depends(require_worker_key)],
)

_events_adapter = TypeAdapter(list[LogEventIn])


def _parse_eventos(payload: Any) -> list[LogEventIn]:
    if isinstance(payload, dict) and "eventos" in payload:
        raw = payload["eventos"]
    elif isinstance(payload, list):
        raw = payload
    elif isinstance(payload, dict):
        raw = [payload]
    else:
        raise ValueError("Payload invalido para importacao de logs.")

    return _events_adapter.validate_python(raw)


@router.post("/importar", response_model=ImportLogsResponse)
def importar_logs(
    payload: Any = Body(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ImportLogsResponse:
    try:
        eventos = _parse_eventos(payload)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    if len(eventos) > settings.import_batch_limit:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"Limite de lote excedido. Limite={settings.import_batch_limit} "
                f"Recebidos={len(eventos)}"
            ),
        )

    return importar_eventos(db, eventos)


@router.post("/status", response_model=HashStatusResponse)
def consultar_status(
    payload: HashStatusQuery,
    db: Session = Depends(get_db),
) -> HashStatusResponse:
    return consultar_status_hashes(db, payload.hashes)
