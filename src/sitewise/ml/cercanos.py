"""Municipios cercanos de SiteWise: para cada municipio, los más próximos en el mapa.

"Cercano" quiere decir **próximo geográficamente**: distancia en línea recta entre los puntos
(``lat``, ``lon``) de los municipios. Sirve para hablar del agua y de los riesgos naturales (sequía,
incendios, inundaciones), que dependen del territorio. No tiene nada que ver con que dos municipios
se parezcan en población, paro u otras características.

Para cambiar cuántos cercanos se devuelven por municipio, basta con cambiar ``N_CERCANOS``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

# Cuántos municipios cercanos se guardan por municipio. Es el único sitio donde hay que cambiarlo.
N_CERCANOS = 5

# Radio medio de la Tierra (km): pasa la distancia haversine (en radianes) a kilómetros.
RADIO_TIERRA_KM = 6371.0088


def calcular_cercanos(lat, lon, cod_ine, n: int = N_CERCANOS) -> pd.DataFrame:
    """Devuelve los ``n`` municipios más cercanos a cada uno (sin incluirse a sí mismo).

    ``lat`` y ``lon`` son las coordenadas en grados de cada municipio y ``cod_ine`` sus códigos INE,
    todo en el mismo orden. La distancia es en línea recta sobre la esfera (haversine). El resultado
    está en formato largo, ordenado por ``cod_ine`` y ``posicion``: ``cod_ine``, ``cod_ine_cercano``,
    ``posicion`` (1 = el más cercano) y ``distancia_km``.
    """
    lat = np.asarray(lat, dtype=float)
    lon = np.asarray(lon, dtype=float)
    cod_ine = pd.Series(cod_ine, dtype="string").reset_index(drop=True)
    if lat.ndim != 1 or lon.ndim != 1 or not len(lat) == len(lon) == len(cod_ine):
        raise ValueError("lat, lon y cod_ine deben ser listas de la misma longitud (un valor por municipio).")
    if cod_ine.isna().any() or not cod_ine.str.fullmatch(r"\d{5}").all():
        raise ValueError("Todos los cod_ine deben ser texto de 5 dígitos.")
    if cod_ine.duplicated().any():
        raise ValueError("Hay cod_ine repetidos.")
    if not (np.isfinite(lat).all() and np.isfinite(lon).all()):
        raise ValueError("lat y lon no pueden tener valores vacíos.")
    if (np.abs(lat) > 90).any() or (np.abs(lon) > 180).any():
        raise ValueError("lat debe estar entre -90 y 90, y lon entre -180 y 180.")
    if not 1 <= n < len(cod_ine):
        raise ValueError("n debe ser al menos 1 y menor que el número de municipios.")

    coords = np.radians(np.column_stack([lat, lon]))
    distancias, posiciones = BallTree(coords, metric="haversine").query(coords, k=n + 1)

    # Cada municipio sale como su propio vecino más cercano (distancia 0). Se quita. Si hay municipios
    # con las mismas coordenadas, el propio puede no ir el primero, así que se busca por posición.
    propio = posiciones == np.arange(len(cod_ine))[:, None]
    conservar = ~propio
    conservar[~propio.any(axis=1), -1] = False  # el propio no ha salido: se descarta el último
    cercanos = posiciones[conservar].reshape(-1, n)
    dist_km = distancias[conservar].reshape(-1, n) * RADIO_TIERRA_KM

    codigos = cod_ine.to_numpy(dtype=str)
    largo = pd.DataFrame(
        {
            "cod_ine": np.repeat(codigos, n),
            "cod_ine_cercano": codigos[cercanos.ravel()],
            "distancia_km": np.round(dist_km.ravel(), 3),
        }
    )
    # Orden fijo también ante empates: primero por distancia y después por código.
    largo = largo.sort_values(["cod_ine", "distancia_km", "cod_ine_cercano"], kind="mergesort").reset_index(drop=True)
    largo["posicion"] = largo.groupby("cod_ine").cumcount() + 1
    return largo[["cod_ine", "cod_ine_cercano", "posicion", "distancia_km"]]
