# SiteWise · entrega conjunta v0.3

Preparada el 14/11/2026. Esta entrega reúne las dos anteriores y añade empleo registrado, recurso eólico y estado de las masas de agua subterránea. Incluye los originales utilizados, los resultados, tres notebooks explicativos con gráficos y la documentación de los cruces y las limitaciones. No se ha hecho ningún push ni se ha modificado tu carpeta de Windows.

## Incorporación en tu proyecto

1. Descomprime el ZIP en una carpeta temporal. Copia `notebooks`, `data`, `docs` y los archivos `LEEME_*.md` a `C:\PROYECTOS_ELE\Final_sidewise`. Deben quedar directamente bajo la raíz del proyecto, sin una carpeta intermedia. Al combinar carpetas se actualizan los notebooks de esta entrega y `notebooks/requirements-dataset.txt`; conserva una copia si los habéis editado vosotros. El README general y el código de la aplicación no van en este paquete.
2. Desde la terminal de ese proyecto, con **el mismo `.venv` que ya tienes** activo:

```powershell
python -m pip install -r notebooks/requirements-dataset.txt
```

3. En VS Code, abre `notebooks/03_dataset_consolidado_empleo_viento_agua.ipynb` y selecciona el Python de `.venv` como kernel. No hace falta crear otro entorno. Las explicaciones, gráficos y salidas ya están guardados.
4. Para repetir esta ampliación, usa **Ejecutar todo** en el notebook 03. Utiliza las salidas v0.2 incluidas; no necesitas ejecutar los tres notebooks antes de probar la aplicación. Los cálculos de esta ampliación funcionan sin conexión.
5. Para empezar a conectar el backend, usa `data/processed/sitewise_v03/valores.csv`, `indicadores.csv` y `municipios.csv`. El archivo ancho `dataset_municipal.csv` sirve para explorar y hacer prototipos.

Los notebooks 01 y 02 explican y permiten reproducir las fases anteriores con las copias incluidas. Algunas celdas de descarga o reconstrucción de recortes mundiales pueden necesitar internet; se entregan los recortes españoles para trabajar sin repetir esas descargas.

## Archivos que debe conocer el equipo

| Archivo o carpeta | Contenido y uso |
| --- | --- |
| `notebooks/01_dataset_municipal.ipynb` | Base municipal: población, conectividad, red eléctrica provincial, incendios e histórico de inundaciones. |
| `notebooks/02_ampliacion_solar_agua_logistica_suelo.ipynb` | Radiación solar, Aqueduct, proximidad logística y superficie industrial cartografiada. |
| `notebooks/03_dataset_consolidado_empleo_viento_agua.ipynb` | Nueva ETL y unión definitiva para esta entrega. |
| `data/raw/sitewise_v03/` | ZIP original SEPE, TIFF eólico, CSV de estados del agua y geometrías WFS oficiales; también archivos nacionales auxiliares no repartidos entre municipios. |
| `data/processed/sitewise_v03/municipios.csv` | Maestro territorial, identificadores y punto interior representativo. |
| `data/processed/sitewise_v03/indicadores.csv` | Diccionario: definición, unidad, sentido, fuente, período, método y limitaciones. |
| `data/processed/sitewise_v03/valores.csv` | Tabla larga para el backend, con valor y estado de cada indicador por municipio. |
| `data/processed/sitewise_v03/dataset_municipal.csv` | Una fila por municipio con valores, estados y niveles de origen; añade controles de cobertura del viento y del agua subterránea. |
| `data/processed/sitewise_v03/sepe_*original.csv.gz` | Series mensuales originales con celdas protegidas y trazabilidad. Son CSV comprimidos; pandas los lee directamente. |
| `data/processed/sitewise_v03/sepe_*armonizado.csv.gz` | Series con códigos antiguos fusionados mediante correspondencias documentadas. |
| `data/processed/sitewise_v03/empleo_municipal.csv` | Último mes disponible y comparación con el mismo mes del año anterior. |
| `data/processed/sitewise_v03/agua_subterranea_intersecciones.csv.gz` | Cruces de municipios y masas, antes de disolver horizontes solapados. No sumar sin aplicar el método del notebook. |
| `data/processed/sitewise_v03/validacion.csv` | Controles ejecutados y resultados. |
| `docs/data/sitewise_v03/` | Metodología, manifiesto SHA-256, resumen de ejecución y vista HTML del notebook. |
| `data/processed/sitewise_v01/municipios.geojson` | Geometrías del mapa. Son límites generalizados GISCO; no sirven para una decisión catastral. |

