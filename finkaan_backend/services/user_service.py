"""
services/user_service.py — Lógica de negocio para usuarios y progreso.

Extrae las operaciones de datos de los routers, dejando a estos solo
el manejo de HTTP (validación de entrada, códigos de respuesta).
"""
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..security import hash_password, verify_password

# XP necesario para subir de nivel (nivel actual → siguiente)
_LEVEL_THRESHOLDS = {1: 200, 2: 500, 3: 1000, 4: 1800, 5: 3000}


# ─── Helpers internos ─────────────────────────────────────────────────────────

def _recalculate_level(xp: int, current_level: int) -> int:
    level = current_level
    while xp >= _LEVEL_THRESHOLDS.get(level, 99_999) and level < 5:
        level += 1
    return level


def get_or_create_progress(user: models.User, db: Session) -> models.UserProgress:
    """Devuelve el progreso del usuario, creándolo si no existe."""
    if user.progress is None:
        progress = models.UserProgress(user_id=user.id)
        db.add(progress)
        db.flush()
        db.refresh(user)
    return user.progress


def build_progress_response(progress: models.UserProgress) -> schemas.ProgressResponse:
    """Convierte un modelo UserProgress al schema de respuesta."""
    return schemas.ProgressResponse(
        total_xp=progress.total_xp,
        level=progress.level,
        streak=progress.streak,
        completed_ids=list(progress.completed_set()),
        unlocked_ids=list(progress.unlocked_set()),
        streak_days=progress.streak_days_list(),
        theme_mode=progress.theme_mode,
    )


# ─── Operaciones de usuario ───────────────────────────────────────────────────

def update_name(user: models.User, name: str, db: Session) -> None:
    user.name = name
    db.commit()


def change_password(
    user: models.User,
    current_password: str,
    new_password: str,
    db: Session,
) -> None:
    if not verify_password(current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual es incorrecta.",
        )
    user.hashed_password = hash_password(new_password)
    db.commit()


def update_language(user: models.User, language: int, db: Session) -> None:
    user.language = language
    db.commit()


def save_onboarding(user: models.User, body: schemas.OnboardingRequest, db: Session) -> None:
    user.language = body.language
    user.situation = body.situation
    user.goal = body.goal
    user.finance_level = body.finance_level
    user.onboarding_done = True
    db.commit()


# ─── Operaciones de progreso ──────────────────────────────────────────────────

def complete_scenario(
    user: models.User,
    body: schemas.CompleteScenarioRequest,
    db: Session,
) -> models.UserProgress:
    """
    Marca un escenario como completado (idempotente).
    Actualiza XP, nivel, racha y desbloquea el siguiente escenario.
    """
    progress = get_or_create_progress(user, db)

    completed = progress.completed_set()
    unlocked = progress.unlocked_set()

    # Idempotente: no procesar si ya estaba completado
    if body.scenario_id in completed:
        return progress

    completed.add(body.scenario_id)
    progress.total_xp += body.xp_earned
    progress.streak += 1
    progress.level = _recalculate_level(progress.total_xp, progress.level)

    if body.next_scenario_id is not None:
        unlocked.add(body.next_scenario_id)

    # Marcar el día de hoy en streak_days (0=Lun … 6=Dom)
    days = progress.streak_days_list()
    days[datetime.now(timezone.utc).weekday()] = True

    progress.set_completed(completed)
    progress.set_unlocked(unlocked)
    progress.set_streak_days(days)

    db.commit()
    db.refresh(progress)
    return progress


def update_theme(user: models.User, theme_mode: int, db: Session) -> None:
    progress = get_or_create_progress(user, db)
    progress.theme_mode = theme_mode
    db.commit()
