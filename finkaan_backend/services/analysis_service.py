"""
services/analysis_service.py — Análisis conductual con IA (Claude → Gemini fallback).
"""
import json
import logging
import re
from typing import Any

import httpx
from fastapi import HTTPException, status

from ..config import settings

logger = logging.getLogger(__name__)

# ─── Constantes ───────────────────────────────────────────────────────────────

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL   = "claude-sonnet-4-20250514"
GEMINI_MODEL      = "gemini-2.5-flash"

# ─── Prompt ───────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """Eres un psicólogo financiero conductual de la app FinKaan.
Analiza el perfil del usuario y detecta sesgos conductuales financieros.

Responde ÚNICAMENTE con JSON válido, sin markdown, sin texto adicional.

Estructura exacta:
{
  "conductual_score": <entero 0-100>,
  "score_label": "<'Iniciante'|'En desarrollo'|'Avanzado'|'Experto'>",
  "intro_text": "<2-3 oraciones describiendo el perfil>",
  "sessions": [
    {"label": "<texto>", "score": <int>, "tag": "<C|C+|B-|B|B+|A-|A|A+>", "is_today": <bool>}
  ],
  "biases": [
    {
      "name": "<nombre en español>",
      "short_name": "<max 15 chars>",
      "category": "<categoría>",
      "level": "<'ALTO'|'MODERADO'|'BAJO'>",
      "intensity": <float 0.0-1.0>,
      "description": "<2-3 oraciones personalizadas>",
      "tip": "<consejo práctico>",
      "icon": "<'filter_alt'|'trending_down'|'timer'|'account_balance'|'anchor'|'psychology'|'warning_amber'|'search'>"
    }
  ]
}

