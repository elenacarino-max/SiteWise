# Agua estimada exclusivamente en la app

## Instalación

Desde la raíz del repositorio, copiar las carpetas `notebooks/` y `data/` de este paquete respetando sus rutas. Se sustituye únicamente el notebook 03; el CSV queda en `data/processed/sitewise_ml/agua_estimada_vecinos_v01.csv`, donde también lo genera el notebook 08.

El notebook 03 se ha preparado a partir de la versión de `main` identificada por el blob `dc18bd3d350db7d43b0bfff0bef91739a5da8519`. Si hay cambios locales adicionales en el 03, comparar antes de sustituirlo.

## Ejecución

Con los ficheros v03 existentes, abrir `notebooks/03_dataset_consolidado_empleo_viento_agua.ipynb`. En un kernel limpio, ejecutar primero:

```python
from pathlib import Path
import numpy as np
import pandas as pd
from IPython.display import display
ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents]
            if (p / 'data').is_dir() and (p / 'notebooks').is_dir())
```

Después ejecutar las dos últimas celdas de código del notebook: la carga de `valores.csv` y la exportación de la opción A. No hace falta repetir el procesamiento geoespacial de empleo, viento y agua.

Se espera el mensaje `Opción A validada: 722 estimaciones cuantitativas en la app; originales intactos.`

## Resultado y procedencia

- `valores_app.csv` y `dataset_municipal_app.csv` incorporan 722 estimaciones del indicador `agua_subterranea_mal_estado_cuantitativo_pct`, con `estado_app = aproximado`.
- `valores.csv` y `dataset_municipal.csv` no se escriben; se comprueba que su SHA-256 permanece intacto. La cobertura original continúa siendo 7.410 municipios con valor, y 722 sin masa catalogada.
- El indicador químico conserva sus 722 ausencias. No se aplican estimaciones de paro ni de viento a la app.
- En el formato largo, `estado` conserva el estado de origen; `estado_app` es el estado para mostrar. Se conservan `valor_original`, `metodo_original` y `naturaleza_original`. `metodo` y `naturaleza` describen el valor actual. `estimado_app`, `fuente_estimacion`, el número de vecinos y las distancias identifican la estimación.
- En el formato ancho se conserva `estado__...` de origen y se añade `valor_original__...`, la marca de estimación, su método y distancias. El valor de la columna del indicador y su `estado_app__...` coinciden con el formato largo.
- La correspondencia de estados es la misma que antes; no se añade ningún estado nuevo.

La ficha debe mostrar «Aproximado · estimación por proximidad geográfica», y consultar el método actualizado. La fuente original describe los datos de partida, no una medición oficial del municipio estimado. No se acredita caudal ni suministro. La interfaz debe comprobarse después de cargar los nuevos CSV: no ha sido ejecutada en esta entrega.

## Método y límites

El notebook 08 selecciona el indicador cuantitativo, calcula la distancia haversine entre coordenadas municipales y promedia los cinco municipios más cercanos con valor disponible. El CSV redondea el valor a dos decimales y las distancias a uno. No se recalculan estimaciones en el 03.

La comprobación del 08 es un error absoluto medio al excluir cada municipio con dato y predecirlo con sus vecinos. No es una validación espacial independiente ni garantiza ese error en los 722 casos sin masa. El quinto vecino llega a 66,9 km en el CSV revisado. Se conserva la propuesta aprobada sin introducir nuevos umbrales.

## Comprobaciones realizadas

- Exportación y relectura con el consolidado v03 disponible: 8.132 valores cuantitativos en la app, de los que 722 son estimados; indicador químico intacto.
- Originales idénticos por SHA-256; restantes indicadores y metadatos de origen conservados.
- Coherencia de valores y estados entre los formatos largo y ancho.
- Segunda ejecución sin acumulación de columnas ni cambios de resultado.
- Rechazo de códigos duplicados y validaciones de ausencias, rangos, cinco vecinos y metadatos.
- Las 722 estimaciones y sus distancias se han reproducido con NumPy usando haversine y coinciden con el CSV al redondeo publicado.
- JSON del notebook y sintaxis de sus celdas de código comprobados. No se ha repetido la ETL geoespacial completa ni ejecutado la interfaz.

Los CSV de datos siguen excluidos de Git según las reglas actuales del repositorio. El notebook es el cambio de código que debe revisarse; este paquete no hace commit ni push.
