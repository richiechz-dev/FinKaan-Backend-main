"""
routers/analysis.py — Análisis conductual con IA.

POST /analysis/behavioral
    Recibe el historial de decisiones del usuario y retorna
    un análisis conductual generado por Claude.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Any

from ..models import User
from ..security import get_current_user
from ..services import analysis_service
from .. import models
from ..database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/analysis", tags=["analysis"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class StepDecision(BaseModel):
    question: str
    selected_option_text: str
    is_good_choice: bool


class ScenarioDecision(BaseModel):
    scenario_id: int
    scenario_title: str
    difficulty: str = "media"
    xp_earned: int = Field(ge=0)
    grade: str = ""
    final_balance: int = 0
    steps: list[StepDecision] = []


class UserContext(BaseModel):
    finance_level: str = "principiante"
    situation: str = ""
    goal: str = ""
    app_level: int = Field(ge=1, default=1)
    completed_count: int = Field(ge=0, default=0)


class BehavioralAnalysisRequest(BaseModel):
    decisions: list[ScenarioDecision]
    user_context: UserContext = UserContext()


class BehavioralAnalysisResponse(BaseModel):
    conductual_score: int
    score_label: str
    intro_text: str
    sessions: list[dict[str, Any]]
    biases: list[dict[str, Any]]

class BehavioralAnalysisRequest(BaseModel):
    decisions: list[ScenarioDecision]
    user_context: UserContext = UserContext()


class NewBehavioralAnalysisRequest(BaseModel):
    user_context: UserContext = UserContext()


@router.post("/behavioral_new")
async def behavioral_analysis(
    body: NewBehavioralAnalysisRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    context_raw = body.user_context.model_dump()

    result = await analysis_service.build_retro(
        db=db,
        user_id=current_user.id,
        user_context=context_raw
    )

    return result

    
    


@router.post("/behavioral",response_model=BehavioralAnalysisResponse) # response_model=BehavioralAnalysisResponse)
async def behavioral_analysis(
    body: BehavioralAnalysisRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Genera análisis conductual personalizado usando Claude.
    Recibe las decisiones del usuario y retorna sesgos detectados,
    puntuación conductual y evolución por sesiones.
    """
    decisions_raw = [d.model_dump() for d in body.decisions]
    context_raw = body.user_context.model_dump()

    result = await analysis_service.generate_behavioral_analysis(
        decisions=decisions_raw,
        user_context=context_raw,
    )

    return BehavioralAnalysisResponse(**result)
