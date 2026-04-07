"""
main.py — Punto de entrada de FinKaan Backend
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from .config import settings

from .database import engine, Base
from .redis_client import ping as redis_ping
from .routers import auth, users, scenarios, analysis


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Crear tablas si no existen (en producción usar Alembic)
    Base.metadata.create_all(bind=engine)

    if redis_ping():
        print("✅  Redis conectado.")
    else:
        print("⚠️   Redis no disponible — blacklist de tokens desactivada.")

    yield


# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="FinKaan API",
    description="Backend para la app de educación financiera FinKaan",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# CORS — en producción reemplazar "*" por el dominio real
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(scenarios.router)
app.include_router(analysis.router)


# ─── Health check ─────────────────────────────────────────────────────────────

@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "redis": redis_ping()}
