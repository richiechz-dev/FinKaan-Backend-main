-- ─── setup.sql — Ejecutar como superusuario de PostgreSQL ───────────────────
-- psql -U postgres -f scripts/setup.sql

-- 1. Crear usuario
CREATE USER finkaan_user WITH PASSWORD 'JCama364_!';

-- 2. Crear base de datos
CREATE DATABASE finkaan_db OWNER finkaan_user;

-- 3. Permisos
GRANT ALL PRIVILEGES ON DATABASE finkaan_db TO finkaan_user;

-- Las tablas se crean automáticamente cuando arranca el backend (Base.metadata.create_all).
-- En producción se recomienda usar Alembic para migraciones controladas.
