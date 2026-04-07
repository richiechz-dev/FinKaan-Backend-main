"""
services/auth_service.py — Lógica de negocio para autenticación.
"""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..security import hash_password, verify_password, create_access_token


def register_user(body: schemas.SignUpRequest, db: Session) -> schemas.TokenResponse:
    """Crea un usuario nuevo y su progreso inicial. Lanza 409 si el email ya existe."""
    existing = db.query(models.User).filter(
        models.User.email == body.email.lower()
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este correo ya tiene una cuenta.",
        )

    user = models.User(
        name=body.name,
        email=body.email.lower(),
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    db.flush()  # obtiene user.id sin commit

    db.add(models.UserProgress(user_id=user.id))
    db.commit()
    db.refresh(user)

    return schemas.TokenResponse(
        access_token=create_access_token(user.id),
        user_id=user.id,
        name=user.name,
        onboarding_done=user.onboarding_done,
    )


def authenticate_user(body: schemas.LoginRequest, db: Session) -> schemas.TokenResponse:
    """Valida credenciales y retorna un token. Lanza 401 si son incorrectas."""
    user = db.query(models.User).filter(
        models.User.email == body.email.lower()
    ).first()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos.",
        )

    return schemas.TokenResponse(
        access_token=create_access_token(user.id),
        user_id=user.id,
        name=user.name,
        onboarding_done=user.onboarding_done,
    )


def authenticate_or_register_social_user(
    provider: str,
    user_info: dict,
    db: Session
) -> schemas.TokenResponse:
    """Autentica o registra un usuario via proveedor social (Google, etc.)."""
    # Extraer datos normalizados del proveedor
    email = user_info.get("email").lower()
    provider_user_id = user_info.get("sub")  # ID único del proveedor
    name = user_info.get("name", email.split("@")[0])

    social_acc = db.query(models.SocialProvider).filter(
        models.SocialProvider.provider == provider,
        models.SocialProvider.provider_user_id == provider_user_id
    ).first()

    if social_acc:
        user = social_acc.user
    else:
        user = db.query(models.User).filter(models.User.email == email).first()

        if not user:
            user = models.User(
                name=name,
                email=email,
                hashed_password=None,
                onboarding_done=False
            )
            db.add(user)
            db.flush()
            db.add(models.UserProgress(user_id=user.id))

        new_social = models.SocialProvider(
            user_id=user.id,
            provider=provider,
            provider_user_id=provider_user_id,
            raw_data=user_info
        )
        db.add(new_social)
        db.commit()

    return schemas.TokenResponse(
        access_token=create_access_token(user.id),
        user_id=user.id,
        name=user.name,
        onboarding_done=user.onboarding_done,
    )
