"""
models.py — Modelos SQLAlchemy para FinKaan
"""
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean, DateTime, Integer, String, Text,
    ForeignKey, JSON, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ─── User ─────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    # Preferencias de onboarding
    language: Mapped[int] = mapped_column(Integer, default=0)          # índice de AppLanguage
    situation: Mapped[int | None] = mapped_column(Integer, nullable=True)
    goal: Mapped[int | None] = mapped_column(Integer, nullable=True)
    finance_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    onboarding_done: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relación con progreso
    progress: Mapped["UserProgress"] = relationship(
        "UserProgress", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    # Relación con Provedores para Loging
    social_providers: Mapped[list["SocialProvider"]] = relationship(
        "SocialProvider", back_populates="user", cascade="all, delete-orphan"
    )

    # Realción con Feedback
    feedback: Mapped[list["Feedback"]] = relationship(
        "Feedback", back_populates="user", cascade="all, delete-orphan"
    )

    # Relación con Answers 
    answers: Mapped[list["Answers"]] = relationship(
        "Answers", back_populates="user", cascade="all, delete-orphan"  
    )


# ─── UserProgress ─────────────────────────────────────────────────────────────

class UserProgress(Base): 
    __tablename__ = "user_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    total_xp: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[int] = mapped_column(Integer, default=1)
    streak: Mapped[int] = mapped_column(Integer, default=0)

    # Listas serializadas como cadenas separadas por comas
    # Ejemplo: "1,3,5" → {1, 3, 5}
    completed_ids: Mapped[str] = mapped_column(Text, default="")
    unlocked_ids: Mapped[str] = mapped_column(Text, default="1")

    # 7 booleans para Lu-Do → "0,1,0,1,0,0,0"
    streak_days: Mapped[str] = mapped_column(String(13), default="0,0,0,0,0,0,0")

    # Tema: 0=system, 1=light, 2=dark
    theme_mode: Mapped[int] = mapped_column(Integer, default=0)

    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    user: Mapped["User"] = relationship("User", back_populates="progress")

    # ── helpers ──────────────────────────────────────────────────────────────

    def completed_set(self) -> set[int]:
        if not self.completed_ids:
            return set()
        return {int(x) for x in self.completed_ids.split(",") if x}

    def unlocked_set(self) -> set[int]:
        if not self.unlocked_ids:
            return {1}
        return {int(x) for x in self.unlocked_ids.split(",") if x}

    def streak_days_list(self) -> list[bool]:
        if not self.streak_days:
            return [False] * 7
        return [x == "1" for x in self.streak_days.split(",")]

    def set_completed(self, ids: set[int]) -> None:
        self.completed_ids = ",".join(str(i) for i in sorted(ids))

    def set_unlocked(self, ids: set[int]) -> None:
        self.unlocked_ids = ",".join(str(i) for i in sorted(ids))

    def set_streak_days(self, days: list[bool]) -> None:
        self.streak_days = ",".join("1" if d else "0" for d in days)


# ─── SocialProvider ─────────────────────────────────────────────────────────────

class SocialProvider(Base):
    __tablename__ = "social_providers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    provider_user_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="social_providers")


# ─── Scenario ─────────────────────────────────────────────────────────────────

class Scenario(Base):
    """
    Almacena cada escenario como un bloque JSON completo.

    Por qué JSON en texto y no columnas normalizadas:
    - La estructura de un escenario (steps, options, narratives…) es compleja y
      variable — normalizar implicaría 5+ tablas con joins costosos.
    - El cliente siempre consume el escenario completo; nunca filtra por campos
      internos del JSON desde el backend.
    - Escalar es sencillo: migrar el tipo de la columna a JSONB en PostgreSQL
      añade índices GIN sin tocar el código de la app.

    Campos que SÍ son columnas reales (para ordenar/filtrar eficientemente):
    - id          → clave primaria = el id lógico del escenario
    - order_index → posición en el mapa de misiones
    - is_active   → soft-delete para retirar escenarios sin borrarlos
    """
    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    data: Mapped[str] = mapped_column(Text, nullable=False)   # JSON serializado
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class Feedback(Base):
    __tablename__ = "feed_back"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    sintesis: Mapped[str] = mapped_column(String, nullable=False)
    fb: Mapped[str] = mapped_column(String, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="feedback")

class Answers(Base):
    __tablename__ = "answers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id : Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    narrativa_id: Mapped[int] = mapped_column(Integer, nullable=False)
    narrativa: Mapped[str] = mapped_column(String, nullable=False)
    question: Mapped[str] = mapped_column(String, nullable=False)
    respuesta: Mapped[str] = mapped_column(String, nullable=False)
    delta:   Mapped[int] = mapped_column(Integer, nullable=False)
    isGood: Mapped[bool] = mapped_column(Boolean, nullable=False)
    isUsed:  Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    user: Mapped["User"] = relationship("User", back_populates="answers")
    
    # Relación opcional — para hacer scenario
    translations: Mapped[list["ScenarioTranslation"]] = relationship(back_populates="scenario")


class ScenarioTranslation(Base):
    """
    Guarda las traducciones de cada escenario a otras lenguas.
    
    La columna 'data' tiene exactamente la misma forma que Scenario.data
    (el mismo JSON con title, description, steps, etc.) — solo que
    los textos están en otro idioma.
    
    Campos no textuales como emoji, color, xp, difficulty NO se traducen;
    esos los sigue leyendo el cliente desde la tabla scenarios original.
    """
    __tablename__ = "scenario_translations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Qué escenario es este (referencia a scenarios.id)
    scenario_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("scenarios.id"), nullable=False
    )
    
    # Código del idioma: 'es_coloquial', 'nah', 'mix', 'zap', 'oto', 'tzo', 'tze'
    lang: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # El JSON traducido (misma estructura que Scenario.data)
    data: Mapped[str] = mapped_column(Text, nullable=False)
    
    # False = generado por IA, True = revisado por hablante nativo
    # Útil para saber qué traducciones ya son confiables
    is_reviewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    # Relación inversa opcional — para hacer scenario.translations desde Python
    scenario: Mapped["Scenario"] = relationship(back_populates="translations")

    # Restricción: no puede haber dos traducciones del mismo escenario al mismo idioma
    __table_args__ = (
        UniqueConstraint("scenario_id", "lang", name="uq_scenario_lang"),
    )
