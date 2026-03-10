from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..models import AuditLog
from ..schemas import (
    HashStatusItem,
    HashStatusResponse,
    ImportItemResult,
    ImportLogsResponse,
    LogEventIn,
)


def importar_eventos(db: Session, eventos: list[LogEventIn]) -> ImportLogsResponse:
    resultados: list[ImportItemResult] = []
    inseridos = 0
    duplicados = 0
    erros = 0

    for evento in eventos:
        row_data = {
            "data_hora": evento.data_hora,
            "usuario": evento.usuario,
            "acao": evento.acao,
            "fazenda_origem": evento.fazenda_origem,
            "fazenda_destino": evento.fazenda_destino,
            "categoria": evento.categoria,
            "qtd": evento.qtd,
            "piq_origem": evento.piq_origem,
            "piq_destino": evento.piq_destino,
            "obs": evento.obs,
            "status_sync": evento.status_sync,
            "id_comando_backend": evento.id_comando_backend,
            "hash_evento": evento.hash_evento,
            "origem": evento.origem,
            "linha_excel": evento.linha_excel,
            "raw_linha": evento.raw_linha,
        }

        try:
            insert_stmt = (
                insert(AuditLog)
                .values(**row_data)
                .on_conflict_do_nothing(index_elements=[AuditLog.hash_evento])
                .returning(AuditLog.id)
            )
            inserted_id = db.execute(insert_stmt).scalar_one_or_none()

            if inserted_id is not None:
                db.commit()
                inseridos += 1
                resultados.append(
                    ImportItemResult(
                        hash_evento=evento.hash_evento,
                        status="inserido",
                        id_log=inserted_id,
                    )
                )
                continue

            existing_id = db.execute(
                select(AuditLog.id).where(AuditLog.hash_evento == evento.hash_evento)
            ).scalar_one_or_none()
            db.commit()

            duplicados += 1
            resultados.append(
                ImportItemResult(
                    hash_evento=evento.hash_evento,
                    status="duplicado",
                    id_log=existing_id,
                )
            )
        except SQLAlchemyError as exc:
            db.rollback()
            erros += 1
            resultados.append(
                ImportItemResult(
                    hash_evento=evento.hash_evento,
                    status="erro",
                    detalhe=str(exc.__class__.__name__),
                )
            )

    return ImportLogsResponse(
        recebidos=len(eventos),
        inseridos=inseridos,
        duplicados=duplicados,
        erros=erros,
        resultados=resultados,
    )


def consultar_status_hashes(db: Session, hashes: list[str]) -> HashStatusResponse:
    unique_hashes = list(dict.fromkeys(hashes))

    rows = db.execute(
        select(AuditLog.hash_evento, AuditLog.id, AuditLog.received_at).where(
            AuditLog.hash_evento.in_(unique_hashes)
        )
    ).all()

    indexed = {
        row.hash_evento: HashStatusItem(
            hash_evento=row.hash_evento,
            sincronizado=True,
            id_log=row.id,
            received_at=row.received_at,
        )
        for row in rows
    }

    itens: list[HashStatusItem] = []
    for hash_evento in unique_hashes:
        itens.append(
            indexed.get(
                hash_evento,
                HashStatusItem(hash_evento=hash_evento, sincronizado=False),
            )
        )

    return HashStatusResponse(
        total=len(unique_hashes),
        encontrados=len(rows),
        itens=itens,
    )
