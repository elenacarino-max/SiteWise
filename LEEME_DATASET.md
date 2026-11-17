# Dataset municipal SiteWise v0.1

Entrega del 13 de noviembre de 2026: 8.132 municipios, 16 indicadores y 130.112 observaciones en formato largo. Hay valores ausentes en los históricos; se mantienen como desconocidos.

## Dónde copiarlo

Descomprime el contenido de este ZIP dentro de `C:\PROYECTOS_ELE\Final_sidewise`. Las carpetas `notebooks`, `data` y `docs` deben quedar directamente dentro de la raíz del proyecto, sin otra carpeta intermedia. Los nombres específicos de esta entrega evitan sobrescribir el README general del repositorio.

## Abrir el notebook

1. Abre el proyecto en VS Code.
2. En la terminal con `.venv` activado, ejecuta `python -m pip install -r notebooks/requirements-dataset.txt`.
3. Abre `notebooks/01_dataset_municipal.ipynb` y selecciona el kernel de `.venv`.
4. Lee las explicaciones y ejecuta todas las celdas en orden.

El notebook contiene resultados guardados y las fuentes están incluidas. Puedes leerlo y usar los resultados sin volver a descargar todo.

## Archivos principales

- `notebooks/01_dataset_municipal.ipynb`: las explicaciones y el ETL completo, con 17 celdas de código ejecutadas.
- `data/raw/sitewise_v01/`: fuentes oficiales congeladas, exportaciones de Access y manifiesto SHA-256.
- `data/processed/sitewise_v01/dataset_municipal.csv`: una fila por municipio, indicadores y estados.
- `data/processed/sitewise_v01/municipios.csv`: identificación, área y punto interior representativo.
- `data/processed/sitewise_v01/municipios.geojson`: geometrías para el mapa, de GISCO 2024, escala generalizada 1:1 millón.
- `data/processed/sitewise_v01/indicadores.csv`: diccionario, unidades, periodos, métodos y limitaciones.
- `data/processed/sitewise_v01/valores.csv`: una fila por municipio e indicador, con origen, periodo y estado.
- `data/processed/sitewise_v01/matriz_base_contexto_infraestructura.csv`: propuesta de variables para exploración; no es un modelo entrenado ni un índice de riesgo.
- `docs/data/sitewise_v01/`: calidad, trazabilidad, incidencias, códigos corregidos, gráficos y resumen.

Al leer CSV en pandas, utiliza `dtype={'cod_ine': str, 'cod_provincia': str}` para conservar ceros iniciales. Se incluyen versiones Parquet de las tablas principales; su regeneración es opcional y requiere `pyarrow`.

## Cobertura y periodos

| Bloque | Periodo | Cobertura |
| --- | --- | --- |
| Municipios oficiales INE | 2026 | 8.132 municipios |
| Población oficial INE | 2024 y 2025 | 8.132 municipios |
| Conectividad sobre hogares | Junio 2025 | 8.132 municipios |
| TIEPI y NIEPI | 2021 | 52 provincias/ciudades autónomas, replicadas a los municipios y marcadas aproximadas |
| Incendios EGIF | 2006–2015 | 4.375 municipios con datos en la tabla publicada |
| Inundaciones CNIH v27 | Selección 2000–2023 | 2.480 municipios con vínculos documentados; años y territorios con cobertura irregular |
| Geometría GISCO | 2024 | 8.132 municipios |

## Decisiones y límites

- No se fabrican observaciones ni se rellenan ausencias con cero.
- Las fuentes exclusivamente autonómicas no se usan como indicadores. Los nombres de CCAA son atributos territoriales.
- Los índices eléctricos se toman de la fila TOTAL provincial publicada; no se promedian zonas.
- Un duplicado de Alicante con las mismas medidas en EGIF se conserva una sola vez.
- Los códigos CNIH se verifican con el nombre. Se corrigieron 1.624 filas mediante correspondencia única de nombre normalizado y provincia. Se apartaron 79 filas sin resolución suficiente. Todos los casos quedan auditados.
- El catálogo CNIH no contiene registros de eventos fechados 2011–2017 en esta instantánea. Esto no significa que no hubiera inundaciones.
- Se conservan las diferencias de hasta 1 ha entre TOTAL y componentes redondeados de EGIF. Los pequeños excesos de cobertura digital sobre 100 % por coma flotante se corrigen y registran.
- Aún faltan exposición SNCZI, sismicidad validada y recursos/restricciones específicos por actividad (radiación, agua, suelo, logística...). No se presentan pesos, notas ni recomendaciones ficticias.
- Las fuentes tienen condiciones de reutilización propias. La geometría mantiene atribución Eurostat/GISCO y © EuroGeographics. La cartografía generalizada no sirve para validar una parcela.

## Validación realizada

Las 17 celdas Python se ejecutaron en orden en IPython dentro del proceso y se guardaron sus salidas. Este host impide iniciar un kernel Jupyter normal por su restricción de sockets, por lo que esa vía y la ejecución en Windows no se han probado aquí. No hay celdas de ETL dejadas sin ejecutar ni resultados escritos a mano.

Se revisaron los gráficos y una vista renderizada de las explicaciones y resultados. Se recalcularon de forma independiente los recuentos CNIH mediante conjuntos y la asignación de TIEPI/NIEPI desde las filas TOTAL originales. Se verificaron claves, nulos, rangos, cruces y hashes.

## GitHub

El paquete está preparado para la estructura de `elenacarino-max/SiteWise`; no se han publicado cambios en el repositorio. Las carpetas `data/raw` y `data/processed` están excluidas de Git en el proyecto original: es intencionado. El notebook y la documentación pueden versionarse por la PR habitual, y las fuentes/resultados conservarse como entrega de datos.

## Corrección de instalación para Python 3.14

Se cambia pandas 2.2.3 por pandas 2.3.3 y se añade lxml 6.0.2 para la lectura HTML. Se ha resuelto y descargado el conjunto de dependencias con wheels para CPython 3.14 y Windows x64, sin compilar. El ETL se ha vuelto a ejecutar con pandas 2.3.3 en Python 3.12; no se afirma una ejecución local en Windows.
