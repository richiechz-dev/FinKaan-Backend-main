#!/usr/bin/env bash
# scripts/start.sh — Inicia el backend FinKaan en desarrollo
# Uso: bash scripts/start.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

cd "$BACKEND_DIR"

# Activar venv si existe
if [ -d "venv" ]; then
  source venv/bin/activate
fi

echo "🚀 Iniciando FinKaan Backend..."
uvicorn finkaan_backend.main:app --host 0.0.0.0 --port 8000 --reload
