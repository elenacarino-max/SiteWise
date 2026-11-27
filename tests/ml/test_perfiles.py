"""Pruebas de los perfiles municipales (src/sitewise/ml/perfiles.py)."""

import numpy as np
import pandas as pd
import pytest

from sitewise.ml.perfiles import (
    PERFILES,
    PERFILES_V02,
    VERSION_V02,
    ordenar_clusters_por_indice,
    ordenar_clusters_por_poblacion,
    tabla_perfiles,
)


def test_hay_cinco_perfiles_con_nombre_y_descripcion():
    assert sorted(PERFILES) == [0, 1, 2, 3, 4]
    assert all(p["nombre"] and p["descripcion"] for p in PERFILES.values())
    assert len({p["nombre"] for p in PERFILES.values()}) == 5


def test_ordenar_deja_el_grupo_mas_grande_en_el_0():
    etiquetas = [2, 2, 0, 0, 1, 1]
    poblacion = [10, 20, 5000, 7000, 300, 500]
    nuevas = ordenar_clusters_por_poblacion(etiquetas, poblacion)
    assert nuevas.tolist() == [2, 2, 0, 0, 1, 1]


def test_ordenar_no_depende_de_la_numeracion_original():
    poblacion = [10, 20, 5000, 7000, 300, 500]
    a = ordenar_clusters_por_poblacion([2, 2, 0, 0, 1, 1], poblacion)
    b = ordenar_clusters_por_poblacion([0, 0, 1, 1, 2, 2], poblacion)
    assert a.tolist() == b.tolist() == [2, 2, 0, 0, 1, 1]


def test_ordenar_exige_misma_longitud():
    with pytest.raises(ValueError):
        ordenar_clusters_por_poblacion([0, 1], [1, 2, 3])


def test_tabla_perfiles_tiene_las_columnas_acordadas():
    t = tabla_perfiles(["28079", "01001"], [0, 4], es_atipico=[1, 0])
    assert list(t.columns) == ["cod_ine", "cluster", "cluster_perfil", "es_atipico", "version_modelo"]
    assert t.loc[0, "cluster_perfil"] == PERFILES[0]["nombre"]
    assert t["es_atipico"].tolist() == [1, 0]
    assert (t["version_modelo"] == "v01").all()


def test_tabla_perfiles_conserva_los_ceros_de_los_codigos():
    t = tabla_perfiles(["01001"], [3])
    assert t.loc[0, "cod_ine"] == "01001"
    assert isinstance(t.loc[0, "cod_ine"], str)


@pytest.mark.parametrize(
    "cod,cluster",
    [(["1001"], [0]), (["28079", "28079"], [0, 1]), (["28079"], [9])],
)
def test_tabla_perfiles_rechaza_datos_incorrectos(cod, cluster):
    with pytest.raises(ValueError):
        tabla_perfiles(cod, cluster)


def test_tabla_perfiles_rechaza_atipico_que_no_es_0_o_1():
    with pytest.raises(ValueError):
        tabla_perfiles(["28079"], [0], es_atipico=[2])


def test_resultado_es_un_dataframe_sin_huecos():
    t = tabla_perfiles(pd.Series(["28079", "08019"]), np.array([0, 1]))
    assert isinstance(t, pd.DataFrame)
    assert not t.isna().any().any()


# --- v02: logística + hídrica + conectividad, 4 grupos -------------------------------------------


def test_v02_tiene_cuatro_perfiles_con_nombre_y_descripcion():
    assert sorted(PERFILES_V02) == [0, 1, 2, 3]
    assert all(p["nombre"] and p["descripcion"] for p in PERFILES_V02.values())
    assert len({p["nombre"] for p in PERFILES_V02.values()}) == 4


def test_ordenar_por_indice_deja_la_mejor_logistica_en_el_0():
    etiquetas = [2, 2, 0, 0, 1, 1]
    logistica = [10, 20, 90, 80, 50, 60]
    nuevas = ordenar_clusters_por_indice(etiquetas, logistica)
    assert nuevas.tolist() == [2, 2, 0, 0, 1, 1]  # 0 -> 85, 1 -> 55, 2 -> 15


def test_ordenar_por_indice_exige_misma_longitud():
    with pytest.raises(ValueError):
        ordenar_clusters_por_indice([0, 1], [1.0])


def test_tabla_v02_usa_los_nombres_de_v02_y_su_version():
    t = tabla_perfiles(["01001", "01002", "01003"], [0, 3, 2], version=VERSION_V02)
    assert (t["version_modelo"] == "v02").all()
    assert t["cluster_perfil"].tolist() == [PERFILES_V02[0]["nombre"], PERFILES_V02[3]["nombre"], PERFILES_V02[2]["nombre"]]
    assert t["es_atipico"].tolist() == [0, 0, 0]


def test_tabla_v02_rechaza_el_grupo_4_que_solo_existe_en_v01():
    with pytest.raises(ValueError):
        tabla_perfiles(["01001"], [4], version=VERSION_V02)


def test_tabla_rechaza_una_version_desconocida():
    with pytest.raises(ValueError):
        tabla_perfiles(["01001"], [0], version="v99")
