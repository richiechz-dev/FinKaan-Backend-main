"""
redis_client.py — Cliente Redis para FinKaan
Uso principal: blacklist de tokens JWT tras logout.
"""
import redis

from .config import settings

redis_client: redis.Redis = redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=3,
    socket_timeout=3,
)


def blacklist_token(token: str, expires_in_seconds: int) -> None:
    """Agrega el token a la blacklist con TTL igual al tiempo restante del JWT."""
    redis_client.setex(f"bl:{token}", expires_in_seconds, "1")


def ping() -> bool:
    """Verifica la conexión a Redis. Retorna True si está disponible."""
    try:
        return redis_client.ping()
    except Exception:
        return False
