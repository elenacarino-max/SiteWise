# Decisión: requisitos mínimos y datos aproximados

Fecha: 21 de noviembre de 2026. Responsable: Adriana (Backend API y cálculo).
Estado: **propuesta provisional**, pendiente de que el equipo la ratifique.

## Contexto

Un requisito mínimo es una condición del tipo "al menos 8 ha de suelo industrial". El contrato
del dataset dice que, si falta el dato de un mínimo, el resultado es `no_evaluable`, y que un
proxy provincial no debe usarse como si fuera una medición municipal.

Mi primera versión del motor rechazaba **cualquier** dato con estado `aproximado` o
`aproximado_modelo` para evaluar un mínimo. Al probar con el dataset v0.3 real descubrí que eso
dejaba los mínimos inservibles: de 292.752 observaciones, 80.136 tienen estado `aproximado` y 8.130
`aproximado_modelo`, y afectan justo a los indicadores con los que se puede plantear un mínimo.

| Indicador | Nivel de origen | Observaciones aproximadas |
|---|---|---:|
| `dist_recta_eje_autovia_km` | eje_infraestructura | 8.076 |
| `dist_recta_ttm_km`, `dist_recta_ttm_intermodal_km` | punto_infraestructura | 7.971 cada una |
| `suelo_industrial_cartografiado_ha` y `_pct` | poligono_industrial | 3.699 cada una |
| `estres_hidrico_pct`, `agotamiento_hidrico_pct`, `superficie_estres_ge40_pct` | subcuenca | 8.108 cada una |
| `irradiacion_ghi_kwh_m2_anio` | rejilla_0.05_grados | 8.132 |
| `viento_100m_media_m_s` | raster | 8.130 |
| `niepi_prov_2021`, `tiepi_horas_prov_2021` | **provincia** | 8.132 cada una |

Solo los dos indicadores eléctricos son un proxy provincial. Los demás se calculan a escala
municipal a partir de una geometría más fina (un eje, una subcuenca, un polígono, una celda).

## Decisión

1. Un dato **aproximado a escala municipal puede evaluar un mínimo** (cumple / no cumple), pero el
   resultado se marca con `aproximado = true` y un `aviso` ("evaluado con un dato aproximado
   (estado: ..., nivel: ...)"). Nadie debe leerlo como una medición exacta.
2. Un dato **proxy provincial nunca certifica un mínimo**: el resultado es `no_evaluable`, tal como
   pide el contrato del dataset.
3. El motor tiene un **modo estricto** (`permitir_aproximados_en_minimos=False`) que rechaza
   cualquier dato aproximado. Si el equipo prefiere ese criterio, basta con cambiar el parámetro.
4. Un dato sin valor o con estado de ausencia sigue siendo `no_evaluable`, nunca `cumple`.
5. En las notas, los datos aproximados siguen entrando y se marcan como aproximados.

## Lo que sigue pendiente de verificar (no lo resuelvo yo)

El archivo `docs/data/sitewise_v03/pendientes_y_proxies.csv` indica límites que esta decisión **no**
elimina:

- **Autovía:** la distancia es recta al eje cartografiado. No acredita acceso, tiempo ni ruta.
- **Terminal ferroviaria:** la proximidad a una terminal catalogada no confirma que el servicio esté
  activo.
- **Parcelas:** el suelo industrial cartografiado no equivale a suelo disponible, y un cero no
  significa que no haya suelo.
- **Agua industrial:** los indicadores hídricos no acreditan caudal ni concesión. Cualquier mínimo de
  agua industrial es no evaluable sin verificación.

Por eso un "cumple" basado en estos datos debe presentarse como una valoración municipal orientativa,
no como una garantía sobre una parcela concreta.

## Consecuencia práctica con los datos reales

En 4.433 municipios (más de la mitad de los 8.132) el suelo industrial tiene valor 0 con estado
`sin_poligonos_en_catalogo`. Como ese cero no significa "no hay suelo", un mínimo de suelo en esos
municipios sale `no_evaluable`, no `no_cumple`. Es correcto según el diccionario, pero la interfaz y
el agente deben explicarlo, o parecerá que la mayoría de los municipios no se pueden valorar.

## Pendiente de decidir con el equipo

- ¿Se acepta que un dato aproximado a escala municipal evalúe un mínimo, o se usa el modo estricto?
- ¿Se mantiene el bloqueo de los proxies provinciales para los mínimos?
- ¿Cómo muestran Gema y Josema el aviso y los 4.433 casos de suelo no evaluable?

## Dónde está en el código

- `src/sitewise/scoring/calidad.py` (`es_proxy_provincial`, `motivo_no_utilizable`).
- `src/sitewise/scoring/motor.py` (`_evaluar_minimos`).
- Pruebas: `tests/scoring/test_motor.py` y `tests/scoring/test_reglas_normalizacion.py`.
