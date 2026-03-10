import os
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Text
from sqlalchemy.orm import declarative_base, sessionmaker

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL")
WORKER_API_KEY = os.getenv("WORKER_API_KEY", "")  # deixe vazio para desativar auth
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL não definida")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

app = FastAPI(title="Agente Fazenda API")

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

api_key_header = APIKeyHeader(name="X-Worker-Key", auto_error=False)


def verify_key(key: Optional[str] = Security(api_key_header)):
    """Valida X-Worker-Key. Se WORKER_API_KEY não estiver configurada, libera tudo."""
    if WORKER_API_KEY and key != WORKER_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

class Movimentacao(Base):
    __tablename__ = "movimentacoes"

    id = Column(Integer, primary_key=True, index=True)
    data_hora = Column(DateTime, nullable=False)
    usuario = Column(String(100), nullable=True)
    acao = Column(String(100), nullable=False)
    fazenda_origem = Column(String(100), nullable=True)
    fazenda_destino = Column(String(100), nullable=True)
    categoria = Column(String(100), nullable=True)
    qtd = Column(Float, nullable=True)
    piq_origem = Column(String(100), nullable=True)
    piq_destino = Column(String(100), nullable=True)
    obs = Column(Text, nullable=True)
    status_sync = Column(String(50), nullable=True)
    id_comando_backend = Column(String(100), nullable=True)
    hash_evento = Column(String(255), unique=True, nullable=False)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class LogInput(BaseModel):
    data_hora: str
    usuario: Optional[str] = None
    acao: str
    fazenda_origem: Optional[str] = None
    fazenda_destino: Optional[str] = None
    categoria: Optional[str] = None
    qtd: Optional[float] = None
    piq_origem: Optional[str] = None
    piq_destino: Optional[str] = None
    obs: Optional[str] = None
    status_sync: Optional[str] = None
    id_comando_backend: Optional[str] = None
    hash_evento: str


class ImportarPayload(BaseModel):
    eventos: list[LogInput]


class StatusPayload(BaseModel):
    hashes: list[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_datetime(value: str) -> datetime:
    """Aceita tanto '2026-03-10T12:00:00' quanto '2026-03-10 12:00:00'."""
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Formato de data inválido: {value}")


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------------------------
# Endpoints públicos
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    return {"ok": True, "service": "agente-fazenda-backend"}


@app.get("/healthz")
def healthz():
    """Health check — formato esperado pelo guia de testes."""
    return {
        "status": "ok",
        "app": "Agente Fazenda API",
        "environment": ENVIRONMENT,
    }


# Mantém /health para compatibilidade com EasyPanel
@app.get("/health")
def health():
    return {"status": "ok", "app": "Agente Fazenda API", "environment": ENVIRONMENT}


# ---------------------------------------------------------------------------
# Endpoints protegidos
# ---------------------------------------------------------------------------

@app.post("/logs/importar", dependencies=[Depends(verify_key)])
def importar_logs(payload: ImportarPayload):
    """
    Recebe um array de eventos e insere os novos, ignorando duplicados pelo hash_evento.
    Retorna contagens: inseridos, duplicados, erros.
    """
    db = SessionLocal()
    inseridos = 0
    duplicados = 0
    erros = []

    try:
        for item in payload.eventos:
            try:
                existente = db.query(Movimentacao).filter_by(hash_evento=item.hash_evento).first()
                if existente:
                    duplicados += 1
                    continue

                log = Movimentacao(
                    data_hora=parse_datetime(item.data_hora),
                    usuario=item.usuario,
                    acao=item.acao,
                    fazenda_origem=item.fazenda_origem,
                    fazenda_destino=item.fazenda_destino,
                    categoria=item.categoria,
                    qtd=item.qtd,
                    piq_origem=item.piq_origem,
                    piq_destino=item.piq_destino,
                    obs=item.obs,
                    status_sync=item.status_sync,
                    id_comando_backend=item.id_comando_backend,
                    hash_evento=item.hash_evento,
                )
                db.add(log)
                db.commit()
                db.refresh(log)
                inseridos += 1

            except Exception as e:
                db.rollback()
                erros.append({"hash_evento": item.hash_evento, "erro": str(e)})

        return {
            "inseridos": inseridos,
            "duplicados": duplicados,
            "erros": erros,
        }
    finally:
        db.close()


@app.post("/logs/status", dependencies=[Depends(verify_key)])
def status_hashes(payload: StatusPayload):
    """
    Recebe uma lista de hashes e retorna quais existem no banco.
    Usado pelo worker para confirmar sincronização.
    """
    db = SessionLocal()
    try:
        encontrados = (
            db.query(Movimentacao.hash_evento)
            .filter(Movimentacao.hash_evento.in_(payload.hashes))
            .all()
        )
        hashes_encontrados = {row.hash_evento for row in encontrados}

        result = {h: h in hashes_encontrados for h in payload.hashes}
        todos_sincronizados = all(result.values())

        return {
            "sincronizado": todos_sincronizados,
            "detalhes": result,
        }
    finally:
        db.close()


@app.get("/logs", dependencies=[Depends(verify_key)])
def listar_logs(limit: int = 50):
    db = SessionLocal()
    try:
        items = db.query(Movimentacao).order_by(Movimentacao.id.desc()).limit(limit).all()
        return [
            {
                "id": x.id,
                "data_hora": x.data_hora.isoformat(),
                "usuario": x.usuario,
                "acao": x.acao,
                "fazenda_origem": x.fazenda_origem,
                "fazenda_destino": x.fazenda_destino,
                "categoria": x.categoria,
                "qtd": x.qtd,
                "piq_origem": x.piq_origem,
                "piq_destino": x.piq_destino,
                "obs": x.obs,
                "status_sync": x.status_sync,
                "id_comando_backend": x.id_comando_backend,
                "hash_evento": x.hash_evento,
            }
            for x in items
        ]
    finally:
        db.close()
