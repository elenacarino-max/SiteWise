# Generador de matrices de SiteWise

Permite crear distintas matrices numéricas desde el dataset municipal consolidado,
seleccionando variables y preprocesado en un JSON. No modifica el dataset ni entrena
el clustering. No requiere Rasterio ni GeoPandas.

## Instalación y primera ejecución en Windows / PowerShell

Los cuatro archivos del generador están en `data/processed/generadorMatrices/`:
`generar_matriz.py`, `config_4_variables.json`, `LEEME.md` y
`requirements-matrices.txt`.

Ejecuta todos los comandos siguientes desde la raíz del repositorio. Todas las
rutas son relativas a esa raíz; no es necesario mover los archivos.
El dataset consolidado debe estar disponible localmente en
`data/processed/sitewise_v03/dataset_municipal.csv`.

Con el entorno Python del proyecto activado, instala las dependencias si faltan:

```powershell
python -m pip install -r "data/processed/generadorMatrices/requirements-matrices.txt"
```

Con el entorno Python del proyecto activado, ejecuta en PowerShell:

```powershell
python "data/processed/generadorMatrices/generar_matriz.py" --dataset "data/processed/sitewise_v03/dataset_municipal.csv" --config "data/processed/generadorMatrices/config_4_variables.json" --salida "data/processed/sitewise_ml/prueba_01"
```

El ejemplo reproduce el preprocesado de las cuatro variables acordadas: log1p,
recorte p1-p99 y StandardScaler; las distancias ausentes se rellenan con el máximo
observado solo para ML. PCA retiene al menos el 85 % de la varianza.

## Elegir otras variables

1. Copia `data/processed/generadorMatrices/config_4_variables.json` como
   `data/processed/generadorMatrices/config_prueba_02.json`.
2. En variables, elimina o añade columnas usando sus nombres exactos en el CSV.
3. Configura cada columna según su significado y cobertura.
4. Ejecuta el mismo comando cambiando --config y --salida. La salida debe ser nueva:
   el programa rechaza sobrescribir pruebas existentes. Guarda cada prueba en una
   subcarpeta distinta de `data/processed/sitewise_ml/`, por ejemplo `prueba_02`.

Ejemplo alternativo, sin PCA:

```json
{
  "id": "cod_ine",
  "contexto": ["nombre", "provincia", "ccaa"],
  "variables": {
    "poblacion_2025": {"ausentes": "error", "transformacion": "log1p"},
    "cobertura_ftth_pct": {"ausentes": "error", "transformacion": "ninguna"},
    "viento_100m_media_m_s": {"ausentes": "mediana", "transformacion": "ninguna"}
  },
  "escalado": "standard",
  "pca": null
}
```

Este segundo ejemplo ilustra la configuración; no supone una nueva selección
acordada ni una recomendación automática de imputar por mediana.

## Opciones exactas

| Campo | Valores admitidos |
|---|---|
| ausentes | error (por defecto), eliminar_filas, mediana, media, maximo, constante |
| valor | Número obligatorio cuando hay ausencias y se usa constante |
| transformacion | ninguna (por defecto), log1p, sqrt |
| recorte | null o dos cuantiles, por ejemplo [0.01, 0.99] |
| escalado | standard (por defecto), robust, minmax, ninguno |
| pca | null para desactivar, fracción como 0.85, entero como 2 |

Orden: selección → eliminación de filas indicada → imputación → transformación →
recorte → escalado → PCA opcional. Las estadísticas se calculan con las filas retenidas.
Las ausencias no se convierten en cero automáticamente. Para una constante explícita:
`{"ausentes": "constante", "valor": 0}`. Usarla solo si el significado del dato lo justifica.
log1p admite valores mayores que -1; sqrt, no negativos. Las columnas deben ser
numéricas. Los estados real/aproximado/pendiente y las categorías no se codifican ni
filtran automáticamente: si es necesario, preparar antes una entrada filtrada.
Tampoco calcula tasas, elige variables, detecta redundancias ni decide qué imputación
es metodológicamente adecuada. Rechaza variables constantes tras el tratamiento.

## Archivos generados

| Archivo | Uso |
|---|---|
| matriz_original.csv | Variables seleccionadas, sin transformar, de las filas retenidas |
| matriz_imputada.csv | Datos con el relleno elegido, antes de transformaciones |
| matriz_transformada.csv | Datos tras transformación y recorte |
| matriz_ml.csv | Matriz escalada, antes de PCA; sin escalado si se elige ninguno |
| matriz_pca.csv | Componentes para clustering; solo cuando se activa PCA |
| municipios.csv | ID y columnas de contexto para interpretar resultados |
| mascara_imputaciones.csv | Marca qué valores se han rellenado |
| filas_excluidas.csv | IDs descartados por ausencia; vacío si no se descartó ninguno |
| informe.json | Configuración, cobertura, parámetros, versiones y huella del CSV |

Todos los CSV conservan cod_ine como identificador. Cargarlo como texto y excluirlo
siempre del cálculo. Mantener el orden de filas al enlazar los clusters.
Con PCA activado, usar matriz_pca.csv en el modelo sin volver a escalar ni aplicar PCA.
Sin PCA, usar matriz_ml.csv.

```python
import pandas as pd
matriz = pd.read_csv('data/processed/sitewise_ml/prueba_01/matriz_pca.csv', dtype={'cod_ine': str})
codigos = matriz['cod_ine'].copy()
X = matriz.drop(columns='cod_ine')
```

El generador ajusta las estadísticas sobre el conjunto de entrada completo para el
clustering exploratorio. Para una evaluación con particiones o para transformar
municipios nuevos con el mismo modelo, se necesita una fase separada de ajuste y
transformación usando los parámetros de entrenamiento. No reajustar una matriz
nueva por separado si se van a comparar coordenadas o asignar clusters existentes.
Los valores imputados son solo para ML: las fichas deben conservar los datos originales.

## Alcance del generador y trabajo pendiente

Esta versión usa NumPy, Pandas y scikit-learn, según
`requirements-matrices.txt`. Es un generador para exploración del conjunto de
entrada; no constituye el pipeline de scikit-learn solicitado en el issue #15.

Antes de evaluar con particiones o transformar datos nuevos con un modelo ya
ajustado, habrá que implementar el ajuste del preprocesado solo con los datos de
entrenamiento y reutilizar ese mismo preprocesado para transformar validación y
nuevos municipios. Esto incluye imputación, límites de recorte, escalado y PCA;
no deben recalcularse por separado sobre validación.

El código permanece por ahora en `data/processed/generadorMatrices/`. Su traslado
a `scripts/` o `src/sitewise/ml/` puede abordarse en una revisión de estructura,
actualizando conjuntamente los comandos y las reglas de `.gitignore`.

Las salidas documentadas se unifican en `data/processed/sitewise_ml/`. Este cambio
de documentación no mueve ni borra matrices de pruebas anteriores.

