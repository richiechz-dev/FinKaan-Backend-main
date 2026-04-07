"""
routers/users.py — Perfil, onboarding y progreso del usuario.

Añade: GET /users/me/sync_info — endpoint ultraligero para detección
de cambios sin descargar datos completos.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import get_current_user
from ..services import user_service

router = APIRouter(prefix="/users", tags=["users"])


# ─── Perfil ───────────────────────────────────────────────────────────────────

@router.get("/me", response_model=schemas.UserProfile)
def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.put("/me/name", response_model=schemas.MessageResponse)
def update_name(
    body: schemas.UpdateNameRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_service.update_name(current_user, body.name, db)
    return {"message": "Nombre actualizado."}


@router.put("/me/password", response_model=schemas.MessageResponse)
def change_password(
    body: schemas.ChangePasswordRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_service.change_password(current_user, body.current_password, body.new_password, db)
    return {"message": "Contraseña actualizada."}


@router.put("/me/language", response_model=schemas.MessageResponse)
def update_language(
    body: schemas.UpdateLanguageRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_service.update_language(current_user, body.language, db)
    return {"message": "Idioma actualizado."}


# ─── Onboarding ───────────────────────────────────────────────────────────────

@router.post("/me/onboarding", response_model=schemas.MessageResponse)
def save_onboarding(
    body: schemas.OnboardingRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_service.save_onboarding(current_user, body, db)
    return {"message": "Onboarding guardado."}


# ─── Progreso ─────────────────────────────────────────────────────────────────

@router.get("/me/progress", response_model=schemas.ProgressResponse)
def get_progress(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    progress = user_service.get_or_create_progress(current_user, db)
    return user_service.build_progress_response(progress)


@router.post("/me/progress/complete", response_model=schemas.ProgressResponse)
def complete_scenario(
    body: schemas.CompleteScenarioRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    progress = user_service.complete_scenario(current_user, body, db)
    return user_service.build_progress_response(progress)


@router.put("/me/progress/theme", response_model=schemas.MessageResponse)
def update_theme(
    body: schemas.UpdateThemeRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_service.update_theme(current_user, body.theme_mode, db)
    return {"message": "Tema actualizado."}


# ─── Sync Info (nuevo) ────────────────────────────────────────────────────────

@router.get("/me/sync_info", response_model=schemas.SyncInfoResponse)
def get_sync_info(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Endpoint ultraligero: devuelve solo los timestamps del perfil/progreso
    y la versión de escenarios. El cliente lo usa para saber si necesita
    descargar datos completos, evitando tráfico innecesario.
    """
    progress = user_service.get_or_create_progress(current_user, db)

    # Versión de escenarios: cuenta de filas activas (simple y sin joins)
    from .. import models as m
    scenarios_version = db.query(m.Scenario).filter(m.Scenario.is_active == True).count()

    return schemas.SyncInfoResponse(
        profile_updated_at=current_user.updated_at.isoformat(),
        progress_updated_at=progress.last_updated.isoformat(),
        scenarios_version=scenarios_version,
    )
