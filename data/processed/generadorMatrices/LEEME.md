# Generador de matrices de SiteWise

Permite crear distintas matrices numéricas desde el dataset municipal consolidado,
seleccionando variables y preprocesado en un JSON. No modifica el dataset ni entrena
el clustering. No requiere Rasterio ni GeoPandas.

## Instalación y primera ejecución en Windows / PowerShell

Descomprime los archivos en la raíz del repositorio, por ejemplo:
C:\PROYECTOS_ELE\Final_sidewise

Con el entorno Python del proyecto activado, instala las dependencias si faltan:

```powershell
python -m pip install -r requirements-matrices.txt
```

Ejecuta en PowerShell (ajusta sidewise_v03 a sitewise_v03 si así se llama tu carpeta):

```powershell
python generar_matriz.py --dataset "data/processed/sidewise_v03/dataset_municipal.csv" --config "config_4_variables.json" --salida "data/processed/ml/prueba_01"
```

El ejemplo reproduce el preprocesado de las cuatro variables acordadas: log1p,
recorte p1-p99 y StandardScaler; las distancias ausentes se rellenan con el máximo
observado solo para ML. PCA retiene al menos el 85 % de la varianza.

## Elegir otras variables

1. Copia config_4_variables.json con otro nombre, por ejemplo config_prueba_02.json.
2. En variables, elimina o añade columnas usando sus nombres exactos en el CSV.
3. Configura cada columna según su significado y cobertura.
4. Ejecuta el mismo comando cambiando --config y --salida. La salida debe ser nueva:
   el programa rechaza sobrescribir pruebas existentes.

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
matriz = pd.read_csv('data/processed/ml/prueba_01/matriz_pca.csv', dtype={'cod_ine': str})
codigos = matriz['cod_ine'].copy()
X = matriz.drop(columns='cod_ine')
```

El generador ajusta las estadísticas sobre el conjunto de entrada completo para el
clustering exploratorio. Para una evaluación con particiones o para transformar
municipios nuevos con el mismo modelo, se necesita una fase separada de ajuste y
transformación usando los parámetros de entrenamiento. No reajustar una matriz
nueva por separado si se van a comparar coordenadas o asignar clusters existentes.
Los valores imputados son solo para ML: las fichas deben conservar los datos originales.
