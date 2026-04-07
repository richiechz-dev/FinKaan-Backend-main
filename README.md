# FinKaan Backend

Backend FastAPI para la app de educación financiera **FinKaan**.

---

## Estructura del proyecto

```
finkaan_backend/
├── main.py              # Punto de entrada: app FastAPI, middleware, routers
├── config.py            # Settings centralizados (pydantic-settings + .env)
├── database.py          # Engine SQLAlchemy y dependency get_db()
├── models.py            # Modelos ORM: User, UserProgress, Scenario
├── schemas.py           # Schemas Pydantic para request/response
├── security.py          # Hash de contraseñas, JWT, dependency get_current_user()
├── redis_client.py      # Cliente Redis y blacklist de tokens
├── routers/
│   ├── auth.py          # POST /auth/signup, /auth/login, /auth/logout
│   ├── users.py         # GET/PUT /users/me, onboarding, progreso
│   └── scenarios.py     # GET /scenarios, /scenarios/{id}
├── services/
│   ├── auth_service.py  # Lógica de registro y autenticación
│   └── user_service.py  # Lógica de perfil, onboarding y progreso
└── scripts/
    ├── seed_scenarios.py  # Carga/actualiza escenarios desde JSON
    ├── scenarios_seed.json
    ├── setup.sql          # Crea usuario y base de datos en PostgreSQL
    └── start.sh           # Arranca el servidor en desarrollo
```

### Por qué esta estructura

| Capa | Responsabilidad |
|------|----------------|
| `routers/` | Solo HTTP: valida entrada, llama al servicio, devuelve respuesta |
| `services/` | Lógica de negocio pura: sin saber de HTTP ni de schemas Pydantic |
| `security.py` | Seguridad transversal: no es un router, no es un servicio de dominio |
| `models.py` | Definición de tablas ORM, sin lógica de negocio |
| `schemas.py` | Contratos de API (Pydantic), sin acceso a DB |

---

## Instalación

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Configuración

Copia `.env` y ajusta los valores:

```bash
cp .env .env.local
```

Variables requeridas:

| Variable | Descripción |
|----------|-------------|
| `DATABASE_URL` | URL de conexión PostgreSQL |
| `SECRET_KEY` | Clave secreta para firmar JWTs |
| `REDIS_URL` | URL de Redis (default: `redis://localhost:6379/0`) |

## Base de datos

```bash
# Crear usuario y DB (como superusuario PostgreSQL)
psql -U postgres -f scripts/setup.sql

# Las tablas se crean automáticamente al arrancar el servidor
```

## Cargar escenarios iniciales

```bash
python -m finkaan_backend.scripts.seed_scenarios

# Con un JSON diferente:
python -m finkaan_backend.scripts.seed_scenarios --file ruta/a/scenarios.json
```

## Arrancar el servidor

```bash
bash scripts/start.sh

# O directamente:
uvicorn finkaan_backend.main:app --host 0.0.0.0 --port 8000 --reload
```

La documentación interactiva queda disponible en:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Endpoints principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/auth/signup` | Registro |
| POST | `/auth/login` | Login |
| POST | `/auth/logout` | Logout (invalida token) |
| GET | `/users/me` | Perfil del usuario |
| PUT | `/users/me/name` | Actualizar nombre |
| PUT | `/users/me/password` | Cambiar contraseña |
| PUT | `/users/me/language` | Cambiar idioma |
| POST | `/users/me/onboarding` | Guardar onboarding |
| GET | `/users/me/progress` | Obtener progreso |
| POST | `/users/me/progress/complete` | Completar escenario |
| PUT | `/users/me/progress/theme` | Cambiar tema |
| GET | `/scenarios` | Listar todos los escenarios |
| GET | `/scenarios/{id}` | Obtener escenario por id |
| GET | `/health` | Health check |

## Notas de producción

- Reemplazar `allow_origins=["*"]` en `main.py` por el dominio real.
- Usar **Alembic** para migraciones en lugar de `create_all`.
- El `SECRET_KEY` debe generarse con `python -c "import secrets; print(secrets.token_hex(32))"`.
