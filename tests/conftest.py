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


# Igual que VALORES, pero con las columnas de valores_app.csv (notebook 09). Cambios respecto a VALORES:
# - 41001 / estres: era "pendiente" sin valor; ahora es una ESTIMACIÓN con los vecinos (valor 30).
#   Conserva su estado de origen (sin_masa_catalogada), como en el dataset real.
# - 41001 / suelo_ha: sigue "sin_poligonos_en_catalogo" aunque la app lo llame "aproximado".
VALORES_APP = (
    "cod_ine,id_indicador,valor,estado,nivel_origen,fecha_dato,fuente_id,naturaleza,metodo,url_fuente,"
    "estado_app,valor_original,estimado_app,k_vecinos,distancia_media_km,distancia_maxima_km\n"
    "01001,suelo_ha,50,real,municipal,2020,f1,observado,m,u,real,50,False,,,\n"
    "01001,autovia_km,80,real,municipal,2026-11-13,f2,calculado,m,u,real,80,False,,,\n"
    "01001,estres,10,real,municipal,2019,f3,modelizado,m,u,real,10,False,,,\n"
    "28001,suelo_ha,30,real,municipal,2020,f1,observado,m,u,real,30,False,,,\n"
    "28001,autovia_km,10,real,municipal,2026-11-13,f2,calculado,m,u,real,10,False,,,\n"
    "28001,estres,20,aproximado,provincial,2019,f3,modelizado,m,u,aproximado,20,False,,,\n"
    "41001,suelo_ha,0,sin_poligonos_en_catalogo,municipal,2020,f1,observado,m,u,aproximado,0,False,,,\n"
    "41001,autovia_km,40,real,municipal,2026-11-13,f2,calculado,m,u,real,40,False,,,\n"
    "41001,estres,30,sin_masa_catalogada,masa_de_agua,2019,f3,estimado_vecinos_geograficos,"
    "Media de los 5 vecinos con dato,u,aproximado,,True,5.0,3.0,3.9\n"
)


@pytest.fixture
def directorio_datos_app(directorio_datos):
    """Como `directorio_datos`, pero además con un valores_app.csv (que tiene prioridad sobre valores.csv)."""
    (directorio_datos / "valores_app.csv").write_text(VALORES_APP, encoding="utf-8")
    return directorio_datos


# Perfiles INVENTADOS (mismo formato que los de Helen en data/reference). 28001 y 41001 comparten perfil.
PERFILES_MUNICIPIOS = (
    "cod_ine,cluster,cluster_perfil,es_atipico,version_modelo\n"
    "01001,0,Perfil de prueba A,0,v01\n"
    "28001,1,Perfil de prueba B,0,v01\n"
    "41001,1,Perfil de prueba B,1,v01\n"
)
PERFILES_DEFINICION = (
    "cluster,cluster_perfil,descripcion,n_municipios,mediana_suelo_industrial_cartografiado_pct,"
    "mediana_dist_recta_eje_autovia_km,mediana_dist_recta_ttm_km,mediana_estres_hidrico_pct,"
    "mediana_cobertura_ftth_pct,mediana_cobertura_5g_pct,media_idx_logistica,media_idx_hidrica,"
    "media_idx_conectividad,version_modelo\n"
    '0,Perfil de prueba A,"Descripción, con coma y ""comillas"" de prueba.",1,1.0,2.0,3.0,40.0,95.0,100.0,75.0,40.0,66.0,v01\n'
    "1,Perfil de prueba B,Otra descripción de prueba.,2,1.5,2.5,3.5,290.0,94.0,99.0,57.0,80.0,58.0,v01\n"
)


@pytest.fixture
def directorio_perfiles(tmp_path_factory):
    """Carpeta temporal con los dos CSV de perfiles inventados (como data/reference)."""
    carpeta = tmp_path_factory.mktemp("reference")
    (carpeta / "perfiles_municipios_v01.csv").write_text(PERFILES_MUNICIPIOS, encoding="utf-8")
    (carpeta / "perfiles_definicion_v01.csv").write_text(PERFILES_DEFINICION, encoding="utf-8")
    return carpeta
