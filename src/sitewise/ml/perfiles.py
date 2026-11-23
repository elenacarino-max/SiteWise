"""Perfiles municipales de SiteWise: nombres de los 5 grupos y fichero ``cod_ine → perfil``.

K-Means numera los grupos al azar (el grupo "0" de una ejecución puede ser el "3" de otra).
Para que el número sea estable, se reordenan por la **mediana de población, de mayor a menor**:
el grupo 0 es siempre el de municipios más grandes y el 4 el de los más pequeños.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

VERSION_MODELO = "v01"

# Nombres y descripciones de los 5 perfiles (K=5), identificados por el número fijo del grupo.
# Las cifras de la descripción son medianas de cada grupo (ver notebooks/10_perfiles_municipios.ipynb).
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


def tabla_perfiles(cod_ine, cluster, es_atipico=None, version: str = VERSION_MODELO) -> pd.DataFrame:
    """Fichero ``cod_ine → perfil`` para la API y el RAG.

    Columnas: ``cod_ine`` (texto de 5 dígitos), ``cluster`` (0 a 4), ``cluster_perfil`` (nombre),
    ``es_atipico`` (0 o 1) y ``version_modelo``.
    """
    cod_ine = pd.Series(cod_ine, dtype="string").reset_index(drop=True)
    cluster = pd.Series(cluster).reset_index(drop=True).astype(int)
    if len(cod_ine) != len(cluster):
        raise ValueError("cod_ine y cluster deben tener la misma longitud.")
    if not cod_ine.str.fullmatch(r"\d{5}").all():
        raise ValueError("Todos los cod_ine deben ser texto de 5 dígitos.")
    if cod_ine.duplicated().any():
        raise ValueError("Hay cod_ine repetidos.")
    desconocidos = set(cluster.unique()) - set(PERFILES)
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
            "cluster_perfil": cluster.map(lambda c: PERFILES[c]["nombre"]),
            "es_atipico": atipico,
            "version_modelo": version,
        }
    )
