"""Pruebas del motor con 4 municipios inventados (A, B, C, D) y números fáciles.

Universo (4 municipios, todos con dato). Con 4 valores distintos, los percentiles
quedan siempre en 12,5 / 37,5 / 62,5 / 87,5 (de menor a mayor valor).

            suelo_ha   autovia_km   estres
    A          50          80          10
    B          30          10          20
    C          20          40          60
    D           5           5          90

Percentiles (de menor a mayor valor):
    suelo_ha:   D=12,5  C=37,5  B=62,5  A=87,5
    autovia_km: D=12,5  B=37,5  C=62,5  A=87,5   (inversa: se da la vuelta)
    estres:     A=12,5  B=37,5  C=62,5  D=87,5

Reglas de la actividad "demo":
    suelo_ha    atractivo  peso 2  directa   y mínimo >= 10
    autovia_km  atractivo  peso 1  inversa
    estres      riesgo     peso 1  directa
"""

import pandas as pd
import pytest

from sitewise.scoring.modelos import EstadoMinimo, Observacion
from sitewise.scoring.motor import MotorPuntuacion, combinar_estados
from sitewise.scoring.normalizacion import Normalizador
from sitewise.scoring.reglas import cargar_reglas

CSV = (
    "actividad,id_indicador,uso_en_actividad,peso,es_requisito_minimo,operador,umbral,"
    "unidad,sentido,justificacion,aprobado_por,fecha_aprobacion\n"
    "demo,suelo_ha,atractivo,2,si,>=,10,ha,directa,,,\n"
    "demo,autovia_km,atractivo,1,no,,,km,inversa,,,\n"
    "demo,estres,riesgo,1,no,,,%,directa,,,\n"
)

DATOS = {
    "A": {"suelo_ha": 50, "autovia_km": 80, "estres": 10},
    "B": {"suelo_ha": 30, "autovia_km": 10, "estres": 20},
    "C": {"suelo_ha": 20, "autovia_km": 40, "estres": 60},
    "D": {"suelo_ha": 5, "autovia_km": 5, "estres": 90},
}


def observaciones(cod):
    return {k: Observacion(float(v), "real", "municipal") for k, v in DATOS[cod].items()}


def crear_motor(tmp_path, **opciones):
    ruta = tmp_path / "reglas.csv"
    ruta.write_text(CSV, encoding="utf-8")
    filas = [
        {"id_indicador": ind, "valor": v, "estado": "real"}
        for municipio in DATOS.values()
        for ind, v in municipio.items()
    ]
    return MotorPuntuacion(cargar_reglas(ruta), Normalizador(pd.DataFrame(filas)), **opciones)


@pytest.fixture
def motor(tmp_path):
    return crear_motor(tmp_path)


def test_atractivo_con_pesos(motor):
    # A: (2*87,5 + 1*(100-87,5)) / 3 = (175 + 12,5) / 3 = 62,5
    assert motor.evaluar("A", "demo", observaciones("A")).atractivo.nota == pytest.approx(62.5)
    # D: (2*12,5 + 1*(100-12,5)) / 3 = (25 + 87,5) / 3 = 37,5
    assert motor.evaluar("D", "demo", observaciones("D")).atractivo.nota == pytest.approx(37.5)


def test_riesgo_es_una_nota_aparte(motor):
    assert motor.evaluar("A", "demo", observaciones("A")).riesgo.nota == pytest.approx(12.5)
    assert motor.evaluar("D", "demo", observaciones("D")).riesgo.nota == pytest.approx(87.5)


def test_minimo_cumple_y_no_cumple(motor):
    assert motor.evaluar("A", "demo", observaciones("A")).cumple_minimos == EstadoMinimo.CUMPLE
    # D tiene 5 ha y el mínimo es >= 10
    assert motor.evaluar("D", "demo", observaciones("D")).cumple_minimos == EstadoMinimo.NO_CUMPLE


