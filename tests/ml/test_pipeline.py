"""Pruebas del pipeline de agrupación (src/sitewise/ml/pipeline.py)."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from sitewise.ml.pipeline import (
    VARIABLES,
    Imputador,
    Recortador,
    construir_pipeline,
    estimar_agua_vecinos,
)

COLUMNAS = list(VARIABLES)


def datos_sinteticos(n=300, semilla=0):
    rng = np.random.default_rng(semilla)
    return pd.DataFrame(
        {
            "poblacion_2025": rng.lognormal(7, 1.5, n).round(),
            "suelo_industrial_cartografiado_pct": rng.gamma(1.0, 2.0, n),
            "dist_recta_eje_autovia_km": rng.gamma(2.0, 8.0, n),
            "dist_recta_ttm_km": rng.gamma(2.0, 20.0, n),
            "paro_por_100_hab": rng.normal(8, 2, n).clip(0.5),
            "viento_100m_media_m_s": rng.normal(5, 1, n),
            "agua_vecinos_pct": rng.uniform(0, 100, n),
        }
    )


def test_imputador_usa_valor_de_entrenamiento():
    imp = Imputador("maximo").fit(np.array([[1.0], [5.0], [np.nan]]))
    resultado = imp.transform(np.array([[np.nan], [2.0]]))
    assert resultado.ravel().tolist() == [5.0, 2.0]


def test_imputador_error_no_admite_huecos():
    imp = Imputador("error").fit(np.array([[1.0], [2.0]]))
    with pytest.raises(ValueError):
        imp.transform(np.array([[np.nan]]))


def test_recortador_aprende_limites_solo_del_entrenamiento():
    entrenamiento = np.arange(101, dtype=float).reshape(-1, 1)
    rec = Recortador((0.01, 0.99)).fit(entrenamiento)
    fuera = rec.transform(np.array([[-1000.0], [1000.0]]))
    assert fuera.ravel().tolist() == [1.0, 99.0]


def test_pipeline_devuelve_cinco_grupos_y_es_reproducible():
    d = datos_sinteticos()
    a = construir_pipeline().fit(d).predict(d)
    b = construir_pipeline().fit(d).predict(d)
    assert set(a) <= set(range(5))
    assert len(set(a)) == 5
    assert (a == b).all()


def test_pca_explica_al_menos_85_por_ciento():
    modelo = construir_pipeline().fit(datos_sinteticos())
    assert modelo.named_steps["pca"].explained_variance_ratio_.sum() >= 0.85


def test_sin_pca_se_puede_construir():
    d = datos_sinteticos()
    modelo = construir_pipeline(varianza_pca=None).fit(d)
    assert "pca" not in modelo.named_steps
    assert len(modelo.predict(d)) == len(d)


def test_municipios_nuevos_no_cambian_lo_aprendido():
    d = datos_sinteticos()
    entrenamiento, nuevos = d.iloc[:250], d.iloc[250:].copy()
    nuevos.loc[nuevos.index[0], "poblacion_2025"] = 1e12  # valor extremo
    modelo = construir_pipeline().fit(entrenamiento)
    centros_antes = modelo.named_steps["kmeans"].cluster_centers_.copy()
    grupos = modelo.predict(nuevos)
    assert len(grupos) == len(nuevos)
    assert np.array_equal(centros_antes, modelo.named_steps["kmeans"].cluster_centers_)


def test_huecos_de_distancia_y_viento_se_rellenan_con_entrenamiento():
    d = datos_sinteticos()
    modelo = construir_pipeline().fit(d)
    nuevo = d.iloc[:3].copy()
    nuevo.loc[nuevo.index[0], "dist_recta_eje_autovia_km"] = np.nan
    nuevo.loc[nuevo.index[1], "viento_100m_media_m_s"] = np.nan
    assert len(modelo.predict(nuevo)) == 3


def test_hueco_en_variable_sin_regla_da_error():
    d = datos_sinteticos()
    modelo = construir_pipeline().fit(d)
    nuevo = d.iloc[:2].copy()
    nuevo.loc[nuevo.index[0], "paro_por_100_hab"] = np.nan
    with pytest.raises(ValueError):
        modelo.predict(nuevo)


def test_agua_vecinos_usa_la_media_de_los_mas_cercanos():
    d = pd.DataFrame(
        {
            "lat": [40.0, 40.01, 40.02, 40.03, 40.04, 40.05, 43.0],
            "lon": [-3.0] * 7,
            "agua": [10.0, 20.0, 30.0, 40.0, 50.0, np.nan, np.nan],
        }
    )
    r = estimar_agua_vecinos(d, columna="agua", k_vecinos=5)
    assert r.loc[5, "agua_vecinos_pct"] == pytest.approx(30.0)  # media de los 5 con dato
    assert r.loc[5, "agua_origen"] == "estimado_vecinos"
    assert r.loc[0, "agua_origen"] == "observado"
    assert r.loc[0, "agua_vecinos_pct"] == 10.0


# --- Prueba con datos reales: solo si existen en local (data/processed no está en git) ---

RAIZ = Path(__file__).resolve().parents[2]
CSV = RAIZ / "data/processed/sitewise_ml/dataset_municipal_tasa_paro.csv"
MATRICES = sorted((RAIZ / "data/processed/sitewise_ml/mlflow_matrices_2").glob("empleo_viento_agua_vecinos_*/matriz_pca.csv"))


@pytest.mark.skipif(not CSV.exists() or not MATRICES, reason="datos locales no disponibles")
def test_reproduce_los_grupos_del_notebook_08():
    from sklearn.cluster import KMeans
    from sklearn.metrics import adjusted_rand_score

    datos = pd.read_csv(CSV, dtype={"cod_ine": str}).set_index("cod_ine")
    pca_generador = pd.read_csv(MATRICES[0], dtype={"cod_ine": str}).set_index("cod_ine")
    datos = datos.loc[pca_generador.index]
    esperado = KMeans(n_clusters=5, n_init=20, random_state=42).fit_predict(pca_generador.to_numpy())
    obtenido = construir_pipeline().fit(datos[COLUMNAS]).predict(datos[COLUMNAS])
    assert adjusted_rand_score(esperado, obtenido) > 0.99
