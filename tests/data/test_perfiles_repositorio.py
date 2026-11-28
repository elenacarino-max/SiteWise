"""Pruebas de los perfiles de municipios (clustering de Helen) en el repositorio CSV."""

import pytest

from sitewise.db.perfiles import ErrorPerfiles, buscar_ficheros, leer_perfiles
from sitewise.db.repositorio import DatosNoDisponibles, RepositorioCSV


def test_sin_carpeta_de_perfiles_no_hay_perfiles(directorio_datos):
    repo = RepositorioCSV(directorio_datos)
    assert repo.perfil("28001") is None
    assert repo.definiciones_perfiles() == []
    assert repo.similares("28001") == (0, [])
    assert repo.info()["perfiles_version"] is None


def test_perfil_de_un_municipio(directorio_datos, directorio_perfiles):
    repo = RepositorioCSV(directorio_datos, directorio_perfiles)
    perfil = repo.perfil("41001")
    assert perfil["cluster"] == 1
    assert perfil["nombre"] == "Perfil de prueba B"
    assert perfil["es_atipico"] is True
    assert perfil["version_modelo"] == "v01"
    assert perfil["descripcion"] == "Otra descripción de prueba."
    assert repo.perfil("99999") is None
    assert repo.info()["perfiles_version"] == "v01"


def test_el_codigo_conserva_el_cero_inicial(directorio_datos, directorio_perfiles):
    assert RepositorioCSV(directorio_datos, directorio_perfiles).perfil("01001")["cluster"] == 0


def test_definiciones_con_medianas_y_descripcion_con_comas(directorio_datos, directorio_perfiles):
    definiciones = RepositorioCSV(directorio_datos, directorio_perfiles).definiciones_perfiles()
    assert [d["cluster"] for d in definiciones] == [0, 1]
    assert definiciones[0]["descripcion"] == 'Descripción, con coma y "comillas" de prueba.'
    assert definiciones[1]["medianas"]["estres_hidrico_pct"] == 290.0
    assert definiciones[1]["medianas"]["cobertura_5g_pct"] == 99.0
    assert definiciones[1]["indices"]["hidrica"] == 80.0
    assert definiciones[1]["n_municipios"] == 2


def test_similares_son_los_del_mismo_perfil_sin_incluirse(directorio_datos, directorio_perfiles):
    total, filas = RepositorioCSV(directorio_datos, directorio_perfiles).similares("28001")
    assert total == 1
    assert [f["cod_ine"] for f in filas] == ["41001"]
    # Madrid (40.4, -3.7) - Sevilla (37.4, -5.9): unos 390 km en línea recta.
    assert 350 < filas[0]["distancia_km"] < 430


def test_similares_de_un_perfil_con_un_solo_municipio(directorio_datos, directorio_perfiles):
    assert RepositorioCSV(directorio_datos, directorio_perfiles).similares("01001") == (0, [])


def test_similares_filtra_por_provincia(directorio_datos, directorio_perfiles):
    repo = RepositorioCSV(directorio_datos, directorio_perfiles)
    assert repo.similares("28001", provincia="sevilla")[0] == 1
    assert repo.similares("28001", provincia="Madrid")[0] == 0


def test_perfiles_de_otro_dataset_se_rechazan(directorio_datos, directorio_perfiles):
    (directorio_perfiles / "perfiles_municipios_v01.csv").write_text(
        "cod_ine,cluster,cluster_perfil,es_atipico,version_modelo\n99999,0,X,0,v01\n", encoding="utf-8"
    )
    with pytest.raises(DatosNoDisponibles, match="misma versión"):
        RepositorioCSV(directorio_datos, directorio_perfiles)


def test_se_usa_la_version_mas_alta(tmp_path):
    for v in ("v2", "v10", "v9"):
        (tmp_path / f"perfiles_municipios_{v}.csv").write_text("cod_ine\n", encoding="utf-8")
        (tmp_path / f"perfiles_definicion_{v}.csv").write_text("cluster\n", encoding="utf-8")
    municipios, definicion = buscar_ficheros(tmp_path)
    assert municipios.name == "perfiles_municipios_v10.csv"
    assert definicion.name == "perfiles_definicion_v10.csv"


def test_nunca_se_mezclan_versiones_de_los_dos_ficheros(tmp_path):
    """Municipios v02 y definiciones solo v01: uso v01 en los dos, no v02 con v01."""
    for nombre in ("perfiles_municipios_v01", "perfiles_municipios_v02", "perfiles_definicion_v01"):
        (tmp_path / f"{nombre}.csv").write_text("x\n", encoding="utf-8")
    municipios, definicion = buscar_ficheros(tmp_path)
    assert municipios.name == "perfiles_municipios_v01.csv"
    assert definicion.name == "perfiles_definicion_v01.csv"


def test_sin_ninguna_version_completa_es_un_error(tmp_path):
    (tmp_path / "perfiles_municipios_v02.csv").write_text("x\n", encoding="utf-8")
    (tmp_path / "perfiles_definicion_v01.csv").write_text("x\n", encoding="utf-8")
    with pytest.raises(ErrorPerfiles, match="ninguna versión"):
        buscar_ficheros(tmp_path)


def test_version_del_modelo_distinta_dentro_de_los_ficheros_es_un_error(directorio_perfiles):
    f = directorio_perfiles / "perfiles_definicion_v01.csv"
    f.write_text(f.read_text(encoding="utf-8").replace("v01", "v02"), encoding="utf-8")
    with pytest.raises(ErrorPerfiles, match="mezclan"):
        leer_perfiles(directorio_perfiles)


def test_la_api_no_arranca_con_perfiles_incoherentes(directorio_datos, tmp_path):
    (tmp_path / "perfiles_municipios_v02.csv").write_text("x\n", encoding="utf-8")
    (tmp_path / "perfiles_definicion_v01.csv").write_text("x\n", encoding="utf-8")
    with pytest.raises(DatosNoDisponibles, match="ninguna versión"):
        RepositorioCSV(directorio_datos, tmp_path)


def test_carpeta_incompleta_o_inexistente(tmp_path):
    assert buscar_ficheros(None) == (None, None)
    assert leer_perfiles(tmp_path / "no_existe") is None
    assert leer_perfiles(tmp_path) is None  # carpeta sin ningún fichero de perfiles
