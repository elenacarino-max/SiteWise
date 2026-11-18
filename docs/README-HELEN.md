# Aportación de ML al README principal (Helen)

Material para quien redacte el `README.md` general. Solo recoge la parte de ML y calidad de datos de Helen, con cifras del 18 de noviembre de 2026.

## 1. Qué hace el módulo de ML

Agrupa los 8.132 municipios en **perfiles territoriales parecidos** (clustering), para poder decir «este municipio se parece a estos otros». Los grupos son **exploratorios**: el número de grupos (K=5) es provisional.

## 2. Qué se ha hecho

| Paso | Issue | Dónde |
|---|---|---|
| Selección de variables para el clustering | #12 | `notebooks/04_seleccion_variables_ml.ipynb` y `docs/methodology/seleccion_variables_ml.md` |
| Primera prueba de clustering con 4 variables (K-Means y DBSCAN) | #14 | Notebooks 05 y 06 |
| Experimentos registrados en MLflow | #15 | Notebooks 07 y 08 |
| Perfiles de los grupos y ficha del modelo | #16 | En curso |

## 3. Variables del clustering

- **Primera prueba (4 variables):** población 2025, % de suelo industrial, distancia a autovía y distancia a terminal ferroviaria.
- **Segunda prueba (7 variables):** las 4 anteriores más tasa de paro, viento a 100 m y agua subterránea en mal estado cuantitativo.
- **Agua subterránea:** presión sobre los acuíferos (superficie en mal estado cuantitativo), no inundaciones.
- El clustering describe el perfil del territorio. No incluye amenazas naturales ni el riesgo, que se calcula aparte en la puntuación.

Detalle de cada variable y de los ficheros derivados: `docs/governance/DICCIONARIO_DATASET.md` (sección 7).

## 4. Cómo se prepara cada variable

1. Los huecos de distancia (islas y 6 casos peninsulares) se rellenan con el máximo observado.
2. `log1p` en las variables muy asimétricas y recorte a los percentiles 1–99.
3. Escalado con `StandardScaler`.
4. PCA hasta explicar al menos el 85 % de la varianza.

**Tasa de paro:** paro registrado entre población total, por 100 habitantes. Dos casos especiales:

| Caso | Municipios | Regla |
|---|---|---|
| Paro oculto (el SEPE oculta cifras menores de 5) | 1.587 | Se calcula con 2,5 parados |
| Celda en blanco en la fuente | 265 | Se calcula con 1 parado |

**Agua subterránea:** 722 municipios no tienen masa de agua catalogada. Su valor se estima con la media de los 5 municipios con dato más cercanos en el mapa (la geografía predice el agua con un error medio de 4,9 puntos, frente a 16,5 poniendo 0). En la app se mostrará como `aproximado`.

**Importante:** el paro rellenado es **solo para entrenar** y la aplicación muestra el dato observado y su estado (`pendiente`). El agua estimada se muestra como `aproximado`: la propuesta está en `data/processed/sitewise_ml/agua_estimada_vecinos_v01.csv` y falta incorporarla al dataset.

## 5. Resultados

- **Primera prueba:** K-Means con K=5 (provisional). DBSCAN se usa solo para detectar municipios atípicos (360).
- **Segunda prueba:** con 7 variables los grupos son menos nítidos (Silhouette de K=5: 0,27 con 4 variables y 0,23 con 7).
- Los resultados son estables entre semillas (ARI medio ≥ 0,97).

## 6. MLflow

Cada prueba (variables, K, métricas y configuración) se registra en MLflow, con SQLite como almacén (`mlruns/mlflow.db`). Versión fijada: `mlflow==3.18.0`.

```powershell
python -m mlflow ui --backend-store-uri sqlite:///mlruns/mlflow.db
```

`mlruns/` y `data/processed/` no se suben a Git: cada persona los regenera ejecutando los notebooks.

## 7. Cómo reproducirlo

```powershell
python -m pip install -r requirements.txt
```

Ejecutar en orden los notebooks 04 a 08 (los resultados se guardan en `data/processed/sitewise_ml/`). Cada ejecución completa del 07 o del 08 añade ejecuciones nuevas a MLflow.

## 8. Limitaciones que conviene mencionar

- Los grupos son provisionales (K=5, sin nombre de perfil todavía).
- El preprocesado se ajusta con todos los municipios. Para evaluar con particiones habrá que ajustarlo solo con los de entrenamiento.
- El agua estimada de los 722 municipios sin masa catalogada es una aproximación (los 722 están algo más lejos de sus vecinos que el resto), y por eso se marca como `aproximado`.
- En los municipios con paro oculto o en blanco, la tasa de paro depende de la población por construcción.

## 9. Texto propuesto para el README general

> **Segmentación de municipios.** SiteWise agrupa los 8.132 municipios españoles en perfiles territoriales parecidos mediante clustering (K-Means, con DBSCAN para detectar municipios atípicos). La entrada es una matriz numérica construida a partir del dataset municipal con un generador configurable (`data/processed/generadorMatrices/`) y cada experimento se registra en MLflow. Los grupos son exploratorios. Los valores rellenados para entrenar (huecos de paro y de distancias) no se muestran en la aplicación, que enseña el dato observado y su estado; el agua subterránea estimada para los municipios sin masa catalogada se muestra como `aproximado`.

Enlaces recomendados: `docs/governance/DICCIONARIO_DATASET.md`, `docs/methodology/seleccion_variables_ml.md` y `data/processed/generadorMatrices/LEEME.md`.
