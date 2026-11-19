# Ejecución en orden: 03 → 04–08 → 09

## Instalar esta corrección

1. Copiar `notebooks/03_dataset_consolidado_empleo_viento_agua.ipynb` sobre el 03 actual.
2. Añadir `notebooks/09_preparacion_datos_app.ipynb`.
3. Conservar el CSV de estimaciones en `data/processed/sitewise_ml/agua_estimada_vecinos_v01.csv`. Se incluye una copia del CSV revisado, también generado por el notebook 08.

El 03 se ha preparado sobre la versión consultada de la rama `feat/dataset-municipal`, conservando sus primeras 14 celdas (ETL y validación de los originales). Se han retirado las celdas posteriores de carga y exportación para la app. Si existen cambios locales adicionales, comparar antes de sustituir el archivo.

## Ejecutar

**Si partes de cero:** ejecutar los notebooks 01–08 en orden y después el 09. La sección 1 del 08 genera el CSV de estimaciones; el 09 lo lee y genera los archivos finales de la app. Nunca hay que volver al 03.

**Si ya tienes el consolidado v03 y el CSV de estimaciones:** abrir únicamente el notebook 09, seleccionar el entorno con Pandas y NumPy y pulsar «Ejecutar todo». El 09 carga por sí mismo todas sus variables y funciona desde la raíz del proyecto o desde `notebooks/`.

El 03 termina con los datos originales. La salida final para la aplicación se genera en el 09. Los notebooks 04–08 siguen trabajando con los originales y sus derivados de ML, sin depender de los archivos de la app.

## Qué hace el 09

- Lee `data/processed/sitewise_v03/valores.csv` y `dataset_municipal.csv`.
- Lee `data/processed/sitewise_ml/agua_estimada_vecinos_v01.csv`.
- Incorpora 722 estimaciones únicamente al indicador `agua_subterranea_mal_estado_cuantitativo_pct` en los datos de la app.
- Exporta `valores_app.csv` y `dataset_municipal_app.csv` en `data/processed/sitewise_v03/`, con `estado_app = aproximado`, método y distancias.
- Conserva `estado` como estado de origen; la interfaz debe consultar `estado_app`. Conserva valor, método y naturaleza originales en columnas específicas.
- No modifica los CSV originales ni el indicador químico. Comprueba los hashes originales antes y después.
- Mantiene la correspondencia de estados existente. Rechaza CSV ausentes, códigos duplicados, valores fuera de rango o estimaciones que no coincidan con las ausencias originales.

## Límites y revisión visual

La estimación es la media del indicador de los cinco municipios más cercanos con valor disponible, usando distancia haversine entre coordenadas. No acredita caudal ni suministro. El error absoluto medio del notebook 08 no equivale a una garantía de error individual ni a una validación espacial independiente. No se han añadido umbrales nuevos a la propuesta acordada.

En la ficha debe verse «Aproximado · estimación por proximidad geográfica», junto con su método. La interfaz todavía debe comprobarse con los CSV generados.

Esta entrega prepara los archivos para sustituirlos en tu ordenador; no hace commit ni push en GitHub. Los datasets siguen sujetos al `.gitignore` actual; el cambio de código son los notebooks 03 y 09.
