"""Pruebas de los índices del perfil v02 (src/sitewise/ml/indices.py)."""

import numpy as np
import pandas as pd
import pytest

from sitewise.ml.indices import (
    COL_ACUIFERO,
    COL_ESTRES,
    construir_indices,
    estimar_con_vecinos,
    pct_rango_medio,
    tabla_estimaciones_vecinos,
)


def test_percentil_de_rango_medio_con_cuatro_valores():
    obs = pd.Series([10.0, 20.0, 30.0, 40.0])
    p = pct_rango_medio(obs, obs)
    assert p.round(1).tolist() == [12.5, 37.5, 62.5, 87.5]


def test_percentil_reparte_los_empates_con_el_rango_medio():
    obs = pd.Series([5.0, 5.0, 9.0, 9.0])
    p = pct_rango_medio(obs, obs)
    assert p.round(1).tolist() == [25.0, 25.0, 75.0, 75.0]


def test_percentil_deja_vacios_los_huecos_y_mide_contra_los_observados():
    obs = pd.Series([1.0, 2.0, 3.0, 4.0, np.nan])
    p = pct_rango_medio(obs, pd.Series([2.5, np.nan]))
    assert p.iloc[0] == pytest.approx(50.0) and np.isnan(p.iloc[1])


def test_percentil_sin_observados_da_error():
    with pytest.raises(ValueError):
        pct_rango_medio(pd.Series([np.nan]), pd.Series([1.0]))


def _mapa():
    # Tres municipios pegados (0, 1, 2) y uno muy lejos (3); el 2 no tiene dato.
    return pd.DataFrame(
        {
            "cod_ine": ["01001", "01002", "01003", "02001"],
            "lat": [40.0, 40.1, 40.05, 37.0],
            "lon": [-3.0, -3.0, -3.0, -5.0],
            "x": [10.0, 30.0, np.nan, 100.0],
        }
    )


def test_estimar_usa_la_media_de_los_vecinos_con_dato_y_marca_el_hueco():
    completo, estimado, dist = estimar_con_vecinos(_mapa(), "x", vecinos=2)
    assert estimado.tolist() == [False, False, True, False]
    # Los dos más cercanos al municipio 2 son el 0 y el 1 (10 y 30) -> media 20.
    assert completo.iloc[2] == pytest.approx(20.0)
    assert completo.iloc[[0, 1, 3]].tolist() == [10.0, 30.0, 100.0]
    assert 0 < dist.iloc[2] < 20 and dist.iloc[[0, 1, 3]].isna().all()


def test_estimar_no_pide_mas_vecinos_de_los_que_hay():
    completo, _, _ = estimar_con_vecinos(_mapa(), "x", vecinos=5)
    assert completo.iloc[2] == pytest.approx((10 + 30 + 100) / 3)


def test_estimar_sin_ningun_dato_da_error():
    d = _mapa().assign(x=np.nan)
    with pytest.raises(ValueError):
        estimar_con_vecinos(d, "x")


def _dataset_y_componentes():
    d = pd.DataFrame(
        {
            "cod_ine": ["01001", "01002", "01003", "01004"],
            "lat": [40.0, 40.1, 40.2, 40.3],
            "lon": [-3.0, -3.0, -3.0, -3.0],
            COL_ESTRES: [10.0, 20.0, 30.0, np.nan],
            COL_ACUIFERO: [0.0, 50.0, 100.0, 100.0],
        }
    )
    c = pd.DataFrame(
        {
            "cod_ine": [1001, 1002, 1003, 1004],  # sin el cero inicial, como el fichero real
            "dimension_logistica__a": [100.0, 50.0, 0.0, np.nan],
            "dimension_logistica__b": [100.0, 50.0, 0.0, 10.0],
            "dimension_logistica__c": [100.0, 50.0, 0.0, 10.0],
            "alternativa_conectividad__f": [80.0, 60.0, 40.0, 20.0],
            "alternativa_conectividad__g": [100.0, 80.0, 60.0, 40.0],
        }
    )
    return d, c


def test_construir_indices_une_por_codigo_y_calcula_las_medias():
    d, c = _dataset_y_componentes()
    r = construir_indices(d, c, vecinos=2)
    assert r["idx_logistica"].iloc[:3].tolist() == [100.0, 50.0, 0.0]
    assert r["idx_conectividad"].tolist() == [90.0, 70.0, 50.0, 30.0]
    assert not r["idx_hidrica"].isna().any()
    assert r["estres_hidrico_estimado_vecinos"].tolist() == [False, False, False, True]
    assert not r["acuifero_estimado_vecinos"].any()


def test_construir_indices_no_imputa_la_logistica():
    d, c = _dataset_y_componentes()
    r = construir_indices(d, c, vecinos=2)
    assert np.isnan(r["idx_logistica"].iloc[3])  # le falta un componente


def test_construir_indices_rechaza_codigos_repetidos():
    d, c = _dataset_y_componentes()
    d.loc[1, "cod_ine"] = "01001"
    with pytest.raises(ValueError):
        construir_indices(d, c)


def test_construir_indices_exige_los_componentes_esperados():
    d, c = _dataset_y_componentes()
    with pytest.raises(ValueError):
        construir_indices(d, c.drop(columns=["alternativa_conectividad__g"]))


def test_tabla_estimaciones_tiene_el_formato_que_lee_el_notebook_09():
    t = tabla_estimaciones_vecinos(_mapa().rename(columns={"x": COL_ACUIFERO}), vecinos=2)
    assert list(t.columns) == [
        "cod_ine", "valor_estimado_pct", "k_vecinos", "distancia_media_km",
        "distancia_maxima_km", "estado_propuesto", "metodo",
    ]
    assert t["cod_ine"].tolist() == ["01003"] and t["valor_estimado_pct"].tolist() == [20.0]
    assert t["distancia_maxima_km"].iloc[0] >= t["distancia_media_km"].iloc[0]
    assert t["estado_propuesto"].eq("aproximado").all() and t["k_vecinos"].eq(2).all()
