"""Perfiles municipales de SiteWise: nombres de los grupos y fichero ``cod_ine → perfil``.

K-Means numera los grupos al azar (el grupo "0" de una ejecución puede ser el "3" de otra).
Para que el número sea estable, se reordenan siempre con un criterio fijo:

- **v01** (5 grupos, referencia): por la mediana de población, de mayor a menor.
- **v02** (4 grupos, rediseño tras la revisión técnica): por el índice de logística, de mayor a
  menor; el grupo 0 es el de mejor logística.

Cada versión tiene su propio diccionario de perfiles (``PERFILES`` para v01, ``PERFILES_V02``) y
``tabla_perfiles`` valida contra el de la versión indicada.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

VERSION_MODELO = "v01"  # versión por defecto de ``tabla_perfiles`` (la v01 sigue siendo reproducible)
VERSION_V02 = "v02"

# Nombres y descripciones de los 5 perfiles (K=5), identificados por el número fijo del grupo.
# Las cifras de la descripción son medianas de cada grupo (ver notebooks/07_perfiles_municipios.ipynb para v02; v01 está en el historial de Git, commit bc30250).
PERFILES: dict[int, dict[str, str]] = {
    0: {
        "nombre": "Municipios industriales y urbanos",
        "descripcion": (
            "Los municipios más grandes (mediana de unos 11.700 habitantes; incluye desde pueblos "
            "grandes hasta las mayores ciudades), casi todos con suelo industrial cartografiado y "
            "muy cerca de autovía y de terminal ferroviaria de mercancías."
        ),
    },
    1: {
        "nombre": "Pueblos con acuíferos en mal estado",
        "descripcion": (
            "Pueblos de alrededor de 1.000 habitantes cuyo territorio se asienta sobre masas de "
            "agua subterránea en mal estado cuantitativo (mediana del 100 %)."
        ),
    },
    2: {
        "nombre": "Pueblos bien conectados",
        "descripcion": (
            "Pueblos de unos 900 habitantes, cerca de autovía (unos 5 km), con poco suelo "
            "industrial y una tasa de paro por debajo de la mediana."
        ),
    },
    3: {
        "nombre": "Rural aislado con más paro",
        "descripcion": (
            "Municipios pequeños (mediana de unos 330 habitantes), lejos de autovía y de terminal "
            "ferroviaria, sin suelo industrial y con la tasa de paro más alta."
        ),
    },
    4: {
        "nombre": "Rural aislado con menos paro y más viento",
        "descripcion": (
            "Los municipios más pequeños (mediana de unos 175 habitantes), lejos de autovía y de "
            "terminal ferroviaria, con la tasa de paro más baja y el viento medio más alto."
        ),
    },
}


# v02: perfil = logística + hídrica + conectividad, K-Means con K=4 sobre tres índices 0-100
# (ver notebooks/07_perfiles_municipios.ipynb). Los nombres son PROVISIONALES: los cierra Gema.
PERFILES_V02: dict[int, dict[str, str]] = {
    0: {
        "nombre": "Buena logística y buena conectividad",
        "descripcion": (
            "Municipios con buena logística (suelo industrial, autovía y terminal cercanos), "
            "buena conectividad digital y presión hídrica moderada."
        ),
    },
    1: {
        "nombre": "Logística media-buena con mucha presión hídrica",
        "descripcion": (
            "Municipios con logística media-buena y buena conectividad, pero con estrés hídrico "
            "alto y acuíferos en mal estado."
        ),
    },
    2: {
        "nombre": "Logística baja y mal conectados",
        "descripcion": "Municipios con poca logística y conectividad digital baja: zonas aisladas.",
    },
    3: {
        "nombre": "Logística baja pero bien conectados",
        "descripcion": "Municipios con poca logística pero buena conectividad digital (fibra y 5G).",
    },
}

PERFILES_POR_VERSION: dict[str, dict[int, dict[str, str]]] = {
    VERSION_MODELO: PERFILES,
    VERSION_V02: PERFILES_V02,
}


def ordenar_clusters_por_poblacion(etiquetas, poblacion) -> np.ndarray:
    """Renumera los grupos: 0 = mayor mediana de población, el último = la menor.

    ``etiquetas`` son las que devuelve K-Means (arbitrarias) y ``poblacion`` la población de cada
    municipio, en el mismo orden. Devuelve un array con los números nuevos.
    """
    etiquetas = np.asarray(etiquetas)
    poblacion = np.asarray(poblacion, dtype=float)
    if etiquetas.shape != poblacion.shape:
        raise ValueError("etiquetas y poblacion deben tener la misma longitud.")
    medianas = pd.Series(poblacion).groupby(etiquetas).median().sort_values(ascending=False)
    # Desempate estable: si dos grupos tuvieran la misma mediana, manda el número original.
    orden = sorted(medianas.index, key=lambda g: (-medianas[g], g))
    nuevo = {viejo: i for i, viejo in enumerate(orden)}
    return np.array([nuevo[g] for g in etiquetas])


def ordenar_clusters_por_indice(etiquetas, indice) -> np.ndarray:
    """Renumera los grupos: 0 = mayor media del ``indice``, el último = la menor (criterio de v02).

    ``etiquetas`` son las de K-Means (arbitrarias) e ``indice`` el valor de cada municipio (por
    ejemplo el índice de logística), en el mismo orden. Se usa la media porque los índices son
    percentiles 0-100 sin valores extremos.
    """
    etiquetas = np.asarray(etiquetas)
    indice = np.asarray(indice, dtype=float)
    if etiquetas.shape != indice.shape:
        raise ValueError("etiquetas e indice deben tener la misma longitud.")
    medias = pd.Series(indice).groupby(etiquetas).mean()
    orden = sorted(medias.index, key=lambda g: (-medias[g], g))
    nuevo = {viejo: i for i, viejo in enumerate(orden)}
    return np.array([nuevo[g] for g in etiquetas])


def tabla_perfiles(cod_ine, cluster, es_atipico=None, version: str = VERSION_MODELO) -> pd.DataFrame:
    """Fichero ``cod_ine → perfil`` para la API y el RAG.

    Columnas: ``cod_ine`` (texto de 5 dígitos), ``cluster`` (número del grupo), ``cluster_perfil``
    (nombre), ``es_atipico`` (0 o 1) y ``version_modelo``. Los grupos válidos son los de la
    ``version`` indicada (v01: 0 a 4; v02: 0 a 3).
    """
    if version not in PERFILES_POR_VERSION:
        raise ValueError(f"Versión sin perfiles definidos: {version!r}. Disponibles: {sorted(PERFILES_POR_VERSION)}")
    perfiles = PERFILES_POR_VERSION[version]
    cod_ine = pd.Series(cod_ine, dtype="string").reset_index(drop=True)
    cluster = pd.Series(cluster).reset_index(drop=True).astype(int)
    if len(cod_ine) != len(cluster):
        raise ValueError("cod_ine y cluster deben tener la misma longitud.")
    if not cod_ine.str.fullmatch(r"\d{5}").all():
        raise ValueError("Todos los cod_ine deben ser texto de 5 dígitos.")
    if cod_ine.duplicated().any():
        raise ValueError("Hay cod_ine repetidos.")
    desconocidos = set(cluster.unique()) - set(perfiles)
    if desconocidos:
        raise ValueError(f"Grupos sin perfil definido: {sorted(desconocidos)}")
    if es_atipico is None:
        atipico = pd.Series(0, index=range(len(cod_ine)))
    else:
        atipico = pd.Series(es_atipico).reset_index(drop=True).astype(int)
        if len(atipico) != len(cod_ine) or not set(atipico.unique()) <= {0, 1}:
            raise ValueError("es_atipico debe ser 0 o 1 y tener la misma longitud.")
    return pd.DataFrame(
        {
            "cod_ine": cod_ine.astype(str),
            "cluster": cluster,
            "cluster_perfil": cluster.map(lambda c: perfiles[c]["nombre"]),
            "es_atipico": atipico,
            "version_modelo": version,
        }
    )
