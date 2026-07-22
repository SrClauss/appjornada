from contextlib import asynccontextmanager
import logging
import time
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.db.database import connect_db, close_db
from app.routers import auth, users, veiculos, jornadas, gps, manutencoes, metas, uploads, relatorios, coleta, precos_particulares, config_sistema
from app.services.scheduler import criar_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("app.timing")

UPLOAD_DIR = Path("/tmp/app_jornada_uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    scheduler = criar_scheduler()
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)
    await close_db()


app = FastAPI(
    title="App Jornada API",
    description="Sistema de controle de jornada para motoristas CLT em apps de corrida.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def log_request_timing(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    level = logging.WARNING if elapsed_ms > 500 else logging.INFO
    logger.log(
        level,
        "%s %s → %d  (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    response.headers["X-Response-Time"] = f"{elapsed_ms:.1f}ms"
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth)
app.include_router(users)
app.include_router(veiculos)
app.include_router(jornadas)
app.include_router(gps)
app.include_router(manutencoes)
app.include_router(metas)
app.include_router(uploads)
app.include_router(relatorios)
app.include_router(coleta)
app.include_router(precos_particulares)
app.include_router(config_sistema.router)

# Serve arquivos de upload via /static/uploads/
app.mount("/static/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


@app.get("/", tags=["health"])
async def health():
    return {"status": "ok", "app": "App Jornada API"}
