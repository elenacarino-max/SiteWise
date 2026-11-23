"""Cargo los CSV del dataset en PostgreSQL.

Uso, desde la raíz del repo (con la base de datos arrancada):
    python -m sitewise.db.cargador --datos data/processed/sitewise_v03

Cada carga BORRA y vuelve a crear las tres tablas: el dataset se sustituye entero por versión,
así que cargar dos veces da el mismo resultado (no duplica filas). Se hace en una sola
transacción: si algo falla, la base se queda como estaba.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

from sitewise.db.esquema import (
    COLUMNAS,
    ENTERAS,
    NUMERICAS,
    OBLIGATORIAS,
    con_tiempo_limite,
    ddl,
    ddl_perfiles,
    url_desde_entorno,
    validar_esquema,
)
from sitewise.db.perfiles import DIRECTORIO_POR_DEFECTO, buscar_ficheros
from sitewise.db.repositorio import FICHEROS, DatosNoDisponibles, fichero_valores

CANDIDATAS = ("data/processed/sitewise_v03", "data/processed/sidewise_v03")


class ErrorCarga(RuntimeError):
    """Lo lanzo cuando los CSV no se pueden cargar (columnas que faltan, claves que no cruzan...)."""


def _leer(directorio: Path, tabla: str, fichero: Path | None = None) -> tuple[pd.DataFrame, list[str]]:
    """Leo un CSV como texto, me quedo con las columnas del esquema y devuelvo las que sobran."""
    if fichero is None:
        fichero = fichero_valores(directorio) if tabla == "valores" else directorio / f"{tabla}.csv"
    df = pd.read_csv(fichero, dtype=str, keep_default_na=False)
    faltan = [c for c in OBLIGATORIAS[tabla] if c not in df.columns]
    if faltan:
        raise ErrorCarga(f"{fichero.name} no tiene la(s) columna(s) obligatoria(s): {', '.join(faltan)}.")
    ignoradas = [c for c in df.columns if c not in COLUMNAS[tabla]]
    presentes = [c for c in COLUMNAS[tabla] if c in df.columns]
    df = df[presentes].copy()

    if "cod_ine" in df.columns:
        df["cod_ine"] = df["cod_ine"].str.strip().str.zfill(5)  # conserva el cero inicial
    for columna in NUMERICAS[tabla]:
        if columna in df.columns:
            # Un campo vacío o un texto que no es número acaba en NULL, igual que en el repositorio CSV.
            df[columna] = pd.to_numeric(df[columna], errors="coerce")
    for columna in ENTERAS[tabla]:
        if columna in df.columns:
            df[columna] = df[columna].round().astype("Int64")
    df["orden"] = range(len(df))  # posición en el fichero
    return df, ignoradas


def _copiar(cursor: Any, esquema: str, tabla: str, df: pd.DataFrame) -> None:
    """Inserto el DataFrame con COPY, que es mucho más rápido que fila a fila."""
    columnas = ", ".join(df.columns)
    texto = df.to_csv(index=False, header=False, na_rep="")  # vacío sin comillas = NULL en COPY
    with cursor.copy(f"COPY {esquema}.{tabla} ({columnas}) FROM STDIN WITH (FORMAT csv)") as copia:
        copia.write(texto)


def _activar_postgis(conexion: Any, esquema: str) -> bool:
    """Si la base tiene PostGIS, añado una columna geográfica a municipios. Si no, no pasa nada.

    La columna `geom` permite consultas espaciales ("municipios a menos de X km"). Las columnas
    `lat` y `lon` se conservan siempre: el resto del backend solo usa esas.
    """
    import psycopg

    with conexion.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_available_extensions WHERE name = 'postgis'")
        if cur.fetchone() is None:
            return False
    try:
        with conexion.transaction(), conexion.cursor() as cur:  # si falla, se deshace solo esto
            cur.execute("CREATE EXTENSION IF NOT EXISTS postgis")
            cur.execute(f"SET LOCAL search_path TO {esquema}, public")
            cur.execute("ALTER TABLE municipios ADD COLUMN geom geography(Point, 4326)")
            cur.execute(
                "UPDATE municipios SET geom = ST_SetSRID(ST_MakePoint(lon, lat), 4326)::geography "
                "WHERE lon IS NOT NULL AND lat IS NOT NULL"
            )
            cur.execute("CREATE INDEX municipios_geom_idx ON municipios USING GIST (geom)")
        return True
    except psycopg.Error:  # sin permisos para crear la extensión, etc.: sigo sin PostGIS
        return False


def cargar_csv(
    directorio: str | Path,
    url: str,
    esquema: str = "public",
    directorio_perfiles: str | Path | None = None,
) -> dict[str, Any]:
    """Carga los tres CSV en la base y devuelve un resumen (filas cargadas, columnas ignoradas, PostGIS).

    Si en `directorio_perfiles` están los CSV de perfiles de Helen, también carga sus dos tablas
    (en la misma transacción). Si no están, la carga sigue igual y la base se queda sin perfiles.
    """
    import psycopg  # import perezoso: solo hace falta si se usa PostgreSQL

    esquema = validar_esquema(esquema)
    directorio = Path(directorio)
    faltan = [f for f in FICHEROS if not (directorio / f).is_file()]
    if not fichero_valores(directorio).is_file():
        faltan.append("valores_app.csv o valores.csv")
    if faltan:
        raise DatosNoDisponibles(f"No encuentro {', '.join(faltan)} en '{directorio}'.")

    tablas, ignoradas = {}, {}
    for tabla in ("municipios", "indicadores", "valores"):
        tablas[tabla], ignoradas[tabla] = _leer(directorio, tabla)

    f_perfiles, f_definicion = buscar_ficheros(directorio_perfiles)
    con_perfiles = f_perfiles is not None
    if con_perfiles:
        tablas["perfiles_definicion"], ignoradas["perfiles_definicion"] = _leer(directorio, "perfiles_definicion", f_definicion)
        tablas["perfiles_municipios"], ignoradas["perfiles_municipios"] = _leer(directorio, "perfiles_municipios", f_perfiles)

    try:
        with psycopg.connect(con_tiempo_limite(url), autocommit=False) as conexion:
            codificacion = conexion.execute("SHOW server_encoding").fetchone()[0]
            if codificacion != "UTF8":
                # Con otra codificación se rompen las tildes y las eñes (Álava, Peñíscola...).
                raise ErrorCarga(
                    f"La base de datos usa la codificación {codificacion} y necesito UTF8. "
                    "Créala con ENCODING 'UTF8' (la imagen oficial de PostgreSQL ya lo hace así)."
                )
            with conexion.cursor() as cur:
                cur.execute(
                    f"DROP TABLE IF EXISTS {esquema}.perfiles_municipios, {esquema}.perfiles_definicion, "
                    f"{esquema}.valores, {esquema}.indicadores, {esquema}.municipios"
                )
                cur.execute(ddl(esquema))
                orden = ["municipios", "indicadores", "valores"]
                if con_perfiles:
                    cur.execute(ddl_perfiles(esquema))
                    orden += ["perfiles_definicion", "perfiles_municipios"]  # la definición va antes: la referencian
                try:
                    for tabla in orden:  # este orden respeta las claves foráneas
                        _copiar(cur, esquema, tabla, tablas[tabla])
                except psycopg.errors.ForeignKeyViolation as exc:
                    raise ErrorCarga(
                        f"Hay valores que apuntan a un municipio o indicador que no existe: {exc.diag.message_detail}"
                    ) from exc
                except psycopg.errors.UniqueViolation as exc:
                    raise ErrorCarga(f"Hay filas duplicadas: {exc.diag.message_detail}") from exc
            postgis = _activar_postgis(conexion, esquema)
    except psycopg.OperationalError as exc:
        raise DatosNoDisponibles(f"No puedo conectarme a la base de datos: {exc}") from exc

    return {
        "municipios": len(tablas["municipios"]),
        "indicadores": len(tablas["indicadores"]),
        "valores": len(tablas["valores"]),
        "columnas_ignoradas": {t: c for t, c in ignoradas.items() if c},
        "postgis": postgis,
        "perfiles": len(tablas["perfiles_municipios"]) if con_perfiles else None,
    }


def _directorio_por_defecto() -> str:
    return next((c for c in CANDIDATAS if Path(c).is_dir()), CANDIDATAS[0])


def main() -> None:
    parser = argparse.ArgumentParser(description="Carga los CSV del dataset en PostgreSQL.")
    parser.add_argument("--datos", default=_directorio_por_defecto(), help="carpeta con los tres CSV")
    parser.add_argument("--url", default=None, help="dirección de la base (por defecto, SITEWISE_DATABASE_URL o POSTGRES_*)")
    parser.add_argument(
        "--perfiles", default=str(DIRECTORIO_POR_DEFECTO),
        help="carpeta con los CSV de perfiles de Helen (si no están, no se cargan)",
    )
    parser.add_argument("--esquema", default="public", help="esquema donde crear las tablas")
    args = parser.parse_args()

    try:
        resumen = cargar_csv(args.datos, args.url or url_desde_entorno(), args.esquema, args.perfiles)
    except (ErrorCarga, DatosNoDisponibles, ValueError) as exc:
        raise SystemExit(f"Error: {exc}") from exc

    print(f"Cargado en el esquema '{args.esquema}':")
    print(f"  municipios  {resumen['municipios']:>8}")
    print(f"  indicadores {resumen['indicadores']:>8}")
    print(f"  valores     {resumen['valores']:>8}")
    if resumen["perfiles"] is None:
        print("  perfiles    no cargados (no encuentro los CSV de perfiles en la carpeta indicada)")
    else:
        print(f"  perfiles    {resumen['perfiles']:>8}")
    print(f"  PostGIS: {'activado (columna geom)' if resumen['postgis'] else 'no disponible (se usan lat y lon)'}")
    for tabla, columnas in resumen["columnas_ignoradas"].items():
        print(f"  Aviso: {tabla}.csv tiene columnas que no guardo: {', '.join(columnas)}")


if __name__ == "__main__":
    main()