## Cómo leer los datos sin perder información

```python
import pandas as pd
ruta = 'data/processed/sitewise_v03/'
municipios = pd.read_csv(ruta + 'municipios.csv',
                         dtype={'cod_ine': str, 'cod_provincia': str})
valores = pd.read_csv(ruta + 'valores.csv', dtype={'cod_ine': str},
                      low_memory=False)
indicadores = pd.read_csv(ruta + 'indicadores.csv')
```

`cod_ine` tiene cinco caracteres, incluidos los ceros iniciales. No conviertas los códigos en números. `valor` vacío significa desconocido; consulta `estado`. Los recuentos de paro protegidos no se sustituyen por cero. No se genera una tasa de paro dividiendo paro por población total.

Las dos métricas nuevas de agua usan como denominador la superficie cubierta por masas catalogadas dentro del municipio; revisa `cobertura_masas_pct`. Las geometrías pueden representar horizontes superpuestos, que se unen antes de medir áreas. Una masa en mal estado no implica que toda el agua municipal lo esté. Las evaluaciones son históricas y heterogéneas; el ciclo de planificación 2022–2027 no es una observación de 2026.

## Lo que permite y lo que queda por validar

La base permite comparar municipios y explorar criterios por actividad. Se conservan los niveles de origen: los datos provinciales anteriores siguen señalados como aproximaciones; no se añaden tablas de agregados autonómicos.

| Necesidad | Estado de la entrega |
| --- | --- |
| Solar y viento | Recurso territorial modelado. No dimensiona instalaciones. La versión y el período exactos de la copia eólica no se han confirmado. |
| Agua | Contexto Aqueduct y estado cuantitativo/químico de masas subterráneas. El caudal contratable y la concesión deben verificarse con operador o confederación. |
| Carretera | Distancia al eje cartografiado de autovía/autopista. Pendiente acceso real y ruta. Un nodo de cruce de la red no se da por válido como enlace de acceso. |
| Ferrocarril | Proximidad a instalaciones TTM/intermodales del catálogo. Pendientes actividad, servicios y capacidad actuales. |
| Suelo industrial | Superficie industrial cartografiada. No es inventario de parcelas libres ni de precios. Debe comprobarse disponibilidad y compatibilidad urbanística en municipios finalistas. |
| Empleo | Paro y contratos registrados, con datos protegidos respetados. No acredita cualificación ni disponibilidad de personas. |
| Inundaciones | Histórico anterior conservado; exposición inundable adicional fuera del alcance acordado. |
| Recomendaciones por actividad | Pesos, umbrales y criterios de exclusión pendientes de acuerdo del equipo. No se entrega un ranking inventado. |

Los archivos nacionales auxiliares del atlas eólico no contienen detalle municipal aprovechable para otros indicadores. No se replica una curva nacional en todos los municipios. Weibull A no es velocidad media; no se usa como sustituto.

## GitHub y distribución de datos

El ZIP es la entrega de datos y documentación para el equipo. Los originales incluyen un GeoPackage de unos 200 MB y no deben forzarse a Git. El `.gitignore` del proyecto ya excluye las carpetas de datos generados y originales. Subid notebooks, requisitos y documentación siguiendo vuestro flujo de ramas; distribuid este paquete por el canal de archivos que acordéis. No se ha publicado ningún cambio.

Las fuentes mantienen sus atribuciones y condiciones; véanse los manifiestos y diccionarios de las tres versiones. Poder consultar un servicio público no equivale a disponer de una licencia genérica para cualquier redistribución comercial. No se otorga una licencia propia a los datos de terceros.
