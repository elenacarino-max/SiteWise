# Ficha del modelo: perfil de municipio (clustering)

Issue #16 (ML-04) · Versión del modelo: `v02` · Responsable: Helen · Noviembre de 2026

## Para qué sirve

Agrupa los municipios de España en **4 perfiles** según su logística, su presión hídrica y su conectividad digital, para describir cada municipio en lenguaje sencillo (API y asistente RAG). Es un análisis **exploratorio**: describe cómo es un municipio, no dice si es bueno o malo para una actividad.

**Un perfil no es un riesgo ni una nota.** El riesgo y el atractivo se calculan aparte, en la puntuación de cada actividad. El esquema es: el clustering *describe*, el scoring *evalúa* y la IA *explica*.

## Qué cambió respecto a v01

v01 agrupaba 7 variables mezcladas (población, suelo industrial, distancias, paro, viento y agua) con PCA y K=5. Tras la revisión técnica se rediseñó: solo se agrupan variables con un sentido claro de bueno/malo, en **índices temáticos**, y el cluster final usa **tres entradas** (el máximo pedido era 3–4). v01 sigue en el historial de Git (commit `bc30250`) y en `data/reference/perfiles_*_v01.csv`, solo como referencia.

## Datos

- Dataset `sitewise_v04_candidata` (notebooks 01A y 03A) y percentiles de los componentes (notebook 03B).
- Tienen perfil **7.975 de los 8.132 municipios (98,1 %)**.
- Se ajusta con todos los municipios a la vez (no hay conjunto de validación separado).

## Índices (0 a 100)

Cada índice es la media de percentiles de rango medio de sus componentes; las distancias van invertidas, así que 100 es siempre lo mejor en logística y conectividad y "más presión" en hídrica. El cálculo está en `src/sitewise/ml/indices.py`.

| Índice | Componentes | Huecos |
|---|---|---|
| Logística | `suelo_industrial_cartografiado_pct`, `dist_recta_eje_autovia_km` (inv.), `dist_recta_ttm_km` (inv.) | No se imputan: sin un componente, no hay perfil |
| Hídrica | `estres_hidrico_pct`, `agua_subterranea_mal_estado_cuantitativo_pct` | Se estiman con la media de los 5 municipios cercanos con dato y se marcan |
| Conectividad | `cobertura_ftth_pct`, `cobertura_5g_pct` | Sin huecos |

No entran en el perfil, y quedan como datos sueltos (filtros, scoring por actividad y RAG): población, densidad, variación de población, paro, viento, irradiación y riesgos naturales (incendios e inundaciones). Los riesgos naturales tienen cobertura parcial: añadirlos dejaría solo el 49,5 % de los municipios con perfil. La decisión se documenta en `notebooks/04_decision_variables_perfil.ipynb`.

## Modelo

K-Means con **K=4**, `n_init=20`, semilla 42, sobre los tres índices. No hay PCA ni escalado (los índices ya están en la misma escala). Los números de grupo se ordenan por el índice de logística (0 = la mejor), así no cambian entre ejecuciones.

**K=4 es una decisión de interpretación, no de métrica.** En el barrido de K de 2 a 8 el silhouette es más alto con K=2 (0,307) y baja hasta 0,253 con K=8; con K=4 vale 0,290. Se eligió 4 porque es el menor número de grupos que separa a los municipios de poca logística **mal conectados** de los que tienen **buena conectividad**, y deja cada perfil descrito en una frase. K=3 sería igualmente defendible (cambiar un parámetro en el notebook 07). Detalle en `notebooks/05_clustering_kmeans.ipynb`; los experimentos se registran en MLflow (notebook 06).

## Perfiles

Los nombres están en `src/sitewise/ml/perfiles.py` y son **provisionales** (los cierra Gema).

| Grupo | Perfil | Municipios | Suelo ind. (%, mediana) | Autovía (km) | Terminal (km) | Estrés hídrico (%) | Fibra (%) | 5G (%) |
|---|---|---|---|---|---|---|---|---|
| 0 | Buena logística y buena conectividad | 1.876 | 0,54 | 3,0 | 29,0 | 41 | 96 | 100 |
| 1 | Logística media-buena con mucha presión hídrica | 1.584 | 0,10 | 6,7 | 53,2 | 295 | 95 | 100 |
| 2 | Logística baja y mal conectados | 2.470 | 0,00 | 15,0 | 62,2 | 58 | 75 | 89 |
| 3 | Logística baja pero bien conectados | 2.045 | 0,00 | 19,5 | 77,5 | 59 | 94 | 100 |

Medias de los índices por grupo (logística / hídrica / conectividad): 75/40/66, 58/80/59, 40/42/24 y 33/43/59. Todas las cifras por grupo están en `data/reference/perfiles_definicion_v02.csv`.

## Calidad

- **Silhouette: 0,290** (sobre una muestra fija de 5.000 municipios). Es bajo y **no es comparable con el 0,230 de v01**, porque son espacios de variables distintos.
- **Estabilidad: ARI mínimo 0,995** entre semillas.
- Los índices de percentil son casi uniformes, así que K-Means *corta un continuo*: los grupos se justifican por su interpretación, no por un silhouette alto.

## Ficheros de salida (`data/reference/`)

- `perfiles_municipios_v02.csv` (7.975 filas, ordenado por `cod_ine`): `cod_ine` (texto de 5 dígitos), `cluster` (0–3), `cluster_perfil`, `es_atipico` y `version_modelo`. Lo usan la API (Adriana) y el RAG (Josema).
- `perfiles_definicion_v02.csv`: una fila por perfil, con nombre, descripción, nº de municipios, medianas de las variables y medias de los índices.
- `perfiles_estado_v02.csv` (8.132 filas): si cada municipio tiene perfil, por qué no, qué datos se estimaron con vecinos y los tres índices.

