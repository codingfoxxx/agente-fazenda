import os
from datetime import datetime

from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL não definida")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

app = FastAPI(title="Agente Fazenda Backend")


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


class LogInput(BaseModel):
    data_hora: str
    usuario: str | None = None
    acao: str
    fazenda_origem: str | None = None
    fazenda_destino: str | None = None
    categoria: str | None = None
    qtd: float | None = None
    piq_origem: str | None = None
    piq_destino: str | None = None
    obs: str | None = None
    status_sync: str | None = None
    id_comando_backend: str | None = None
    hash_evento: str


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


@app.get("/")
def root():
    return {"ok": True, "service": "agente-fazenda-backend"}


@app.get("/health")
def health():
    return {"ok": True, "timestamp": datetime.utcnow().isoformat()}


@app.post("/logs/importar")
def importar_log(item: LogInput):
    db = SessionLocal()
    try:
        existente = db.query(Movimentacao).filter_by(hash_evento=item.hash_evento).first()
        if existente:
            return {"status": "duplicado", "id": existente.id}

        dt = datetime.strptime(item.data_hora, "%Y-%m-%d %H:%M:%S")

        log = Movimentacao(
            data_hora=dt,
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

        return {"status": "ok", "id": log.id}
    finally:
        db.close()


@app.get("/logs")
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