import pandas as pd
import pytest

from sitewise.scoring.calidad import motivo_no_utilizable
from sitewise.scoring.normalizacion import Normalizador
from sitewise.scoring.reglas import ErrorReglas, cargar_reglas

CSV = (
    "actividad,id_indicador,uso_en_actividad,peso,es_requisito_minimo,operador,umbral,"
    "unidad,sentido,justificacion,aprobado_por,fecha_aprobacion\n"
    "demo,suelo_ha,atractivo,2,si,>=,10,ha,directa,,,\n"
    "demo,estres,riesgo,1,no,,,%,directa,x,Ana,2026-11-18\n"
)


def test_percentil_a_mano():
    # Universo: 10, 20, 30, 40. El 30 tiene 2 por debajo y 1 igual: (2+3)/(2*4)=62,5
    obs = pd.DataFrame({
        "id_indicador": ["a"] * 4,
        "valor": [10, 20, 30, 40],
        "estado": ["real"] * 4,
    })
    n = Normalizador(obs)
    assert n.percentil("a", 30) == pytest.approx(62.5)
    assert n.percentil("a", 10) == pytest.approx(12.5)
    assert n.percentil("no_existe", 1) is None


def test_estados_sin_valor_no_entran_en_el_universo():
    obs = pd.DataFrame({
        "id_indicador": ["a"] * 3,
        "valor": [10, 0, 20],
        "estado": ["real", "ocultado_menor5", "real"],
    })
    assert Normalizador(obs).n("a") == 2


def test_dato_aproximado_no_certifica_minimo():
    assert motivo_no_utilizable(5.0, "real", "municipal", permitir_aproximados=False) is None
    assert motivo_no_utilizable(5.0, "aproximado", "municipal", permitir_aproximados=False)
    assert motivo_no_utilizable(5.0, "real", "Provincial", permitir_aproximados=False)
    assert motivo_no_utilizable(float("nan"), "real", None)


def test_carga_de_reglas(tmp_path):
    f = tmp_path / "reglas.csv"
    f.write_text(CSV, encoding="utf-8")
    reglas = cargar_reglas(f)
    assert reglas.actividades() == ["demo"]
    res = reglas.resumen("demo")
    assert res["n_minimos"] == 1 and res["n_puntuables"] == 2
    assert res["estado_reglas"] == "provisionales"  # solo una regla está aprobada
    assert [r.aprobada for r in reglas.de("demo")] == [False, True]


def test_fichero_ausente_es_conjunto_vacio(tmp_path):
    assert cargar_reglas(tmp_path / "no_existe.csv").actividades() == []


def test_operador_invalido(tmp_path):
    f = tmp_path / "r.csv"
    f.write_text(CSV.replace(">=", "~"), encoding="utf-8")
    with pytest.raises(ErrorReglas):
        cargar_reglas(f)
