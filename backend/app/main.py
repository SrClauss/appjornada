from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.db.database import connect_db, close_db
from app.routers import auth, users, veiculos, jornadas, gps, manutencoes, metas, relatorios, uploads
from app.services.scheduler import criar_scheduler

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
app.include_router(relatorios)
app.include_router(uploads)

# Serve arquivos de upload via /static/uploads/
app.mount("/static/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


@app.get("/", tags=["health"])
async def health():
    return {"status": "ok", "app": "App Jornada API"}
