"""Pruebo el motor con los datos REALES y unas reglas inventadas solo para ensayar.

IMPORTANTE: las reglas de este script (pesos, mínimo de 10 ha...) NO son criterios del equipo.
Sirven solo para ver cómo se comporta el código. No se guardan en configs/.

Desde la raíz del repo (no es un test de pytest, no se commitea):
    python tests/scoring/prueba_motor_real.py
"""

import sys
import tempfile
from pathlib import Path

from sitewise.db.repositorio import RepositorioCSV
from sitewise.scoring.motor import MotorPuntuacion
from sitewise.scoring.normalizacion import Normalizador
from sitewise.scoring.reglas import cargar_reglas

directorio = sys.argv[1] if len(sys.argv) > 1 else "data/processed/sitewise_v03"
repo = RepositorioCSV(directorio)

# Reglas de ensayo (sentido: directa = valor alto da nota alta; inversa = valor bajo da nota alta)
REGLAS = (
    "actividad,id_indicador,uso_en_actividad,peso,es_requisito_minimo,operador,umbral,unidad,sentido\n"
    "ensayo,suelo_industrial_cartografiado_ha,atractivo,2,si,>=,10,ha,directa\n"
    "ensayo,dist_recta_eje_autovia_km,atractivo,1,si,<=,20,km,inversa\n"
    "ensayo,cobertura_ftth_pct,atractivo,1,no,,,%,directa\n"
    "ensayo,estres_hidrico_pct,riesgo,1,no,,,%,directa\n"
)
with tempfile.TemporaryDirectory() as carpeta:
    ruta = Path(carpeta) / "reglas.csv"
    ruta.write_text(REGLAS, encoding="utf-8")
    reglas = cargar_reglas(ruta)

# Cargo el universo de percentiles con TODOS los municipios (tarda unos segundos)
motor = MotorPuntuacion(reglas, Normalizador(repo.valores))


def mostrar(cod_ine):
    nombre = repo.municipio(cod_ine)["nombre"]
    ev = motor.evaluar(cod_ine, "ensayo", repo.observaciones(cod_ine))
    print(f"\n=== {nombre} ({cod_ine}) ===")
    print(f"Mínimos: {ev.cumple_minimos.value}  {ev.motivo_minimos}")
    for m in ev.minimos:
        extra = f" | {m.aviso}" if m.aviso else (f" | {m.motivo}" if m.motivo else "")
        print(f"   - {m.id_indicador} {m.operador} {m.umbral}: {m.estado.value} (valor {m.valor}){extra}")
    for nota in (ev.atractivo, ev.riesgo):
        print(f"{nota.dimension}: {nota.estado} nota={nota.nota} confianza={nota.confianza} {nota.motivo}")
    print(f"Reglas provisionales: {ev.reglas_provisionales}")


# Pruebo varios municipios: Madrid, Álava (01001) y Sevilla (41091)
for cod in ("28079", "01001", "41091"):
    if repo.municipio(cod):
        mostrar(cod)

# Cuántos municipios caen en cada estado de mínimos (tarda algo: evalúa los 8132)
print("\n=== Reparto de mínimos en todos los municipios ===")
conteo = {}
for cod in repo.municipios.index:
    estado = motor.evaluar(cod, "ensayo", repo.observaciones(cod)).cumple_minimos.value
    conteo[estado] = conteo.get(estado, 0) + 1
print(conteo)