La API carga siempre la versión más alta que tengan los dos ficheros principales. Los municipios sin perfil devuelven `perfil_no_disponible`.

## Municipios cercanos

Para cada municipio, los 5 más **cercanos en el mapa**, en `data/reference/municipios_cercanos_v01.csv` (40.660 filas, generadas con `notebooks/10_municipios_cercanos.ipynb` y `src/sitewise/ml/cercanos.py`). Columnas: `cod_ine`, `cod_ine_cercano`, `posicion` (1 = el más cercano) y `distancia_km`. No depende del modelo de agrupación: es un cálculo geográfico. Se explica aquí porque lo usan los mismos equipos que el fichero de perfiles.

- "Cercano" es próximo en el mapa (distancia en línea recta entre los puntos `lat` y `lon` de cada municipio), no parecido en características. Se eligió así porque el agua y los riesgos naturales dependen del territorio.
- El número de cercanos es una constante, `N_CERCANOS` (5), en `cercanos.py`. Para cambiarlo, se cambia ese número y se regenera el fichero.
- El 92 % de los cercanos son de la misma provincia y la mediana de la distancia media es de 6,7 km.
- Los cercanos comparten el agua y el estrés hídrico (correlación de 0,88 a 0,97) y menos las inundaciones y los incendios (de 0,52 a 0,74). Con municipios elegidos al azar sale casi 0.
- Melilla, Ceuta, Canarias y Formentera tienen cercanos lejanos (hasta 164 km de media en Melilla); `distancia_km` permite avisar.

## Limitaciones

1. **Es un continuo, no cuatro bloques separados.** Un municipio cerca de la frontera entre dos perfiles podría estar en cualquiera de los dos.
2. **K=4 no lo eligen las métricas** (ver arriba). Es una decisión de interpretación defendible, no la única.
3. **157 municipios sin perfil** (1,93 %): Baleares (67), Canarias (88), Ceuta y Melilla, sin distancia a terminal de mercancías por tierra. Hacinas, Monasterio de la Sierra, Llívia y A Illa de Arousa tenían el dato vacío por cómo se calculaba; se corrigió el 27 de noviembre de 2026 (PR #61, notebook 02) y ahora tienen perfil. La distancia a terminal no se imputa porque estimarla desde un vecino no tendría sentido por tierra.
4. **La dimensión hídrica usa datos estimados**: 722 municipios sin masa de agua catalogada (acuíferos) y 24 sin estrés hídrico, completados con los 5 municipios cercanos. Comprobado ocultando municipios y estimándolos con vecinos de otras provincias, el error medio es de 12,8 puntos (16,5 si se rellena con 0 y 26,1 con la media) y la correlación con el valor real es de 0,67. Es una aproximación: se marca en `perfiles_estado_v02.csv` y en la app como aproximado. El agua química no está incluida (solo la cuantitativa).
5. **El grupo 1 se define por la presión hídrica.** El estrés hídrico toma valores superiores a 100 en los datos (mediana 295 en ese grupo).
6. **No incluye población, paro, viento ni riesgos naturales.** Un municipio de un perfil puede tener un riesgo natural alto o bajo; eso se consulta aparte.
7. **Atípicos:** `es_atipico` vale 0 en todos los municipios porque **no se evalúa en v02**. En v01 salía de un DBSCAN sobre variables con valores extremos (población); los índices de v02 son percentiles de 0 a 100 y no tienen extremos. El campo se mantiene porque la API y la base de datos lo esperan.
8. **Nombres y descripciones provisionales**, pendientes de Gema.
9. **Ajustado con todos los municipios**: no se ha medido cómo se comporta con municipios nuevos.
10. Modelo **exploratorio**: no usar para decidir inversiones ni para clasificar municipios como adecuados o no.
11. **Cercano no es misma cuenca ni mismo relieve.** La distancia es en línea recta entre un punto por municipio: dos municipios cercanos pueden estar en cuencas distintas, y en municipios muy extensos la distancia entre puntos no es la distancia entre sus límites.

## Cómo regenerarlo

```bash
source .venv/Scripts/activate
# Orden estricto: 01A, 03A y 03B (datos y dimensiones); después 04, 05, 06, 07, 08 y 10
jupyter nbconvert --to notebook --execute --inplace notebooks/07_perfiles_municipios.ipynb
PYTHONPATH=src python -m pytest tests/ml -q
```

Cada notebook de la serie 04–10 comprueba al empezar que el anterior se ha ejecutado (ver `notebooks/README.md`). Si cambian los datos o las variables, hay que subir la versión (`perfiles.py`) y revisar nombres y descripciones.

## Archivos relacionados

- `src/sitewise/ml/indices.py` (índices y estimación con vecinos), `src/sitewise/ml/experimentos.py` (métricas de K-Means), `src/sitewise/ml/perfiles.py` (nombres y tabla), `src/sitewise/ml/cercanos.py` (municipios cercanos)
- `notebooks/04_decision_variables_perfil.ipynb`, `05_clustering_kmeans.ipynb`, `06_mlflow_experimentos.ipynb`, `07_perfiles_municipios.ipynb`, `08_estimaciones_vecinos_app.ipynb`, `10_municipios_cercanos.ipynb`
- `docs/methodology/seleccion_variables_ml.md` (criterios de selección de variables)
- `src/sitewise/ml/pipeline.py` es el pipeline de v01 (PCA); ya no lo usa ningún notebook
