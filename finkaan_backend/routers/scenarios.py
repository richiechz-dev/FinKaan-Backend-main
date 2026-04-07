"""
routers/scenarios.py — Escenarios del juego FinKaan.

Los escenarios se almacenan en la tabla `scenarios` como filas con un campo
`data` (JSON serializado). El cliente obtiene todos de una sola llamada:
    GET /scenarios  →  lista completa ordenada por `order_index`

Para cargar los escenarios iniciales usa:
    python -m finkaan_backend.scripts.seed_scenarios
"""
import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..security import get_current_user
from ..database import get_db

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.get("", response_model=list[schemas.ScenarioOut])
def list_scenarios(
    _: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Devuelve todos los escenarios activos ordenados por order_index."""
    rows = (
        db.query(models.Scenario)
        .filter(models.Scenario.is_active == True)
        .order_by(models.Scenario.order_index)
        .all()
    )
    return [
        schemas.ScenarioOut(id=row.id, order_index=row.order_index, data=json.loads(row.data))
        for row in rows
    ]


@router.get("/{scenario_id}", response_model=schemas.ScenarioOut)
def get_scenario(
    scenario_id: int,
    _: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Devuelve un escenario específico por su id."""
    row = db.query(models.Scenario).filter(
        models.Scenario.id == scenario_id,
        models.Scenario.is_active == True,
    ).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escenario no encontrado.")
    return schemas.ScenarioOut(id=row.id, order_index=row.order_index, data=json.loads(row.data))
