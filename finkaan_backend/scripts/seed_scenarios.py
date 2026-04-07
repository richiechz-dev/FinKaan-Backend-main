"""
scripts/seed_scenarios.py
Carga (o actualiza) los escenarios desde un archivo JSON hacia la base de datos.

Uso:
    # Desde la raíz del proyecto (donde está finkaan_backend/)
    python -m finkaan_backend.scripts.seed_scenarios

    # Para apuntar a un JSON diferente:
    python -m finkaan_backend.scripts.seed_scenarios --file ruta/a/scenarios.json

El JSON debe ser una lista de objetos escenario con al menos { "id": <int>, ... }.
Si el escenario ya existe en la DB, actualiza su data; si no, lo inserta.
"""
import argparse
import json
import sys
from pathlib import Path

# Añadir la raíz del proyecto al path para importar finkaan_backend.*
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from finkaan_backend.database import SessionLocal, engine, Base
from finkaan_backend.models import Scenario

# JSON de escenarios por defecto (junto a este script)
DEFAULT_JSON = Path(__file__).parent / "scenarios_seed.json"


def seed(json_path: Path) -> None:
    if not json_path.exists():
        print(f"❌  No se encontró el archivo: {json_path}")
        sys.exit(1)

    with open(json_path, encoding="utf-8") as f:
        scenarios: list[dict] = json.load(f)

    if not isinstance(scenarios, list):
        print("❌  El JSON debe ser una lista de escenarios.")
        sys.exit(1)

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        inserted = 0
        updated = 0
        for idx, sc in enumerate(scenarios):
            sc_id = sc.get("id")
            if sc_id is None:
                print(f"⚠️   Escenario en posición {idx} sin 'id' — omitido.")
                continue

            row = db.query(Scenario).filter(Scenario.id == sc_id).first()
            data_str = json.dumps(sc, ensure_ascii=False)

            if row is None:
                db.add(Scenario(
                    id=sc_id,
                    order_index=idx,
                    data=data_str,
                    is_active=True,
                ))
                inserted += 1
            else:
                row.order_index = idx
                row.data = data_str
                row.is_active = True
                updated += 1

        db.commit()
        print(f"✅  Seed completado: {inserted} insertados, {updated} actualizados.")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed de escenarios FinKaan")
    parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_JSON,
        help="Ruta al JSON de escenarios (default: scripts/scenarios_seed.json)",
    )
    args = parser.parse_args()
    seed(args.file)
