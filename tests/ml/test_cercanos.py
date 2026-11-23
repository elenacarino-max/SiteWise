"""Pruebas de los municipios cercanos (src/sitewise/ml/cercanos.py)."""

import numpy as np
import pytest

from sitewise.ml.cercanos import N_CERCANOS, calcular_cercanos

CODIGOS = ["01001", "02002", "03003", "04004", "05005", "06006", "07007", "08008"]


def _coords(n=8):
    rng = np.random.default_rng(0)
    return rng.uniform(36, 44, size=n), rng.uniform(-9, 3, size=n)


def test_por_defecto_devuelve_n_cercanos_por_municipio():
    lat, lon = _coords()
    t = calcular_cercanos(lat, lon, CODIGOS)
    assert N_CERCANOS == 5
    assert len(t) == len(CODIGOS) * N_CERCANOS
    assert (t.groupby("cod_ine").size() == N_CERCANOS).all()


def test_el_numero_de_cercanos_se_puede_cambiar():
    lat, lon = _coords()
    t = calcular_cercanos(lat, lon, CODIGOS, n=2)
    assert (t.groupby("cod_ine").size() == 2).all()
    assert t["posicion"].max() == 2


def test_un_municipio_nunca_es_cercano_a_si_mismo():
    lat, lon = _coords()
    t = calcular_cercanos(lat, lon, CODIGOS)
    assert (t["cod_ine"] != t["cod_ine_cercano"]).all()


def test_devuelve_el_mas_cercano():
    lat, lon = [40.0, 40.1, 40.3, 45.0], [0.0, 0.0, 0.0, 0.0]
    t = calcular_cercanos(lat, lon, CODIGOS[:4], n=1)
    cercano = dict(zip(t["cod_ine"], t["cod_ine_cercano"]))
    assert cercano["01001"] == "02002"
    assert cercano["03003"] == "02002"
    assert cercano["04004"] == "03003"


def test_distancia_en_km_un_grado_de_latitud():
    t = calcular_cercanos([0.0, 1.0], [0.0, 0.0], CODIGOS[:2], n=1)
    assert t["distancia_km"].iloc[0] == pytest.approx(111.195, abs=0.01)


def test_un_grado_de_longitud_mide_menos_lejos_del_ecuador():
    t = calcular_cercanos([60.0, 60.0], [0.0, 1.0], CODIGOS[:2], n=1)
    assert t["distancia_km"].iloc[0] == pytest.approx(55.598, abs=0.01)


def test_las_posiciones_van_ordenadas_por_distancia():
    lat, lon = _coords()
    t = calcular_cercanos(lat, lon, CODIGOS)
    for _, grupo in t.groupby("cod_ine"):
        assert grupo["posicion"].tolist() == list(range(1, N_CERCANOS + 1))
        assert grupo["distancia_km"].is_monotonic_increasing


def test_municipios_con_las_mismas_coordenadas_no_se_devuelven_a_si_mismos():
    lat, lon = [40.0, 40.0, 40.0, 41.0], [-3.0, -3.0, -3.0, -3.0]
    t = calcular_cercanos(lat, lon, CODIGOS[:4], n=2)
    assert (t["cod_ine"] != t["cod_ine_cercano"]).all()
    assert (t.groupby("cod_ine").size() == 2).all()


def test_conserva_los_ceros_de_los_codigos_y_las_columnas():
    lat, lon = _coords()
    t = calcular_cercanos(lat, lon, CODIGOS)
    assert list(t.columns) == ["cod_ine", "cod_ine_cercano", "posicion", "distancia_km"]
    assert t["cod_ine"].iloc[0] == "01001"
    assert isinstance(t["cod_ine_cercano"].iloc[0], str)


def test_es_reproducible():
    lat, lon = _coords()
    a = calcular_cercanos(lat, lon, CODIGOS)
    b = calcular_cercanos(lat, lon, CODIGOS)
    assert a.equals(b)


@pytest.mark.parametrize(
    "codigos,n",
    [
        (["1001"] + CODIGOS[1:], 5),  # código de 4 dígitos
        (["01001"] * 2 + CODIGOS[2:], 5),  # repetido
        (CODIGOS, 0),  # n demasiado pequeño
        (CODIGOS, 8),  # n no puede ser todos los municipios
        (CODIGOS[:-1], 5),  # distinta longitud
        ([None] + CODIGOS[1:], 5),  # código vacío
    ],
)
def test_rechaza_datos_incorrectos(codigos, n):
    lat, lon = _coords()
    with pytest.raises(ValueError):
        calcular_cercanos(lat, lon, codigos, n=n)


def test_rechaza_coordenadas_vacias():
    lat, lon = _coords()
    lat[0] = np.nan
    with pytest.raises(ValueError):
        calcular_cercanos(lat, lon, CODIGOS)


def test_rechaza_coordenadas_fuera_de_rango():
    lat, lon = _coords()
    lat[0] = 95.0
    with pytest.raises(ValueError):
        calcular_cercanos(lat, lon, CODIGOS)


def test_rechaza_lat_y_lon_de_distinta_longitud():
    lat, lon = _coords()
    with pytest.raises(ValueError):
        calcular_cercanos(lat[:-1], lon, CODIGOS)
