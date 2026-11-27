# Notebooks — SiteWise

Exploración, preparación de datos, análisis y experimentación de Machine Learning.

## Orden de ejecución

| Orden | Notebook | Función |
|---|---|---|
| 01 | `01_dataset_municipal.ipynb` | Dataset municipal base. |
| 01A | `01A_revision_riesgos_naturales.ipynb` | Procesamiento de incendios e inundaciones. |
| 02 | `02_ampliacion_solar_agua_logistica_suelo.ipynb` | Ampliación de indicadores territoriales. |
| 03 | `03_dataset_consolidado_empleo_viento_agua.ipynb` | Consolidación del dataset v03. |
| 03A | `03A_validacion_agrupacion_variables.ipynb` | Validación del dataset v04 candidato y agrupación temática de los 43 indicadores. |
| 03B | `03B_construccion_dimensiones_tematicas.ipynb` | Feature Engineering y construcción de cinco dimensiones candidatas. |
| 04 | `04_decision_variables_perfil.ipynb` | Qué variable va a cada uso (perfil, datos sueltos, scoring). **Guarda** `variables_perfil_v02.csv`. |
| 05 | `05_clustering_kmeans.ipynb` | K-Means v02: cuántos grupos y qué entradas. **Lee** la salida del 04. **Guarda** `experimentos_v02.csv` y `modelo_elegido_v02.json`. |
| 06 | `06_mlflow_experimentos.ipynb` | Registra en MLflow lo que guardó el 05 (no recalcula). |
| 07 | `07_perfiles_municipios.ipynb` | Perfil final v02. **Lee** K y entradas de `modelo_elegido_v02.json`. **Guarda** los ficheros de `data/reference/`. |
| 08 | `08_estimaciones_vecinos_app.ipynb` | Agua estimada con vecinos para la app. **Comprueba** que coincide con lo marcado en el perfil del 07. **Guarda** el fichero que lee el 09. |
| 09 | `09_preparacion_datos_app.ipynb` | Preparación de datos para la aplicación (lee la salida del 08). |
| 10 | `10_municipios_cercanos.ipynb` | Municipios cercanos para la API y el RAG (no usa resultados del 09; solo cierra el orden). |

**Orden estricto de 04 a 10:** cada notebook comprueba al empezar que el anterior se ha ejecutado y, si no, se detiene con un mensaje que dice cuál ejecutar antes. Los ficheros intermedios se guardan en `data/processed/sitewise_ml/` (no se suben a Git).

## Datos y reproducibilidad

- Los datos originales se distribuyen mediante Google Drive.
- La carpeta de riesgos naturales debe colocarse en `data/raw/riesgos_naturales/`.
- Los datos procesados se generan localmente mediante la ejecución de los notebooks.
- No se incluyen datasets en GitHub.
- Instalar las dependencias de `requirements.txt` y utilizar el kernel del entorno virtual `.venv`.
- Ejecutar los notebooks siguiendo el orden establecido. El cálculo de los índices del perfil y de los experimentos está en `src/sitewise/ml/` (`indices.py` y `experimentos.py`), con tests, y los notebooks 05 a 08 lo importan.
- El notebook 01A puede requerir un tiempo de ejecución elevado debido al tamaño de las fuentes geoespaciales.

## Dimensiones temáticas candidatas

1. Logística e industria.
2. Condicionantes hídricos.
3. Riesgos naturales.
4. Socioeconómico.
5. Recursos y servicios.

Las cinco dimensiones son propuestas experimentales. Para el perfil de municipio (v02) se usan tres: logística, hídrica y conectividad (esta última, una de las alternativas de 03B). Las demás se conservan como datos sueltos para filtros, scoring y RAG.

El dataset v04 candidato no sustituye automáticamente al dataset de producción. El perfil vigente es v02 (notebooks 04 a 08). El clustering v01 (7 variables + PCA, K=5) y sus notebooks antiguos siguen en el historial de Git (commit `bc30250`) y los CSV `*_v01` en `data/reference/`.

## Buenas prácticas

- Mantener la trazabilidad de fuentes, transformaciones y estimaciones.
- No confundir ausencia de datos con valores cero.
- Mover el proceso final reproducible a `src/sitewise` y `scripts`.
- No publicar salidas con secretos o datos no autorizados.