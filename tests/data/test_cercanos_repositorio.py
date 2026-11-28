"""Pruebas de los municipios cercanos en el repositorio CSV (datos inventados)."""

import pytest

from sitewise.db.perfiles import buscar_cercanos
from sitewise.db.repositorio import DatosNoDisponibles, RepositorioCSV


def test_sin_fichero_no_hay_cercanos(directorio_datos):
    repo = RepositorioCSV(directorio_datos)
    assert repo.cercanos("28001") is None
    assert repo.info()["cercanos_cargados"] is False


def test_cercanos_con_datos_del_municipio(directorio_datos, directorio_perfiles):
    repo = RepositorioCSV(directorio_datos, directorio_perfiles)
    primero = repo.cercanos("28001")[0]
    assert primero["cod_ine"] == "41001" and primero["posicion"] == 1 and primero["distancia_km"] == 12.5
    assert repo.cercanos("01001") is None  # sin filas
    assert repo.info()["cercanos_cargados"] is True


def test_elige_la_version_mas_alta(tmp_path):
    (tmp_path / "municipios_cercanos_v01.csv").write_text("cod_ine\n", encoding="utf-8")
    (tmp_path / "municipios_cercanos_v02.csv").write_text("cod_ine\n", encoding="utf-8")
    assert buscar_cercanos(tmp_path).name == "municipios_cercanos_v02.csv"
    assert buscar_cercanos(tmp_path / "no_existe") is None


def test_cercanos_de_otro_dataset_dan_error(directorio_datos, tmp_path):
    (tmp_path / "municipios_cercanos_v01.csv").write_text(
        "cod_ine,cod_ine_cercano,posicion,distancia_km\n28001,99999,1,1.0\n", encoding="utf-8"
    )
    with pytest.raises(DatosNoDisponibles):
        RepositorioCSV(directorio_datos, tmp_path)
