"""Compruebo con los datos REALES que mis suposiciones sobre el dataset son correctas.

Se ejecuta desde la raíz del repo (no es un test de pytest, no se commitea):
    python tests/data/prueba_datos_reales.py
    python tests/data/prueba_datos_reales.py data/processed/sitewise_v03

Solo lee, no escribe nada.
"""

import sys

from sitewise.db.repositorio import RepositorioCSV
from sitewise.scoring.calidad import ESTADOS_APROXIMADOS, ESTADOS_SIN_VALOR

directorio = sys.argv[1] if len(sys.argv) > 1 else "data/processed/sitewise_v03"
repo = RepositorioCSV(directorio)
v = repo.valores

print("=== 1. Resumen ===")
print(repo.info())
print("Columnas de valores.csv:", list(v.columns))

print("\n=== 2. Estados: ¿los reconozco todos? ===")
# Para cada estado distinto: cuántas filas tiene y cómo lo trata mi código.
cuentas = v["estado"].fillna("(vacío)").value_counts()
for estado, n in cuentas.items():
    if estado in ESTADOS_SIN_VALOR:
        trato = "SIN VALOR (no se usa)"
    elif estado in ESTADOS_APROXIMADOS:
        trato = "aproximado (puntúa, no certifica mínimos)"
    else:
        trato = "se usa como dato normal"
    print(f"  {estado:40s} {n:8d}  -> {trato}")
print("  Revisa los que dicen 'se usa como dato normal': ¿alguno debería ser 'sin valor'?")

print("\n=== 3. ¿Hay valores con número pero estado 'sin valor'? (el caso del cero engañoso) ===")
raros = v[v["estado"].isin(ESTADOS_SIN_VALOR) & v["valor"].notna()]
print("  ninguno" if raros.empty else raros.groupby(["id_indicador", "estado"]).size().head(15).to_string())

print("\n=== 4. ¿Hay valores vacíos con un estado que mi código trataría como normal? ===")
huecos = v[v["valor"].isna() & ~v["estado"].isin(ESTADOS_SIN_VALOR)]
print("  ninguno" if huecos.empty else huecos.groupby("estado").size().to_string())
print("  (no es un fallo: un hueco siempre se trata como 'sin valor' aunque el estado no esté en mi lista)")

if "nivel_origen" in v.columns:
    print("\n=== 5. Niveles de origen ===")
    print(v["nivel_origen"].fillna("(vacío)").value_counts().to_string())

print("\n=== 6. Un municipio de ejemplo ===")
total, encontrados = repo.buscar_municipios(q="madrid", limite=3)
print("Búsqueda 'madrid':", total, [(m["cod_ine"], m["nombre"]) for m in encontrados])
if encontrados:
    for d in repo.detalle_indicadores(encontrados[0]["cod_ine"])[:5]:
        print(" ", d["id_indicador"], d["valor"], d["unidad"], d["estado"], d["fecha_dato"])
