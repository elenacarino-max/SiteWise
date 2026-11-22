"""Export the municipal indicators used by the frontend from the local v0.3 dataset."""

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/processed/sitewise_v03"
TARGET = ROOT / "apps/frontend/public/indicadores-municipales.json"
GROUPS = ROOT / "apps/frontend/src/gruposIndicadores.json"


def main():
    groups = json.loads(GROUPS.read_text(encoding="utf-8"))
    fields = {field for group in groups for field in group["indicadores"]}
    with (SOURCE / "indicadores.csv").open(encoding="utf-8-sig", newline="") as file:
        definitions = {
            row["id_indicador"]: {
                key: row[key]
                for key in ("nombre", "unidad", "fuente", "url", "fecha_dato")
            }
            for row in csv.DictReader(file)
            if row["id_indicador"] in fields
        }
    if fields != definitions.keys():
        raise ValueError(f"Indicadores sin definición: {fields - definitions.keys()}")

    municipalities = {}
    with (SOURCE / "valores_app.csv").open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            field = row["id_indicador"]
            if field not in fields:
                continue

            values = municipalities.setdefault(row["cod_ine"], {})
            if row["valor"] and row["estado_app"] in ("real", "aproximado"):
                dato = {
                    "valor": float(row["valor"]),
                    "estado": row["estado_app"],
                }
                if row["estimado_app"] == "True":
                    dato["metodo"] = row["metodo"]
                if row["url_fuente"] and row["url_fuente"] != definitions[field]["url"]:
                    dato["url"] = row["url_fuente"]
                if row["fecha_dato"] and row["fecha_dato"] != definitions[field]["fecha_dato"]:
                    dato["fecha_dato"] = row["fecha_dato"]
                values[field] = dato

    payload = {"indicadores": definitions, "municipios": municipalities}
    TARGET.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n",
                      encoding="utf-8")


if __name__ == "__main__":
    main()
