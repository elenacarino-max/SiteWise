"""Mis pruebas libres del paso 1. NO es un test de pytest: se ejecuta como script.

Desde la raíz del repo:
    python tests/scoring/prueba_libre.py

Antes de ejecutar cada bloque, escribo en un papel qué espero que salga.
Luego comparo. Si no coincide, miro por qué (puede ser un fallo mío o una
decisión de diseño que quiero entender).
"""

import tempfile
from pathlib import Path

import pandas as pd

from sitewise.scoring.calidad import motivo_no_utilizable
from sitewise.scoring.normalizacion import Normalizador
from sitewise.scoring.reglas import ErrorReglas, cargar_reglas


def universo(valores, estados=None):
    """Atajo: crea la tabla mínima que necesita Normalizador."""
    estados = estados or ["real"] * len(valores)
    return pd.DataFrame({"id_indicador": ["a"] * len(valores), "valor": valores, "estado": estados})


print("=== 1. Empates ===")
# Espero: el 20 está repetido 3 veces. Menores=1, menores_o_iguales=4 -> (1+4)/(2*5)=50
n = Normalizador(universo([10, 20, 20, 20, 40]))
print("percentil del 20:", n.percentil("a", 20), "(espero 50)")

print("\n=== 2. Valores fuera de rango ===")
n = Normalizador(universo([10, 20, 30, 40]))
print("percentil del 5:  ", n.percentil("a", 5), "(espero 0)")
print("percentil del 100:", n.percentil("a", 100), "(espero 100)")
# Pregunta para mí: ¿es razonable que un valor por debajo de todos tenga percentil 0?

print("\n=== 3. Estados raros ===")
print(motivo_no_utilizable(0.0, "sin_poligonos_en_catalogo", None))
print(motivo_no_utilizable(0.0, "real", None), "(espero None: un 0 real sí se usa)")
print(motivo_no_utilizable(None, "ocultado_menor5", None))
print(motivo_no_utilizable(7.0, "aproximado_modelo", "municipal", permitir_aproximados=False))

print("\n=== 4. CSV roto a propósito ===")
CABECERA = "actividad,id_indicador,uso_en_actividad,peso,es_requisito_minimo,operador,umbral,sentido\n"
casos = {
    "peso no numérico": "demo,a,riesgo,abc,no,,,directa\n",
    "sentido inventado": "demo,a,riesgo,1,no,,,alto\n",
    "uso inventado": "demo,a,otro,1,no,,,directa\n",
}
with tempfile.TemporaryDirectory() as carpeta:
    for nombre, fila in casos.items():
        ruta = Path(carpeta) / "r.csv"
        ruta.write_text(CABECERA + fila, encoding="utf-8")
        try:
            cargar_reglas(ruta)
            print(f"{nombre}: ¡no dio error! (revisar)")
        except ErrorReglas as error:
            print(f"{nombre}: {error}")

print("\n=== 5. Dos actividades en el mismo CSV ===")
with tempfile.TemporaryDirectory() as carpeta:
    ruta = Path(carpeta) / "r.csv"
    ruta.write_text(
        CABECERA
        + "conservas,suelo_ha,atractivo,2,si,>=,8,directa\n"
        + "conservas,estres,riesgo,1,no,,,directa\n"
        + "logistica,dist_autovia,atractivo,3,no,,,inversa\n",
        encoding="utf-8",
    )
    reglas = cargar_reglas(ruta)
    print("actividades:", reglas.actividades())
    print("resumen conservas:", reglas.resumen("conservas"))
    print("resumen logistica:", reglas.resumen("logistica"))

print("\n=== 6. Mi propia prueba (completar) ===")
# Idea: si todos los valores de un indicador están en estado 'pendiente',
# n.n("a") debería ser 0 y n.percentil("a", 5) debería ser None.
# Escribo aquí el código, lo ejecuto y compruebo si pasa lo que espero.
