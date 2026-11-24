"""Ajustes de la API: de dónde leo los datos. Se pueden cambiar con variables de entorno."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from sitewise.db.perfiles import DIRECTORIO_POR_DEFECTO as PERFILES_POR_DEFECTO

# El diccionario del dataset escribe a veces "sidewise" (con d) por una errata.
# Pruebo las dos carpetas y me quedo con la primera que exista.
CANDIDATAS = ("data/processed/sitewise_v03", "data/processed/sidewise_v03")


# Las reglas por actividad (pesos y mínimos) las aprueba el equipo; yo solo leo el fichero.
REGLAS_POR_DEFECTO = Path("configs/actividades/reglas_actividad.csv")


@dataclass(frozen=True)
class Ajustes:
    directorio_datos: Path
    ruta_reglas: Path = REGLAS_POR_DEFECTO
    # Si defino la dirección de la base de datos, leo de PostgreSQL; si no, de los CSV.
    url_base_datos: str | None = None
    esquema_base_datos: str = "public"
    # Carpeta con los CSV de perfiles de Helen (solo con CSV; con PostgreSQL salen de la base de datos).
    # Aquí es None (sin perfiles); `desde_entorno` pone data/reference si no se indica otra.
    directorio_perfiles: Path | None = None

    @classmethod
    def desde_entorno(cls) -> Ajustes:
        """Cada ruta se puede cambiar con una variable de entorno.

        SITEWISE_DATA_DIR  -> carpeta de los CSV de datos
        SITEWISE_REGLAS    -> CSV de reglas por actividad
        SITEWISE_DATABASE_URL -> (opcional) si la defino, leo los datos de PostgreSQL en vez de los CSV
        SITEWISE_DB_SCHEMA    -> (opcional) esquema de PostgreSQL, por defecto "public"
        SITEWISE_PERFILES_DIR -> (opcional) carpeta con los CSV de perfiles, por defecto data/reference
        Si no las defino, uso las rutas por defecto (la primera carpeta de datos que exista).
        """
        reglas = Path(os.environ.get("SITEWISE_REGLAS") or REGLAS_POR_DEFECTO)
        base = {
            "url_base_datos": os.environ.get("SITEWISE_DATABASE_URL") or None,
            "esquema_base_datos": os.environ.get("SITEWISE_DB_SCHEMA") or "public",
            "directorio_perfiles": Path(os.environ.get("SITEWISE_PERFILES_DIR") or PERFILES_POR_DEFECTO),
        }
        indicada = os.environ.get("SITEWISE_DATA_DIR")
        if indicada:
            return cls(Path(indicada), reglas, **base)
        for candidata in CANDIDATAS:
            if Path(candidata).is_dir():
                return cls(Path(candidata), reglas, **base)
        return cls(Path(CANDIDATAS[0]), reglas, **base)  # no existe aún: la API avisará con un 503
