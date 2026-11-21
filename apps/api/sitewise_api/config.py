"""Ajustes de la API: de dónde leo los datos. Se pueden cambiar con variables de entorno."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# El diccionario del dataset escribe a veces "sidewise" (con d) por una errata.
# Pruebo las dos carpetas y me quedo con la primera que exista.
CANDIDATAS = ("data/processed/sitewise_v03", "data/processed/sidewise_v03")


@dataclass(frozen=True)
class Ajustes:
    directorio_datos: Path

    @classmethod
    def desde_entorno(cls) -> Ajustes:
        """Si defines SITEWISE_DATA_DIR uso esa carpeta; si no, la primera candidata que exista."""
        indicada = os.environ.get("SITEWISE_DATA_DIR")
        if indicada:
            return cls(Path(indicada))
        for candidata in CANDIDATAS:
            if Path(candidata).is_dir():
                return cls(Path(candidata))
        return cls(Path(CANDIDATAS[0]))  # no existe aún: la API avisará con un 503
