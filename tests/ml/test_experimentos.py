"""Pruebas de los experimentos de K-Means (src/sitewise/ml/experimentos.py)."""

import numpy as np
import pandas as pd
import pytest

from sitewise.ml.experimentos import barrido_k, estabilidad, matriz_entrada, metricas_kmeans


def _tres_nubes(n=60, semilla=0):
    rng = np.random.default_rng(semilla)
    centros = np.array([[10.0, 10.0], [50.0, 50.0], [90.0, 10.0]])
    return np.vstack([c + rng.normal(0, 2, size=(n, 2)) for c in centros])


def test_matriz_entrada_deja_fuera_los_municipios_con_huecos():
    d = pd.DataFrame({"a": [1.0, 2.0, np.nan], "b": [4.0, np.nan, 6.0], "c": [7.0, 8.0, 9.0]})
    X, mascara = matriz_entrada(d, ["a", "c"])
    assert mascara.tolist() == [True, True, False] and X.shape == (2, 2)


def test_metricas_con_tres_nubes_separadas_dan_silhouette_alto():
    m = metricas_kmeans(_tres_nubes(), 3, n_init=5)
    assert m["silhouette"] > 0.8 and m["davies_bouldin"] < 0.5
    assert m["grupo_menor_pct"] == pytest.approx(100 / 3)


def test_el_barrido_tiene_una_fila_por_k_y_la_mejor_es_la_de_tres_nubes():
    t = barrido_k(_tres_nubes(), ks=range(2, 6), n_init=5)
    assert list(t.index) == [2, 3, 4, 5]
    assert t["silhouette"].idxmax() == 3
    assert t["inercia"].is_monotonic_decreasing


def test_k_invalido_da_error():
    with pytest.raises(ValueError):
        metricas_kmeans(_tres_nubes(), 1)


def test_estabilidad_alta_con_grupos_claros():
    e = estabilidad(_tres_nubes(), 3, semillas=(42, 1, 2), n_init=5)
    assert e["ari_minimo"] > 0.99 and e["ari_medio"] >= e["ari_minimo"]


def test_estabilidad_exige_dos_semillas():
    with pytest.raises(ValueError):
        estabilidad(_tres_nubes(), 3, semillas=(42,))
