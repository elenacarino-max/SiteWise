"""Leo los perfiles de municipios que calcula Helen (clustering) y los dejo listos para el backend.

Son dos CSV de `data/reference/`:
  - perfiles_municipios_vNN.csv  una fila por municipio: cod_ine, cluster, cluster_perfil, es_atipico, version_modelo
  - perfiles_definicion_vNN.csv  una fila por perfil: nombre, descripción y medianas de cada variable

Un perfil NO es un riesgo ni una nota: solo describe a qué otros municipios se parece uno. Por eso
lo sirvo aparte de las notas y nunca lo mezclo con ellas.
No toco los ficheros de Helen: solo los leo. Si ella saca una versión nueva (v02), cojo la más alta que tengan los dos ficheros.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

DIRECTORIO_POR_DEFECTO = Path("data/reference")
_VERSION = re.compile(r"_v(\d+)\.csv$")


class ErrorPerfiles(Exception):
    """Los ficheros de perfiles no son coherentes entre sí (por ejemplo, de versiones distintas)."""


def _versiones(directorio: Path, prefijo: str) -> dict[int, Path]:
    """Los ficheros `prefijo_vNN.csv` de la carpeta, por número de versión."""
    return {
        int(m.group(1)): f for f in directorio.glob(f"{prefijo}_v*.csv") if (m := _VERSION.search(f.name))
    }


def buscar_ficheros(directorio: str | Path | None) -> tuple[Path | None, Path | None]:
    """(perfiles_municipios, perfiles_definicion) de UNA misma versión, o (None, None) si no hay perfiles.

    Elijo la versión más alta que tengan los DOS ficheros, para no mezclar municipios de una versión
    con definiciones de otra. Si hay ficheros pero ninguna versión está completa, doy error en vez de
    seguir sin perfiles en silencio.
    """
    if directorio is None or not Path(directorio).is_dir():
        return None, None
    directorio = Path(directorio)
    municipios = _versiones(directorio, "perfiles_municipios")
    definicion = _versiones(directorio, "perfiles_definicion")
    if not municipios and not definicion:
        return None, None
    comunes = municipios.keys() & definicion.keys()
    if not comunes:
        raise ErrorPerfiles(
            f"En '{directorio}' hay ficheros de perfiles pero ninguna versión tiene los dos "
            f"(perfiles_municipios: {sorted(municipios) or 'ninguna'}, "
            f"perfiles_definicion: {sorted(definicion) or 'ninguna'})."
        )
    version = max(comunes)
    return municipios[version], definicion[version]


def leer_perfiles(directorio: str | Path | None) -> tuple[pd.DataFrame, pd.DataFrame] | None:
    """Leo los dos CSV con los tipos que necesita el backend. None si no están en la carpeta."""
    f_municipios, f_definicion = buscar_ficheros(directorio)
    if f_municipios is None or f_definicion is None:
        return None
    municipios = pd.read_csv(f_municipios, dtype={"cod_ine": str, "version_modelo": str})
    definicion = pd.read_csv(f_definicion, dtype={"version_modelo": str})
    versiones = set(municipios["version_modelo"].dropna()) | set(definicion["version_modelo"].dropna())
    if len(versiones) > 1:
        raise ErrorPerfiles(f"Los perfiles mezclan versiones del modelo: {sorted(versiones)}.")
    # cod_ine siempre como texto de 5 dígitos (si no, "01001" pierde el cero inicial).
    municipios["cod_ine"] = municipios["cod_ine"].str.strip().str.zfill(5)
    return municipios, definicion


def buscar_cercanos(directorio: str | Path | None) -> Path | None:
    """El `municipios_cercanos_vNN.csv` de versión más alta, o None si no hay ninguno."""
    if directorio is None or not Path(directorio).is_dir():
        return None
    versiones = _versiones(Path(directorio), "municipios_cercanos")
    return versiones[max(versiones)] if versiones else None


def leer_cercanos(directorio: str | Path | None) -> pd.DataFrame | None:
    """Los 5 municipios más próximos de cada municipio (calculados por Helen). None si no está el CSV."""
    fichero = buscar_cercanos(directorio)
    if fichero is None:
        return None
    df = pd.read_csv(fichero, dtype={"cod_ine": str, "cod_ine_cercano": str})
    for columna in ("cod_ine", "cod_ine_cercano"):
        df[columna] = df[columna].str.strip().str.zfill(5)
    return df
