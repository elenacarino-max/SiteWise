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
| 04 | `04_seleccion_variables_ml.ipynb` | Selección de variables para ML. |
| 05 | `05_clustering_kmeans.ipynb` | Experimentación con K-Means. |
| 06 | `06_clustering_dbscan.ipynb` | Experimentación con DBSCAN. |
| 07 | `07_mlflow_experimentos.ipynb` | Registro de experimentos. |
| 08 | `08_mlflow_segunda_prueba.ipynb` | Segunda fase de experimentación. |
| 09 | `09_preparacion_datos_app.ipynb` | Preparación de datos para la aplicación. |
| 10 | `10_perfiles_municipios.ipynb` | Perfiles municipales. |
| 11 | `11_municipios_cercanos.ipynb` | Análisis de proximidad municipal. |

## Datos y reproducibilidad

- Los datos originales se distribuyen mediante Google Drive.
- La carpeta de riesgos naturales debe colocarse en `data/raw/riesgos_naturales/`.
- Los datos procesados se generan localmente mediante la ejecución de los notebooks.
- No se incluyen datasets en GitHub.
- Instalar las dependencias de `requirements.txt` y utilizar el kernel del entorno virtual `.venv`.
- Ejecutar los notebooks siguiendo el orden establecido.
- El notebook 01A puede requerir un tiempo de ejecución elevado debido al tamaño de las fuentes geoespaciales.

## Dimensiones temáticas candidatas

1. Logística e industria.
2. Condicionantes hídricos.
3. Riesgos naturales.
4. Socioeconómico.
5. Recursos y servicios.

Las cinco dimensiones son propuestas experimentales pendientes de validación conjunta entre Data y ML. No constituyen una selección definitiva para clustering.

El dataset v04 candidato no sustituye automáticamente al dataset de producción. Los notebooks 04 y posteriores deberán adaptarse cuando se apruebe la nueva selección de variables.

## Buenas prácticas

- Mantener la trazabilidad de fuentes, transformaciones y estimaciones.
- No confundir ausencia de datos con valores cero.
- Mover el proceso final reproducible a `src/sitewise` y `scripts`.
- No publicar salidas con secretos o datos no autorizados.