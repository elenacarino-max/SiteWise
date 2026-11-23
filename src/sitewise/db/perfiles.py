"""Leo los perfiles de municipios que calcula Helen (clustering) y los dejo listos para el backend.

Son dos CSV de `data/reference/`:
  - perfiles_municipios_vNN.csv  una fila por municipio: cod_ine, cluster, cluster_perfil, es_atipico, version_modelo
  - perfiles_definicion_vNN.csv  una fila por perfil: nombre, descripción y medianas de cada variable

Un perfil NO es un riesgo ni una nota: solo describe a qué otros municipios se parece uno. Por eso
lo sirvo aparte de las notas y nunca lo mezclo con ellas.
No toco los ficheros de Helen: solo los leo. Si ella saca una versión nueva (v02), cojo la más alta.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

DIRECTORIO_POR_DEFECTO = Path("data/reference")
_VERSION = re.compile(r"_v(\d+)\.csv$")


def _ultima_version(directorio: Path, prefijo: str) -> Path | None:
    """El fichero `prefijo_vNN.csv` con el NN más alto (v10 va después de v9, no antes)."""
    candidatos = [
        (int(m.group(1)), f) for f in directorio.glob(f"{prefijo}_v*.csv") if (m := _VERSION.search(f.name))
    ]
    return max(candidatos, key=lambda c: c[0])[1] if candidatos else None


def buscar_ficheros(directorio: str | Path | None) -> tuple[Path | None, Path | None]:
    """(perfiles_municipios, perfiles_definicion) de la última versión, o (None, None) si no están."""
    if directorio is None or not Path(directorio).is_dir():
        return None, None
    directorio = Path(directorio)
    municipios = _ultima_version(directorio, "perfiles_municipios")
    definicion = _ultima_version(directorio, "perfiles_definicion")
    if municipios is None or definicion is None:
        return None, None
    return municipios, definicion


def leer_perfiles(directorio: str | Path | None) -> tuple[pd.DataFrame, pd.DataFrame] | None:
    """Leo los dos CSV con los tipos que necesita el backend. None si no están en la carpeta."""
    f_municipios, f_definicion = buscar_ficheros(directorio)
    if f_municipios is None or f_definicion is None:
        return None
    municipios = pd.read_csv(f_municipios, dtype={"cod_ine": str, "version_modelo": str})
    definicion = pd.read_csv(f_definicion, dtype={"version_modelo": str})
    # cod_ine siempre como texto de 5 dígitos (si no, "01001" pierde el cero inicial).
    municipios["cod_ine"] = municipios["cod_ine"].str.strip().str.zfill(5)
    return municipios, definicion