Reglas:
- Mínimo 3 sesgos, máximo 5
- conductual_score: 0-30 Iniciante, 31-55 En desarrollo, 56-75 Avanzado, 76-100 Experto
- sessions: 2-4 entradas con evolución, la última con is_today=true
- Sin datos de decisiones: score entre 40-60, análisis basado en perfil
- Sé específico y personalizado
- IMPORTANTE: No uses comillas dobles dentro de los valores de texto. Usa solo comillas simples si necesitas citar algo."""


# ─── Mensajes ─────────────────────────────────────────────────────────────────

def _build_message(decisions: list[dict[str, Any]], user_context: dict[str, Any]) -> str:
    lines = []

    if decisions:
        lines.append("El usuario completó estos escenarios:\n")
        for i, d in enumerate(decisions, 1):
            lines.append(f"--- Escenario {i}: {d.get('scenario_title', 'Sin título')} ---")
            lines.append(f"Dificultad: {d.get('difficulty', 'media')} | XP: {d.get('xp_earned', 0)} | Calificación: {d.get('grade', 'N/A')}")
            lines.append(f"Balance final: ${d.get('final_balance', 0):,}")
            for j, step in enumerate(d.get("steps", []), 1):
                lines.append(
                    f"  Paso {j}: '{step.get('question', '')}' → "
                    f"'{step.get('selected_option_text', '')}' "
                    f"({'✓ buena' if step.get('is_good_choice') else '✗ subóptima'})"
                )
            lines.append("")
    else:
        lines.append("El usuario aún no ha completado escenarios en esta sesión.\n")
        lines.append("Infiere sesgos probables desde su perfil e invítalo a jugar para refinar el análisis.\n")

    lines.append("Perfil del usuario:")
    lines.append(f"- Conocimiento financiero: {user_context.get('finance_level', 'principiante')}")
    lines.append(f"- Situación: {user_context.get('situation', 'no especificada')}")
    lines.append(f"- Objetivo: {user_context.get('goal', 'no especificado')}")
    lines.append(f"- Nivel en app: {user_context.get('app_level', 1)}")
    lines.append(f"- Escenarios completados: {user_context.get('completed_count', 0)}")

    return "\n".join(lines)


# ─── Parser ───────────────────────────────────────────────────────────────────

def _parse_json(raw: str) -> dict[str, Any]:
    raw = raw.strip()

    # Intento 1: JSON puro
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Intento 2: Eliminar bloques markdown (```json ... ```)
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Intento 3: Extraer primer { ... } completo
    start = cleaned.find("{")
    end   = cleaned.rfind("}") + 1
    if start != -1 and end > start:
        candidate = cleaned[start:end]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

        # Intento 4: Reparar comillas dobles no escapadas dentro de strings
        # Busca patrones como: "campo": "texto con "comillas" adentro"
        repaired = _repair_json_strings(candidate)
        try:
            return json.loads(repaired)
        except json.JSONDecodeError as exc:
            logger.error("JSON inválido tras reparación: %s | candidate[:400]: %s", exc, candidate[:400])
            raise ValueError(str(exc)) from exc

    raise ValueError(f"Sin JSON en respuesta. Raw[:300]: {raw[:300]}")


def _repair_json_strings(text: str) -> str:
    """
    Intenta reparar JSON con comillas dobles no escapadas dentro de valores string.
    Reemplaza comillas dobles internas por comillas simples.
    """
    # Estrategia: parsear carácter a carácter y escapar comillas dentro de strings
    result = []
    in_string = False
    escape_next = False
    i = 0

    while i < len(text):
        ch = text[i]

        if escape_next:
            result.append(ch)
            escape_next = False
            i += 1
            continue

        if ch == "\\":
            escape_next = True
            result.append(ch)
            i += 1
            continue

        if ch == '"':
            if not in_string:
                in_string = True
                result.append(ch)
            else:
                # ¿Es el cierre real? Mira el siguiente carácter no-espacio
                rest = text[i + 1:].lstrip()
                if rest and rest[0] in (",", "}", "]", ":"):
                    in_string = False
                    result.append(ch)
                else:
                    # Comilla dentro del string — reemplazar por comilla simple
                    result.append("'")
        else:
            result.append(ch)

        i += 1

    return "".join(result)


# ─── Provider: Claude ─────────────────────────────────────────────────────────

async def _call_claude(message: str, client: httpx.AsyncClient) -> dict[str, Any]:
    api_key = settings.ANTHROPIC_API_KEY.strip()
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY vacía en .env")

    resp = await client.post(
        ANTHROPIC_API_URL,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": ANTHROPIC_MODEL,
            "max_tokens": 2000,
            "system": _SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": message}],
        },
    )

    if resp.status_code != 200:
        raise ValueError(f"Claude HTTP {resp.status_code}: {resp.text[:200]}")

    return _parse_json(resp.json()["content"][0]["text"])


# ─── Provider: Gemini SDK ─────────────────────────────────────────────────────

async def _call_gemini(message: str) -> dict[str, Any]:
    api_key = settings.GEMINI_API_KEY.strip()
    if not api_key:
        raise ValueError("GEMINI_API_KEY vacía en .env")

    import google.generativeai as genai
    import asyncio

    genai.configure(api_key=api_key)

    # Intentar con response_mime_type (SDKs recientes); si no lo soporta, ignorar
    try:
        gen_config = genai.GenerationConfig(
            temperature=0.4,
            max_output_tokens=8192,          # ← Era 2000: el JSON completo en español supera ese límite
            response_mime_type="application/json",  # Fuerza JSON válido en SDKs que lo soportan
        )
    except TypeError:
        # SDK antiguo que no acepta response_mime_type
        gen_config = genai.GenerationConfig(
            temperature=0.4,
            max_output_tokens=8192,
        )

    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=_SYSTEM_PROMPT,
        generation_config=gen_config,
    )

    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: model.generate_content(message),
    )

    raw = response.text
    logger.info(
        "Gemini raw (%d chars, finish=%s): %s…",
        len(raw),
        getattr(response.candidates[0], "finish_reason", "?") if response.candidates else "?",
        raw[:200],
    )

    # Detectar truncamiento por token limit antes de intentar parsear
    if response.candidates:
        finish = getattr(response.candidates[0], "finish_reason", None)
        if finish and str(finish) not in ("FinishReason.STOP", "STOP", "1"):
            logger.warning("Gemini terminó por razón distinta a STOP: %s — posible truncamiento", finish)

    return _parse_json(raw)


# ─── Punto de entrada ─────────────────────────────────────────────────────────

async def generate_behavioral_analysis(
    decisions: list[dict[str, Any]],
    user_context: dict[str, Any],
) -> dict[str, Any]:
    """
    Genera análisis conductual. Fallback automático Claude → Gemini.
    Siempre llama a la IA (con o sin decisiones).
    """
    message = _build_message(decisions, user_context)

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            result = await _call_claude(message, client)
            logger.info("Análisis con Claude ✅")
            return result
        except Exception as exc:
            logger.warning("Claude falló (%s) — usando Gemini…", exc)

    try:
        result = await _call_gemini(message)
        logger.info("Análisis con Gemini ✅")
        return result
    except Exception as exc:
        logger.error("Gemini falló: %s", exc)

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Servicio de análisis no disponible. Intenta más tarde.",
    )