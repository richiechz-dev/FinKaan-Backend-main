"""
security.py — Utilidades de seguridad: hashing de contraseñas y JWT.

Separado de routers/auth.py para evitar confusión de nombres y responsabilidades:
- Este módulo: lógica pura de seguridad (no sabe de rutas HTTP).
- routers/auth.py: endpoints HTTP de autenticación.
"""
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .redis_client import redis_client
from . import models

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
_bearer = HTTPBearer()

CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Credenciales inválidas o sesión expirada.",
    headers={"WWW-Authenticate": "Bearer"},
)


# ─── Contraseñas ──────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


# ─── JWT ──────────────────────────────────────────────────────────────────────

def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _decode_token(token: str) -> int:
    """Decodifica el JWT y retorna el user_id. Lanza 401 si falla."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            raise CREDENTIALS_EXC
        return int(sub)
    except JWTError:
        raise CREDENTIALS_EXC


# ─── Dependency ───────────────────────────────────────────────────────────────

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> models.User:
    token = credentials.credentials

    # Verificar que el token no esté en la blacklist de Redis
    if redis_client.exists(f"bl:{token}"):
        raise CREDENTIALS_EXC

    user_id = _decode_token(token)
    user = db.get(models.User, user_id)
    if user is None:
        raise CREDENTIALS_EXC
    return user
