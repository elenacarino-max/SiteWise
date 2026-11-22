"""Datos inventados con el mismo formato que el dataset v0.3, para probar sin los datos reales.

Los nombres y los valores NO son reales: solo sirven para comprobar que el código funciona.
"""

import pytest

MUNICIPIOS = (
    "cod_ine,nombre,cod_provincia,provincia,ccaa,superficie_km2,lat,lon,anio_geometria\n"
    "01001,Villaverde Alta,01,Álava,País Vasco,100.0,42.8,-2.7,2024\n"
    "28001,Vallehondo,28,Madrid,Comunidad de Madrid,50.0,40.4,-3.7,2024\n"
    "41001,Río Seco,41,Sevilla,Andalucía,80.0,37.4,-5.9,2024\n"
)

INDICADORES = (
    "id_indicador,nombre,bloque,tipo,unidad,sentido,fuente_id,fuente,fecha_dato,nivel_origen,"
    "metodo,naturaleza,limitaciones\n"
    "suelo_ha,Suelo industrial,logistica,atractivo,ha,mayor_mejor,f1,Fuente 1,2020,municipal,m,observado,"
    "No equivale a suelo disponible\n"
    "autovia_km,Distancia a autovía,logistica,atractivo,km,menor_mejor,f2,Fuente 2,2026-11-13,municipal,m,"
    "calculado,Distancia recta\n"
    "estres,Estrés hídrico,agua,riesgo,%,mayor_peor,f3,Fuente 3,2019,municipal,m,modelizado,\n"
)

# Municipio 41001 no tiene suelo industrial en el catálogo: un 0 que NO es un 0 real.
VALORES = (
    "cod_ine,id_indicador,valor,estado,nivel_origen,fecha_dato,fuente_id,naturaleza,metodo,url_fuente\n"
    "01001,suelo_ha,50,real,municipal,2020,f1,observado,m,u\n"
    "01001,autovia_km,80,real,municipal,2026-11-13,f2,calculado,m,u\n"
    "01001,estres,10,real,municipal,2019,f3,modelizado,m,u\n"
    "28001,suelo_ha,30,real,municipal,2020,f1,observado,m,u\n"
    "28001,autovia_km,10,real,municipal,2026-11-13,f2,calculado,m,u\n"
    "28001,estres,20,aproximado,provincial,2019,f3,modelizado,m,u\n"
    "41001,suelo_ha,0,sin_poligonos_en_catalogo,municipal,2020,f1,observado,m,u\n"
    "41001,autovia_km,40,real,municipal,2026-11-13,f2,calculado,m,u\n"
    "41001,estres,,pendiente,municipal,2019,f3,modelizado,m,u\n"
)


@pytest.fixture
def directorio_datos(tmp_path):
    """Carpeta temporal con los tres CSV inventados."""
    (tmp_path / "municipios.csv").write_text(MUNICIPIOS, encoding="utf-8")
    (tmp_path / "indicadores.csv").write_text(INDICADORES, encoding="utf-8")
    (tmp_path / "valores.csv").write_text(VALORES, encoding="utf-8")
    return tmp_path
