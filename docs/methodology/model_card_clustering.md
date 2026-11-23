# Ficha del modelo: agrupación de municipios (clustering)

Issue #16 (ML-04) · Versión del modelo: `v01` · Responsable: Helen · Noviembre de 2026

## Para qué sirve

Agrupa los 8.132 municipios de España en **5 perfiles territoriales** para describir cada municipio en lenguaje sencillo (API y asistente RAG). Es un análisis **exploratorio**: describe cómo se parece un municipio a otros, no dice si es bueno o malo para una actividad.

**Un perfil no es un riesgo.** El riesgo se calcula aparte, en la puntuación de cada actividad.

## Datos

- Dataset municipal `sitewise_v03` (8.132 municipios) más la tasa de paro (`dataset_municipal_tasa_paro.csv`).
- Se ajusta con los 8.132 municipios a la vez (no hay conjunto de validación separado).

## Variables (7)

| Variable | Qué mide | Preparación |
|---|---|---|
| `poblacion_2025` | Habitantes | log1p, recorte p1–p99 |
| `suelo_industrial_cartografiado_pct` | % de suelo industrial | log1p, recorte p1–p99 |
| `dist_recta_eje_autovia_km` | Distancia a autovía | huecos = máximo, log1p, recorte |
| `dist_recta_ttm_km` | Distancia a terminal ferroviaria de mercancías | huecos = máximo, log1p, recorte |
| `paro_por_100_hab` | Paro por 100 habitantes | recorte p1–p99 |
| `viento_100m_media_m_s` | Viento medio a 100 m | huecos = mediana |
| `agua_vecinos_pct` | % de territorio sobre acuíferos en mal estado cuantitativo | los huecos se estiman con la media de los 5 municipios vecinos |

## Modelo

Pipeline de scikit-learn (`src/sitewise/ml/pipeline.py`): imputación → transformación → recorte → estandarizado → **PCA (85 % de varianza; 85,6 % con los componentes resultantes)** → **K-Means con K=5**, `n_init=20`, semilla 42.

K=5 y el uso de PCA se acordaron con el equipo.

## Perfiles

Los números de grupo se reordenan por población (0 = municipios más grandes), así no cambian entre ejecuciones. Los nombres y descripciones están en `src/sitewise/ml/perfiles.py`.

| Grupo | Perfil | Municipios | Población (mediana) | Autovía (km) | Paro /100 hab | Viento (m/s) |
|---|---|---|---|---|---|---|
| 0 | Municipios industriales y urbanos | 892 | 11.715 | 1,9 | 4,6 | 4,9 |
| 1 | Pueblos con acuíferos en mal estado | 1.107 | 1.015 | 7,9 | 4,3 | 5,4 |
| 2 | Pueblos bien conectados | 2.145 | 878 | 4,9 | 3,5 | 5,1 |
| 3 | Rural aislado con más paro | 1.504 | 332 | 19,6 | 6,5 | 5,3 |
| 4 | Rural aislado con menos paro y más viento | 2.484 | 175 | 19,1 | 2,5 | 5,9 |

Todas las medianas por grupo están en `data/reference/perfiles_definicion_v01.csv`.

## Calidad

- **Silhouette: 0,230.** Es un valor bajo: los grupos se solapan.
- **Estabilidad: ARI ≥ 0,97** al repetir con otras semillas y submuestras. Los grupos salen casi igual cada vez.

## Fichero de salida

`data/reference/perfiles_municipios_v01.csv` (8.132 filas, ordenado por `cod_ine`): `cod_ine` (texto de 5 dígitos), `cluster` (0–4), `cluster_perfil` (nombre), `es_atipico` (0/1) y `version_modelo`. Lo usan la API (Adriana) y el RAG (Josema).

## Limitaciones

1. **Es un continuo, no cinco bloques separados.** Un municipio cerca de la frontera entre dos perfiles podría estar en cualquiera de los dos.
2. **El paro define los grupos 3 y 4 por construcción.** Los dos son rural aislado; los separa sobre todo el paro, así que su diferencia es relativa.
3. **El grupo 1 se define por el agua.** Casi todos sus municipios comparten acuíferos en mal estado, lo que pesa más que su tamaño.
4. **El agua de 722 municipios está estimada** con los 5 vecinos más cercanos; en el dato final se marca como aproximado. El agua química no está incluida (solo la cuantitativa).
5. **El grupo 0 es muy amplio**: va desde pueblos grandes hasta las mayores ciudades (p10 2.288, p90 77.321 habitantes).
6. **Ajustado con los 8.132 municipios**: no se ha medido cómo se comporta con municipios nuevos.
7. **Atípicos**: `es_atipico` marca 360 municipios que DBSCAN consideró ruido en una prueba inicial con 4 variables, no con las 7 finales. Es solo una pista.
8. **No se comparó sin PCA.** La decisión de usar PCA se tomó con el equipo, sin una comparación detallada en notebook.
9. Modelo **exploratorio**: no usar para decidir inversiones ni para clasificar municipios como adecuados o no.

## Cómo regenerarlo

```bash
source .venv/Scripts/activate
jupyter nbconvert --to notebook --execute --inplace notebooks/10_perfiles_municipios.ipynb
PYTHONPATH=src python -m pytest tests/ml -q
```

Si cambian los datos o las variables, hay que subir `VERSION_MODELO` en `perfiles.py` y revisar nombres y descripciones, porque las cifras de la descripción son medianas actuales.

## Archivos relacionados

- `src/sitewise/ml/pipeline.py` (pipeline), `src/sitewise/ml/perfiles.py` (nombres y tabla)
- `notebooks/10_perfiles_municipios.ipynb` (análisis y generación de ficheros)
- `docs/methodology/seleccion_variables_ml.md` (criterios de selección de variables)
