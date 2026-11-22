"""Pruebas de la lectura de valores_app.csv (preparado por el notebook 09 con las estimaciones de agua).

Los datos son inventados, con la misma forma que los reales. Lo que se comprueba:
- si existe valores_app.csv, se usa; si no, valores.csv;
- una estimación con vecinos (estado de origen "sin_masa_catalogada") pasa a ser un dato aproximado utilizable;
- "sin_poligonos_en_catalogo" NO pasa a ser utilizable aunque la app lo llame "aproximado".
"""

from sitewise.db.repositorio import RepositorioCSV
from sitewise.scoring.calidad import motivo_no_utilizable


def test_usa_valores_app_si_existe(directorio_datos_app):
    assert RepositorioCSV(directorio_datos_app).info()["valores_fichero"] == "valores_app.csv"


def test_sin_valores_app_usa_valores_csv(directorio_datos):
    repo = RepositorioCSV(directorio_datos)
    assert repo.info()["valores_fichero"] == "valores.csv"
    assert all(not d["estimado"] for d in repo.detalle_indicadores("41001"))


def test_la_estimacion_con_vecinos_es_aproximada_y_utilizable(directorio_datos_app):
    obs = RepositorioCSV(directorio_datos_app).observaciones("41001")["estres"]
    assert obs.valor == 30 and obs.estado == "aproximado"
    assert motivo_no_utilizable(obs.valor, obs.estado, obs.nivel_origen) is None


def test_la_ficha_cuenta_como_se_estimo(directorio_datos_app):
    detalle = {d["id_indicador"]: d for d in RepositorioCSV(directorio_datos_app).detalle_indicadores("41001")}
    estres = detalle["estres"]
    assert estres["estimado"] is True and estres["vecinos"] == 5
    assert estres["distancia_media_km"] == 3.0 and estres["distancia_maxima_km"] == 3.9
    assert estres["metodo"] == "Media de los 5 vecinos con dato"
    # Los datos no estimados no llevan esos campos.
    assert detalle["autovia_km"]["estimado"] is False and detalle["autovia_km"]["metodo"] is None


def test_sin_poligonos_sigue_sin_ser_utilizable(directorio_datos_app):
    suelo = RepositorioCSV(directorio_datos_app).observaciones("41001")["suelo_ha"]
    assert suelo.estado == "sin_poligonos_en_catalogo"  # no se sustituye por el "aproximado" de la app
    assert motivo_no_utilizable(suelo.valor, suelo.estado, suelo.nivel_origen) is not None


def test_el_resto_de_filas_no_cambia(directorio_datos, directorio_datos_app):
    sin_app = RepositorioCSV(directorio_datos)
    con_app = RepositorioCSV(directorio_datos_app)
    for cod in ("01001", "28001"):
        assert con_app.observaciones(cod) == sin_app.observaciones(cod)
