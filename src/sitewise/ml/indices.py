"""Índices del perfil de municipio (v02): logística, hídrica y conectividad.

Todo el cálculo vive aquí, en un solo sitio, y lo usan los notebooks 05 (K-Means), 06 (MLflow),
07 (perfiles) y 08 (estimaciones para la app). Así no se repite ni puede diferir entre notebooks.

Reglas (acordadas el 27 nov 2026):
- Cada índice es una media de percentiles 0-100 (rango medio; las distancias van invertidas, de modo
  que 100 siempre es "mejor" en logística y conectividad y "más presión" en hídrica).
- Hídrica = estrés hídrico + mal estado cuantitativo de acuíferos. Los huecos de esos dos indicadores se
  estiman con la media de los 5 municipios más cercanos con dato, y se marcan como estimados.
- Logística y conectividad NO se imputan: si falta un componente, el índice queda vacío.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

VECINOS = 5
RADIO_TIERRA_KM = 6371.0
COL_ESTRES = "estres_hidrico_pct"
COL_ACUIFERO = "agua_subterranea_mal_estado_cuantitativo_pct"
PREFIJO_LOGISTICA = "dimension_logistica__"
PREFIJO_CONECTIVIDAD = "alternativa_conectividad__"
INDICES = ["idx_logistica", "idx_hidrica", "idx_conectividad"]


def pct_rango_medio(observados: pd.Series, valores: pd.Series) -> pd.Series:
    """Percentil ``100 * (rango - 0.5) / n`` de ``valores`` respecto a la distribución de ``observados``.

    ``n`` es el número de municipios con dato observado. Los empates reciben el rango medio. Los
    valores vacíos siguen vacíos.
    """
    ref = np.sort(observados.dropna().to_numpy(dtype=float))
    if len(ref) == 0:
        raise ValueError("No hay valores observados para calcular el percentil.")
    v = valores.to_numpy(dtype=float)
    izq = np.searchsorted(ref, v, side="left")
    der = np.searchsorted(ref, v, side="right")
    rango = (izq + der + 1) / 2
    return pd.Series(100 * (rango - 0.5) / len(ref), index=valores.index).where(valores.notna())


def _vecinos(datos: pd.DataFrame, columna: str, vecinos: int):
    """Valor completo, marca de estimado y distancias media y máxima (km) a los vecinos usados."""
    tiene = datos[columna].notna().to_numpy()
    if not tiene.any():
        raise ValueError(f"'{columna}' no tiene ningún valor observado.")
    coords = np.radians(datos[["lat", "lon"]].to_numpy(dtype=float))
    k = min(vecinos, int(tiene.sum()))
    arbol = BallTree(coords[tiene], metric="haversine")
    valores = datos.loc[tiene, columna].to_numpy(dtype=float)
    falta = np.where(~tiene)[0]
    completo = datos[columna].astype(float).copy()
    media = pd.Series(np.nan, index=datos.index)
    maxima = pd.Series(np.nan, index=datos.index)
    if len(falta):
        dist, idx = arbol.query(coords[falta], k=k)
        completo.iloc[falta] = valores[idx].mean(axis=1)
        media.iloc[falta] = dist.mean(axis=1) * RADIO_TIERRA_KM
        maxima.iloc[falta] = dist.max(axis=1) * RADIO_TIERRA_KM
    return completo, pd.Series(~tiene, index=datos.index), media, maxima


def estimar_con_vecinos(
    datos: pd.DataFrame, columna: str, vecinos: int = VECINOS
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Rellena los huecos de ``columna`` con la media de los municipios más cercanos con dato.

    Devuelve ``(valor completo, marca de estimado, distancia media a los vecinos usados en km)``.
    Necesita las columnas ``lat`` y ``lon`` (grados). La distancia es en línea recta (haversine).
    """
    completo, estimado, media, _ = _vecinos(datos, columna, vecinos)
    return completo, estimado, media


def tabla_estimaciones_vecinos(datos: pd.DataFrame, columna: str = COL_ACUIFERO, vecinos: int = VECINOS) -> pd.DataFrame:
    """Una fila por municipio con hueco: el valor estimado, sus vecinos y el método (para la app).

    Es el formato de ``agua_estimada_vecinos_v01.csv``, que lee el notebook 09.
    """
    completo, estimado, media, maxima = _vecinos(datos, columna, vecinos)
    return pd.DataFrame(
        {
            "cod_ine": datos.loc[estimado, "cod_ine"].to_numpy(),
            "valor_estimado_pct": completo[estimado].round(2).to_numpy(),
            "k_vecinos": vecinos,
            "distancia_media_km": media[estimado].round(1).to_numpy(),
            "distancia_maxima_km": maxima[estimado].round(1).to_numpy(),
            "estado_propuesto": "aproximado",
            "metodo": (
                f"Media del indicador en los {vecinos} municipios con dato más cercanos "
                "(distancia entre coordenadas). Solo para municipios sin masa catalogada."
            ),
        }
    )


def construir_indices(datos: pd.DataFrame, componentes: pd.DataFrame, vecinos: int = VECINOS) -> pd.DataFrame:
    """Los tres índices del perfil, alineados con las filas de ``datos``.

    ``datos`` es el dataset municipal (``cod_ine``, ``lat``, ``lon``, estrés hídrico y acuífero) y
    ``componentes`` la tabla de percentiles del notebook 03B. Se unen por código INE como número, porque
    en un fichero tiene cero inicial y en el otro no.

    Columnas devueltas: ``idx_logistica``, ``idx_hidrica``, ``idx_conectividad``,
    ``acuifero_estimado_vecinos``, ``estres_hidrico_estimado_vecinos``, ``dist_vecinos_acuifero_km`` y
    ``dist_vecinos_estres_km``.
    """
    if datos["cod_ine"].duplicated().any():
        raise ValueError("Hay cod_ine repetidos en el dataset.")
    comp = componentes.copy()
    comp["_k"] = comp["cod_ine"].astype(int)
    if comp["_k"].duplicated().any():
        raise ValueError("Hay cod_ine repetidos en los componentes.")
    comp = comp.set_index("_k")
    alineado = comp.reindex(datos["cod_ine"].astype(int).to_numpy())
    alineado.index = datos.index

    log_cols = [c for c in comp.columns if c.startswith(PREFIJO_LOGISTICA)]
    con_cols = [c for c in comp.columns if c.startswith(PREFIJO_CONECTIVIDAD)]
    if len(log_cols) != 3 or len(con_cols) != 2:
        raise ValueError(f"Se esperaban 3 componentes de logística y 2 de conectividad: {log_cols}, {con_cols}")

    estres, est_estres, dist_estres = estimar_con_vecinos(datos, COL_ESTRES, vecinos)
    acuifero, est_acuifero, dist_acuifero = estimar_con_vecinos(datos, COL_ACUIFERO, vecinos)
    hidrica = (pct_rango_medio(datos[COL_ESTRES], estres) + pct_rango_medio(datos[COL_ACUIFERO], acuifero)) / 2

    return pd.DataFrame(
        {
            "idx_logistica": alineado[log_cols].mean(axis=1, skipna=False),
            "idx_hidrica": hidrica,
            "idx_conectividad": alineado[con_cols].mean(axis=1, skipna=False),
            "acuifero_estimado_vecinos": est_acuifero,
            "estres_hidrico_estimado_vecinos": est_estres,
            "dist_vecinos_acuifero_km": dist_acuifero,
            "dist_vecinos_estres_km": dist_estres,
        },
        index=datos.index,
    )
