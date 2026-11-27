"""Experimentos de K-Means para el perfil de municipio (v02).

Funciones que usan los notebooks 05 (explorar) y 06 (registrar en MLflow), para que el cálculo de las
métricas esté escrito una sola vez.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import (
    adjusted_rand_score,
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)

SEMILLA = 42
N_INIT = 20
MUESTRA_SILHOUETTE = 5000


def matriz_entrada(datos: pd.DataFrame, columnas: list[str]) -> tuple[np.ndarray, pd.Series]:
    """Matriz de los municipios con TODAS las ``columnas`` y la máscara de los que entran."""
    mascara = datos[columnas].notna().all(axis=1)
    return datos.loc[mascara, columnas].to_numpy(dtype=float), mascara


def metricas_kmeans(X: np.ndarray, k: int, semilla: int = SEMILLA, n_init: int = N_INIT) -> dict[str, float]:
    """Ajusta K-Means y devuelve inercia, silhouette, Davies-Bouldin, Calinski-Harabasz y el grupo menor (%).

    El silhouette se calcula sobre una muestra fija de hasta 5.000 municipios, para que sea rápido y repetible.
    Solo se pueden comparar silhouettes de **la misma matriz de entrada**.
    """
    if k < 2 or k >= len(X):
        raise ValueError("k debe estar entre 2 y el número de municipios menos 1.")
    km = KMeans(n_clusters=k, n_init=n_init, random_state=semilla).fit(X)
    return {
        "inercia": float(km.inertia_),
        "silhouette": float(silhouette_score(X, km.labels_, sample_size=min(MUESTRA_SILHOUETTE, len(X)), random_state=0)),
        "davies_bouldin": float(davies_bouldin_score(X, km.labels_)),
        "calinski_harabasz": float(calinski_harabasz_score(X, km.labels_)),
        "grupo_menor_pct": float(np.bincount(km.labels_).min() / len(X) * 100),
    }


def barrido_k(X: np.ndarray, ks=range(2, 9), semilla: int = SEMILLA, n_init: int = N_INIT) -> pd.DataFrame:
    """Una fila por K con las métricas de ``metricas_kmeans``."""
    filas = [{"k": k, **metricas_kmeans(X, k, semilla, n_init)} for k in ks]
    return pd.DataFrame(filas).set_index("k")


def estabilidad(X: np.ndarray, k: int, semillas=(42, 1, 2, 3, 4), n_init: int = N_INIT) -> dict[str, float]:
    """ARI (1 = grupos idénticos) entre el ajuste con la primera semilla y los de las demás."""
    semillas = list(semillas)
    if len(semillas) < 2:
        raise ValueError("Hacen falta al menos dos semillas.")
    referencia = KMeans(n_clusters=k, n_init=n_init, random_state=semillas[0]).fit_predict(X)
    aris = [
        adjusted_rand_score(referencia, KMeans(n_clusters=k, n_init=n_init, random_state=s).fit_predict(X))
        for s in semillas[1:]
    ]
    return {"ari_medio": float(np.mean(aris)), "ari_minimo": float(np.min(aris))}
