"""Pipeline de agrupación de municipios (K-Means con PCA) de SiteWise.

Reproduce, con scikit-learn, lo que hace el generador de matrices
(``data/processed/generadorMatrices/generar_matriz.py``) pero con una diferencia clave:
**todo se aprende solo con los municipios de entrenamiento** (``fit``) y después se aplica
igual a municipios nuevos o de validación (``transform`` / ``predict``).

Pasos, en este orden:
    1. Imputación de huecos (según la regla de cada variable).
    2. Transformación (``log1p`` o ninguna).
    3. Recorte de extremos (percentiles aprendidos en entrenamiento).
    4. Escalado estándar.
    5. PCA (por defecto, componentes necesarios para explicar el 85 % de la varianza).
    6. K-Means (K=5, ``n_init=20``, semilla 42).

Uso básico::

    from sitewise.ml.pipeline import construir_pipeline, VARIABLES

    modelo = construir_pipeline()
    modelo.fit(entrenamiento[list(VARIABLES)])
    grupos = modelo.predict(nuevos[list(VARIABLES)])
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import PCA
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

K_POR_DEFECTO = 5
SEMILLA = 42
VARIANZA_PCA = 0.85
RECORTE_P1_P99 = (0.01, 0.99)


@dataclass(frozen=True)
class Variable:
    """Cómo se prepara cada variable antes de agrupar."""

    ausentes: str = "error"  # error | maximo | mediana | media
    transformacion: str = "ninguna"  # ninguna | log1p
    recorte: tuple[float, float] | None = None  # percentiles (sobre el valor ya transformado)


# Las 7 variables acordadas. El agua usa la estimación con los 5 municipios vecinos
# (columna ``agua_vecinos_pct``), por eso aquí no admite huecos.
VARIABLES: dict[str, Variable] = {
    "poblacion_2025": Variable("error", "log1p", RECORTE_P1_P99),
    "suelo_industrial_cartografiado_pct": Variable("error", "log1p", RECORTE_P1_P99),
    "dist_recta_eje_autovia_km": Variable("maximo", "log1p", RECORTE_P1_P99),
    "dist_recta_ttm_km": Variable("maximo", "log1p", RECORTE_P1_P99),
    "paro_por_100_hab": Variable("error", "ninguna", RECORTE_P1_P99),
    "viento_100m_media_m_s": Variable("mediana", "ninguna", None),
    "agua_vecinos_pct": Variable("error", "ninguna", None),
}


class Imputador(BaseEstimator, TransformerMixin):
    """Rellena huecos con un valor aprendido en entrenamiento (máximo, mediana o media)."""

    def __init__(self, metodo: str = "error"):
        self.metodo = metodo

    def fit(self, X, y=None):
        X = np.asarray(X, dtype=float)
        if self.metodo == "error":
            self.relleno_ = None
        elif self.metodo in ("maximo", "mediana", "media"):
            funcion = {"maximo": np.nanmax, "mediana": np.nanmedian, "media": np.nanmean}[self.metodo]
            self.relleno_ = float(funcion(X))
            if not np.isfinite(self.relleno_):
                raise ValueError("No se puede calcular un relleno válido con los datos de entrenamiento.")
        else:
            raise ValueError(f"Método de imputación desconocido: {self.metodo!r}")
        return self

    def transform(self, X):
        X = np.asarray(X, dtype=float).copy()
        hay = np.isnan(X)
        if hay.any():
            if self.relleno_ is None:
                raise ValueError(f"Hay {int(hay.sum())} huecos y esta variable no admite ninguno.")
            X[hay] = self.relleno_
        return X


class Recortador(BaseEstimator, TransformerMixin):
    """Recorta los extremos a los percentiles calculados SOLO con el entrenamiento."""

    def __init__(self, percentiles: tuple[float, float] = RECORTE_P1_P99):
        self.percentiles = percentiles

    def fit(self, X, y=None):
        X = np.asarray(X, dtype=float)
        self.minimo_, self.maximo_ = np.quantile(X, self.percentiles)
        return self

    def transform(self, X):
        return np.clip(np.asarray(X, dtype=float), self.minimo_, self.maximo_)


def _preparar_variable(spec: Variable) -> Pipeline:
    pasos: list[tuple[str, object]] = [("imputar", Imputador(spec.ausentes))]
    if spec.transformacion == "log1p":
        pasos.append(("log1p", _Log1p()))
    elif spec.transformacion != "ninguna":
        raise ValueError(f"Transformación desconocida: {spec.transformacion!r}")
    if spec.recorte is not None:
        pasos.append(("recortar", Recortador(spec.recorte)))
    return Pipeline(pasos)


class _Log1p(BaseEstimator, TransformerMixin):
    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X = np.asarray(X, dtype=float)
        if (X <= -1).any():
            raise ValueError("log1p requiere valores mayores que -1.")
        return np.log1p(X)


def construir_preprocesado(variables: dict[str, Variable] | None = None) -> ColumnTransformer:
    """Imputación → transformación → recorte, variable a variable."""
    variables = VARIABLES if variables is None else variables
    return ColumnTransformer(
        [(nombre, _preparar_variable(spec), [nombre]) for nombre, spec in variables.items()],
        verbose_feature_names_out=False,
    )


def construir_pipeline(
    k: int = K_POR_DEFECTO,
    varianza_pca: float | None = VARIANZA_PCA,
    variables: dict[str, Variable] | None = None,
    semilla: int = SEMILLA,
) -> Pipeline:
    """Pipeline completo. Con ``varianza_pca=None`` se agrupa sin PCA."""
    pasos: list[tuple[str, object]] = [
        ("preparar", construir_preprocesado(variables)),
        ("escalar", StandardScaler()),
    ]
    if varianza_pca is not None:
        pasos.append(("pca", PCA(n_components=varianza_pca, svd_solver="full")))
    pasos.append(("kmeans", KMeans(n_clusters=k, n_init=20, random_state=semilla)))
    return Pipeline(pasos)


def estimar_agua_vecinos(
    municipios: pd.DataFrame,
    columna: str = "agua_subterranea_mal_estado_cuantitativo_pct",
    k_vecinos: int = 5,
) -> pd.DataFrame:
    """Devuelve ``agua_vecinos_pct`` y ``agua_origen`` (observado / estimado_vecinos).

    Los municipios sin dato de agua reciben la media de los ``k_vecinos`` municipios con dato
    más cercanos (distancia haversine sobre ``lat`` y ``lon``). Los que sí tienen dato conservan
    el suyo. ``municipios`` debe incluir ``lat``, ``lon`` y ``columna``.
    """
    from sklearn.neighbors import BallTree

    d = municipios.copy()
    tiene = d[columna].notna().to_numpy()
    d["agua_vecinos_pct"] = d[columna]
    d["agua_origen"] = np.where(tiene, "observado", "estimado_vecinos")
    if tiene.all():
        return d
    if tiene.sum() < k_vecinos:
        raise ValueError("Hay menos municipios con dato que vecinos pedidos.")
    coords = np.radians(d[["lat", "lon"]].to_numpy(dtype=float))
    arbol = BallTree(coords[tiene], metric="haversine")
    _, idx = arbol.query(coords[~tiene], k=k_vecinos)
    d.loc[~tiene, "agua_vecinos_pct"] = d.loc[tiene, columna].to_numpy()[idx].mean(axis=1)
    return d