def test_dato_sin_valor_es_no_evaluable_no_cumple(motor):
    obs = observaciones("B")
    obs["suelo_ha"] = Observacion(0.0, "sin_poligonos_en_catalogo")  # un 0 que NO es un 0 real
    ev = motor.evaluar("B", "demo", obs)
    assert ev.cumple_minimos == EstadoMinimo.NO_EVALUABLE
    assert "suelo_ha" in ev.motivo_minimos


def test_falta_un_dato_calcula_nota_parcial(motor):
    obs = observaciones("B")
    obs["suelo_ha"] = Observacion(None, "pendiente")  # falta el indicador de peso 2 (de 3)
    nota = motor.evaluar("B", "demo", obs).atractivo
    # Solo cuenta autovia_km (peso 1): percentil 37,5, inversa -> 62,5
    assert nota.estado == "calculada_parcial"
    assert nota.nota == pytest.approx(62.5)
    assert nota.confianza == pytest.approx(1 / 3, abs=1e-3)
    assert "provisional" in nota.motivo


def test_nota_completa_es_calculada(motor):
    assert motor.evaluar("A", "demo", observaciones("A")).atractivo.estado == "calculada"


def test_sin_ningun_dato_es_no_evaluable(motor):
    obs = {"estres": Observacion(10.0, "real")}  # nada del atractivo
    nota = motor.evaluar("A", "demo", obs).atractivo
    assert nota.estado == "no_evaluable"
    assert nota.nota is None


def test_min_confianza_configurable(tmp_path):
    exigente = crear_motor(tmp_path, min_confianza=0.5)
    obs = observaciones("B")
    obs["suelo_ha"] = Observacion(None, "pendiente")
    nota = exigente.evaluar("B", "demo", obs).atractivo
    assert nota.estado == "no_evaluable"  # confianza 33 % < 50 %
    assert nota.nota is None


def test_proxy_provincial_no_certifica_minimo_pero_si_puntua(motor):
    obs = observaciones("A")
    obs["suelo_ha"] = Observacion(50.0, "aproximado", "provincial")
    ev = motor.evaluar("A", "demo", obs)
    assert ev.cumple_minimos == EstadoMinimo.NO_EVALUABLE  # un proxy provincial no sirve
    assert ev.atractivo.nota == pytest.approx(62.5)  # pero sí entra en la nota
    assert ev.atractivo.componentes[0].aproximado is True


def test_dato_aproximado_municipal_si_evalua_el_minimo_con_aviso(motor):
    # Es lo que pasa con los datos reales: la distancia a un eje o el suelo de un polígono
    # vienen como "aproximado" pero a escala municipal.
    obs = observaciones("A")
    obs["suelo_ha"] = Observacion(50.0, "aproximado", "poligono_industrial")
    minimo = motor.evaluar("A", "demo", obs).minimos[0]
    assert minimo.estado == EstadoMinimo.CUMPLE
    assert minimo.aproximado is True
    assert "aproximado" in minimo.aviso


def test_modo_estricto_rechaza_cualquier_aproximado(tmp_path):
    estricto = crear_motor(tmp_path, permitir_aproximados_en_minimos=False)
    obs = observaciones("A")
    obs["suelo_ha"] = Observacion(50.0, "aproximado", "poligono_industrial")
    assert estricto.evaluar("A", "demo", obs).cumple_minimos == EstadoMinimo.NO_EVALUABLE


def test_reglas_provisionales_hasta_que_se_aprueben(motor):
    assert motor.evaluar("A", "demo", observaciones("A")).reglas_provisionales is True


def test_actividad_sin_reglas(motor):
    with pytest.raises(ValueError):
        motor.evaluar("A", "no_existe", observaciones("A"))


def test_combinar_estados():
    C, N, E = EstadoMinimo.CUMPLE, EstadoMinimo.NO_CUMPLE, EstadoMinimo.NO_EVALUABLE
    assert combinar_estados([C, C]) == C
    assert combinar_estados([C, E]) == E
    assert combinar_estados([N, E]) == N  # un fallo seguro manda sobre lo que no sé
    assert combinar_estados([]) == E  # sin mínimos definidos no digo "cumple"
