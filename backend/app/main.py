from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.routes_estoque import router as estoque_router
from .api.routes_logs import router as logs_router
from .api.routes_consulta import router as consulta_router
from .api.routes_comandos import router as comandos_router
from .config import get_settings
from .db import init_db

app.include_router(estoque_router)

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
)

if settings.cors_origins == "*":
    origins = ["*"]
else:
    origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(logs_router)
app.include_router(consulta_router)
app.include_router(comandos_router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
    }

def init_db() -> None:
    from . import models  # noqa: F401
    from . import models_comandos  # noqa: F401
    from . import models_estoque  # noqa: F401
    Base.metadata.create_all(bind=engine)
