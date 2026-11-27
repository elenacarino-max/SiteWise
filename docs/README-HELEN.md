# Aportación de ML al README principal (Helen)

Material para quien redacte el `README.md` general. Solo recoge la parte de ML y calidad de datos de Helen, actualizada el 27 de noviembre de 2026 (modelo v02).

## 1. Qué hace el módulo de ML

Agrupa los municipios en **4 perfiles** según su logística, su presión hídrica y su conectividad digital, para poder decir «este municipio es de este tipo». El perfil **describe**; no puntúa. El scoring por actividad **evalúa** y la IA **explica**. Los grupos son **exploratorios**, y sus nombres son provisionales (los cierra Gema).

## 2. Qué se ha hecho

| Paso | Issue | Dónde |
|---|---|---|
| Qué variable va a cada uso (perfil, datos sueltos, scoring) | #12 | `notebooks/04_decision_variables_perfil.ipynb` y `docs/methodology/seleccion_variables_ml.md` |
| Experimentos de K-Means: cuántos grupos y qué entradas | #14 | `notebooks/05_clustering_kmeans.ipynb` |
| Experimentos registrados en MLflow | #15 | `notebooks/06_mlflow_experimentos.ipynb` |
| Perfiles de los grupos y ficha del modelo | #16 | `notebooks/07_perfiles_municipios.ipynb` y `docs/methodology/model_card_clustering.md` |
| Agua estimada con municipios cercanos para la app | #16 | `notebooks/08_estimaciones_vecinos_app.ipynb` |
| Municipios cercanos para la API y el RAG | #16 | `notebooks/10_municipios_cercanos.ipynb` |
| Cálculo de índices y de experimentos en código, con tests | #15 | `src/sitewise/ml/indices.py`, `src/sitewise/ml/experimentos.py` y `tests/ml/` |

El modelo anterior (v01: 7 variables, PCA y K=5) se sustituyó tras la revisión técnica. Sus notebooks siguen en el historial de Git (commit `bc30250`).

## 3. Variables del perfil

Tres índices de 0 a 100, que son las 3 entradas del clustering:

- **Logística:** % de suelo industrial, distancia a autovía y distancia a terminal de mercancías.
- **Hídrica:** estrés hídrico y agua subterránea en mal estado cuantitativo (presión sobre los acuíferos, no inundaciones).
- **Conectividad:** fibra FTTH y 5G.

Población, paro, viento, irradiación y riesgos naturales **no entran**: quedan como datos sueltos para filtros, scoring por actividad y RAG. El clustering no incluye amenazas naturales ni el riesgo, que se calcula aparte.

Detalle de cada variable y de los ficheros derivados: `docs/governance/DICCIONARIO_DATASET.md` (sección 7).

## 4. Cómo se prepara cada variable

1. Cada componente se convierte en **percentil de 0 a 100** (rango medio); las distancias se invierten, de modo que 100 es lo mejor en logística y conectividad.
2. Cada índice es la media de los percentiles de sus componentes.
3. K-Means directamente sobre los tres índices: no hay PCA ni escalado, porque ya están en la misma escala.

**Huecos:**

| Dato | Municipios | Tratamiento |
|---|---|---|
| Distancia a terminal de mercancías | 161 (Baleares, Canarias, Ceuta, Melilla y 4 peninsulares) | No se imputa: sin perfil |
| Agua subterránea (acuíferos) | 722 | Media de los 5 municipios cercanos con dato; se marca como aproximado |
| Estrés hídrico | 24 | Igual que el anterior |

**Agua subterránea:** la estimación con vecinos se validó ocultando municipios con dato y estimándolos con vecinos de **otras provincias**: error medio de 12,8 puntos, frente a 16,5 poniendo 0 y 26,1 con la media de todos los municipios; correlación con el valor real de 0,67. Mejora a las alternativas, pero deja un error apreciable: en la app se muestra como `aproximado`.

