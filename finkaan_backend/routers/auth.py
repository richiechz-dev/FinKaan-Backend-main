"""
routers/auth.py — Endpoints de autenticación.

Cada endpoint delega la lógica de negocio al módulo services/auth_service.py,
conservando aquí solo el manejo HTTP (request/response, códigos de estado).
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

from .. import models, schemas
from ..config import settings
from ..database import get_db
from ..oauth import oauth
from ..redis_client import blacklist_token
from ..security import get_current_user
from ..services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])
_bearer = HTTPBearer()


@router.post("/signup", response_model=schemas.TokenResponse, status_code=201)
def signup(body: schemas.SignUpRequest, db: Session = Depends(get_db)):
    return auth_service.register_user(body, db)


@router.post("/login", response_model=schemas.TokenResponse)
def login(body: schemas.LoginRequest, db: Session = Depends(get_db)):
    return auth_service.authenticate_user(body, db)


@router.post("/logout", response_model=schemas.MessageResponse)
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    _: models.User = Depends(get_current_user),
):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        exp = payload.get("exp", 0)
        ttl = max(int(exp - datetime.now(timezone.utc).timestamp()), 1)
    except JWTError:
        ttl = 60  # fallback conservador

    blacklist_token(token, ttl)
    return {"message": "Sesión cerrada correctamente."}


@router.get("/login/google")
async def google_login(request: Request):
    """Redirige al usuario a la página de Google"""
    redirect_uri = request.url_for('auth_callback')
    return await oauth.google.authorize_redirect(request, str(redirect_uri))


@router.get("/callback/google", name="auth_callback")
async def auth_callback(request: Request, db: Session = Depends(get_db)):
    """Recibe la respuesta de Google y procesa el login"""
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get('userinfo')

    if not user_info:
        raise HTTPException(status_code=400, detail="No se pudo obtener informacion de Google")

    return auth_service.authenticate_or_register_social_user("google", user_info, db)


@router.post("/google/mobile", response_model=schemas.TokenResponse)
async def google_mobile_login(
    body: schemas.GoogleMobileRequest,
    db: Session = Depends(get_db),
):
    """Verifica un ID token nativo de Google (iOS/Android) y procesa el login."""
    try:
        idinfo = google_id_token.verify_oauth2_token(
            body.id_token,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Token de Google inválido o expirado.")

    user_info = {
        "email": idinfo.get("email"),
        "sub": idinfo.get("sub"),
        "name": idinfo.get("name", idinfo.get("email", "").split("@")[0]),
    }
    return auth_service.authenticate_or_register_social_user("google", user_info, db)
