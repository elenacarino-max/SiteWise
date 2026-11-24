"""El repositorio que lee los datos de PostgreSQL en vez de los CSV.

Tiene exactamente la misma interfaz que `RepositorioCSV` (de hecho hereda de él): el motor y la API no
notan la diferencia. Lee las tres tablas una vez al arrancar y las consulta en memoria, igual que el
repositorio CSV, así que las respuestas siguen siendo inmediatas. La base de datos es el almacén; las
consultas espaciales con PostGIS (columna `geom`) quedan disponibles para lo que se añada después.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from sitewise.db.esquema import COLUMNAS, con_tiempo_limite, validar_esquema
from sitewise.db.repositorio import DatosNoDisponibles, RepositorioCSV


def _existe(cursor: Any, esquema: str, tabla: str) -> bool:
    cursor.execute("SELECT to_regclass(%s)", (f"{esquema}.{tabla}",))
    return cursor.fetchone()[0] is not None


def _tabla(cursor: Any, esquema: str, tabla: str) -> pd.DataFrame:
    """Leo una tabla entera como DataFrame, en el orden del CSV original, sin la columna `orden`."""
    columnas = ", ".join(COLUMNAS[tabla])
    cursor.execute(f"SELECT {columnas} FROM {esquema}.{tabla} ORDER BY orden")
    nombres = [c.name for c in cursor.description]
    return pd.DataFrame(cursor.fetchall(), columns=nombres)


class RepositorioPostgres(RepositorioCSV):
    origen = "postgresql"

    def __init__(self, url: str, esquema: str = "public"):
        try:
            import psycopg
        except ImportError as exc:
            raise DatosNoDisponibles(
                "Falta el paquete psycopg. Instálalo con: python -m pip install -e \".[db]\""
            ) from exc

        esquema = validar_esquema(esquema)
        try:
            with psycopg.connect(con_tiempo_limite(url)) as conexion, conexion.cursor() as cur:
                municipios = _tabla(cur, esquema, "municipios")
                indicadores = _tabla(cur, esquema, "indicadores")
                valores = _tabla(cur, esquema, "valores")
                # Los perfiles son opcionales: si la base no los tiene, la API funciona sin ellos.
                perfiles = None
                if _existe(cur, esquema, "perfiles_municipios") and _existe(cur, esquema, "perfiles_definicion"):
                    perfiles = (_tabla(cur, esquema, "perfiles_municipios"), _tabla(cur, esquema, "perfiles_definicion"))
        except psycopg.errors.UndefinedTable as exc:
            raise DatosNoDisponibles(
                f"La base de datos no tiene las tablas del dataset en el esquema '{esquema}'. "
                "Cárgalas con: python -m sitewise.db.cargador"
            ) from exc
        except psycopg.errors.UndefinedColumn as exc:
            raise DatosNoDisponibles(
                "Las tablas de la base de datos son de una versión anterior (faltan columnas). "
                "Vuelve a cargarlas con: python -m sitewise.db.cargador"
            ) from exc
        except psycopg.OperationalError as exc:
            raise DatosNoDisponibles(f"No puedo conectarme a la base de datos: {exc}") from exc

        if municipios.empty or valores.empty:
            raise DatosNoDisponibles(
                "La base de datos está vacía. Cárgala con: python -m sitewise.db.cargador"
            )
        self.esquema = esquema
        self._preparar(municipios, indicadores, valores)
        self._preparar_perfiles(*(perfiles or (None, None)))
