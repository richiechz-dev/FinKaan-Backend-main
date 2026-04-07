@echo off
title Backend FinKaan - FastAPI
color 0A

:: Navegar a la carpeta del proyecto (por si acaso)
cd /d "E:\Proyecto FinKaan\backend"

echo ==========================================
echo    INICIANDO BACKEND FINKAAN
echo ==========================================

:: Activar el entorno virtual e iniciar uvicorn en una sola linea
:: Usamos call para asegurar que el venv se mantenga activo para el comando
call finkaan_backend\venv\Scripts\activate && uvicorn finkaan_backend.main:app --host 0.0.0.0 --port 8000 --reload

pause