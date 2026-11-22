"""El esquema de PostgreSQL: las tablas, sus columnas y cómo me conecto.

Las tres tablas son las del diccionario del dataset (docs/data/DICCIONARIO_DATASET.md):
municipios, indicadores y valores (formato largo). Las columnas están en UN solo sitio (aquí) y las
usan el cargador y el repositorio, para que nunca se desincronicen.
"""

from __future__ import annotations

import os
import re
from urllib.parse import quote

# Columnas de cada tabla, en el orden en que las leo y las escribo. Además cada tabla guarda `orden`
# (la posición de la fila en el CSV), para devolver los datos en el mismo orden que el fichero.
COLUMNAS = {
    "municipios": (
        "cod_ine", "nombre", "cod_provincia", "provincia", "ccaa",
        "superficie_km2", "lat", "lon", "anio_geometria",
    ),
    "indicadores": (
        "id_indicador", "nombre", "bloque", "tipo", "unidad", "sentido", "fuente_id", "fuente",
        "url", "fecha_dato", "nivel_origen", "metodo", "naturaleza", "limitaciones",
    ),
    "valores": (
        "cod_ine", "id_indicador", "valor", "estado", "nivel_origen", "fecha_dato", "fuente_id",
        "naturaleza", "metodo", "url_fuente", "fuentes_adicionales",
    ),
}
# Columnas sin las que una fila no tiene sentido: si faltan en el CSV, el cargador se detiene.
OBLIGATORIAS = {
    "municipios": ("cod_ine", "nombre"),
    "indicadores": ("id_indicador",),
    "valores": ("cod_ine", "id_indicador"),
}
# Las que deben guardarse como número (el resto son texto).
NUMERICAS = {
    "municipios": ("superficie_km2", "lat", "lon", "anio_geometria"),
    "indicadores": (),
    "valores": ("valor",),
}

_NOMBRE_VALIDO = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")


def validar_esquema(nombre: str) -> str:
    """El nombre del esquema se mete en SQL como texto, así que solo admito nombres simples."""
    if not _NOMBRE_VALIDO.match(nombre):
        raise ValueError(f"Nombre de esquema no válido: {nombre!r} (minúsculas, números y guion bajo).")
    return nombre


def ddl(esquema: str) -> str:
    """Las sentencias que crean las tres tablas desde cero."""
    esquema = validar_esquema(esquema)
    return f"""
CREATE SCHEMA IF NOT EXISTS {esquema};

CREATE TABLE {esquema}.municipios (
    cod_ine          text PRIMARY KEY CHECK (cod_ine ~ '^[0-9]{{5}}$'),
    nombre           text NOT NULL,
    cod_provincia    text,
    provincia        text,
    ccaa             text,
    superficie_km2   double precision,
    lat              double precision,
    lon              double precision,
    anio_geometria   integer,
    orden            integer NOT NULL
);

CREATE TABLE {esquema}.indicadores (
    id_indicador     text PRIMARY KEY,
    nombre           text,
    bloque           text,
    tipo             text,
    unidad           text,
    sentido          text,
    fuente_id        text,
    fuente           text,
    url              text,
    fecha_dato       text,
    nivel_origen     text,
    metodo           text,
    naturaleza       text,
    limitaciones     text,
    orden            integer NOT NULL
);

-- Una fila por municipio e indicador. `valor` es NULL cuando falta el dato (nunca 0):
-- `estado` explica por qué.
CREATE TABLE {esquema}.valores (
    cod_ine              text NOT NULL REFERENCES {esquema}.municipios (cod_ine),
    id_indicador         text NOT NULL REFERENCES {esquema}.indicadores (id_indicador),
    valor                double precision,
    estado               text,
    nivel_origen         text,
    fecha_dato           text,
    fuente_id            text,
    naturaleza           text,
    metodo               text,
    url_fuente           text,
    fuentes_adicionales  text,
    orden                integer NOT NULL,
    PRIMARY KEY (cod_ine, id_indicador)
);

CREATE INDEX valores_indicador_idx ON {esquema}.valores (id_indicador);
"""


def con_tiempo_limite(url: str, segundos: int = 10) -> str:
    """Añado un tiempo máximo de espera a la conexión, salvo que la dirección ya lo traiga.

    Sin él, si la base está apagada o el puerto no responde, la API puede quedarse esperando mucho
    (en Windows, más de un minuto) en vez de avisar con un error claro.
    """
    if "connect_timeout" in url:
        return url
    if "://" in url:
        return url + ("&" if "?" in url else "?") + f"connect_timeout={segundos}"
    return f"{url} connect_timeout={segundos}"  # formato "host=... dbname=..."


def url_desde_entorno() -> str:
    """La dirección de la base de datos.

    1. SITEWISE_DATABASE_URL, por ejemplo: postgresql://sitewise:CLAVE@127.0.0.1:5432/sitewise
    2. Si no existe, la monto con las mismas variables que usa docker-compose.yml (POSTGRES_*).
    """
    url = os.environ.get("SITEWISE_DATABASE_URL")
    if url:
        return url
    clave = os.environ.get("POSTGRES_PASSWORD")
    if not clave:
        raise ValueError(
            "No sé a qué base de datos conectarme. Define SITEWISE_DATABASE_URL "
            "(postgresql://usuario:clave@127.0.0.1:5432/sitewise) o POSTGRES_PASSWORD."
        )
    usuario = os.environ.get("POSTGRES_USER", "sitewise")
    base = os.environ.get("POSTGRES_DB", "sitewise")
    puerto = os.environ.get("POSTGRES_PORT", "5432")
    return f"postgresql://{quote(usuario)}:{quote(clave)}@127.0.0.1:{puerto}/{quote(base)}"