**Importante:** los valores estimados se usan para el índice hídrica y se muestran como `aproximado`; la app nunca los presenta como dato medido. Elena ha decidido incorporarlos solo a los ficheros de la app (`valores_app.csv` y `dataset_municipal_app.csv`), sin tocar `valores.csv`. El fichero lo genera el notebook 08 en `data/processed/sitewise_ml/agua_estimada_vecinos_v01.csv`.

## 5. Resultados

- **K-Means con K=4.** No lo elige una métrica: el silhouette es más alto con K=2 (0,308) y baja hasta 0,255 con K=8 (0,285 con K=4). Se eligió 4 porque es el menor número de grupos que separa a los municipios de poca logística mal conectados de los que tienen buena conectividad y deja cada perfil explicable en una frase. K=3 también sería defendible.
- **Cobertura:** 7.971 de 8.132 municipios con perfil (98,0 %).
- **Alternativas de entrada** (notebook 05): añadir el índice natural (JRC) dejaría solo el 49,5 % de los municipios con perfil, por eso se descarta.
- Los grupos son estables entre semillas (ARI mínimo 0,99).
- **Atípicos:** `es_atipico` vale 0 en todos: no se evalúa en v02 (los índices son percentiles y no tienen valores extremos).

## 6. MLflow

Cada prueba (entradas, K, métricas y configuración) se registra en MLflow desde el notebook 06, con SQLite como almacén (`mlruns/mlflow.db`). Versión fijada: `mlflow==3.18.0`.

```bash
python -m mlflow ui --backend-store-uri sqlite:///mlruns/mlflow.db
```

`mlruns/` y `data/processed/` no se suben a Git: cada persona los regenera ejecutando los notebooks.

## 7. Cómo reproducirlo

```bash
python -m pip install -r requirements.txt
python -m pytest tests/ml -v
```

Ejecutar en orden los notebooks 01A, 03A y 03B (datos y dimensiones) y después del 04 al 08 y el 10. Cada notebook de la serie 04–10 comprueba al empezar que el anterior se ha ejecutado (ver `notebooks/README.md`). Cada ejecución completa del 06 añade ejecuciones nuevas a MLflow.

Para calcular los índices desde código, sin pasar por los notebooks:

```python
from sitewise.ml.indices import construir_indices

indices = construir_indices(datos, componentes)  # idx_logistica, idx_hidrica, idx_conectividad y marcas de estimado
```

## 8. Limitaciones que conviene mencionar

- K=4 se decide por interpretación, no por una métrica; los grupos son exploratorios y los nombres son provisionales.
- Los índices son percentiles casi uniformes: K-Means corta un continuo y un municipio cerca de la frontera entre dos perfiles podría estar en cualquiera.
- 161 municipios no tienen perfil por falta de distancia a terminal; los 4 peninsulares hay que revisarlos.
- El agua estimada es una aproximación (error medio de 12,8 puntos).
- El modelo se ajusta con los 8.132 municipios a la vez: no se ha medido con municipios nuevos.
- El perfil no incluye población, paro, viento ni riesgos naturales: se consultan aparte.

## 9. Texto propuesto para el README general

> **Perfiles de municipio.** SiteWise agrupa los municipios españoles en 4 perfiles según su logística (suelo industrial, autovía y terminal de mercancías), su presión hídrica y su conectividad digital, mediante K-Means sobre tres índices de 0 a 100. Cada experimento se registra en MLflow. El código reutilizable está en `src/sitewise/ml/` (scikit-learn, con pruebas en `tests/ml/`). Los grupos son exploratorios y describen el territorio: no puntúan. Los valores estimados con municipios cercanos (agua) se muestran siempre como `aproximado`.

Enlaces recomendados: `docs/governance/DICCIONARIO_DATASET.md`, `docs/methodology/seleccion_variables_ml.md` y `docs/methodology/model_card_clustering.md`.
