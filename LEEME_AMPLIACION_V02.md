# SiteWise · ampliación del dataset v0.2

Esta entrega amplía la v0.1 e incluye el suelo industrial aportado el 14/11/2026. Conserva el trabajo anterior. No se ha publicado ningún cambio en GitHub ni en el ordenador de Elena.

## Cómo incorporarla en Windows

1. Descomprime el ZIP y copia las carpetas `notebooks`, `data` y `docs` en `C:\PROYECTOS_ELE\Final_sidewise`. Conserva las carpetas que ya existían. Las salidas nuevas se escriben en `sitewise_v02`; las tablas base incluidas son las de la entrega v0.1.
2. Con `.venv` activo y situado en la raíz del proyecto, ejecuta:

```powershell
python -m pip install -r notebooks/requirements-dataset.txt
```

3. Abre `notebooks/02_ampliacion_solar_agua_logistica_suelo.ipynb` y selecciona como kernel el Python de `.venv`, el mismo en el que instalaste las dependencias. No crees un segundo entorno.
4. Puedes leer las explicaciones y gráficos guardados sin ejecutar. Para repetir el ETL, usa **Ejecutar todo**. No necesitas conexión para los cálculos con las copias incluidas.
5. El backend puede empezar por `data/processed/sitewise_v02/dataset_municipal.csv`. Lee `cod_ine` como texto; los ceros iniciales son parte del identificador.

## Qué añade

- Radiación solar: media territorial de irradiación global horizontal PVGIS/SARAH3, 2005–2023, con cobertura y ponderación por superficie.
- Agua: contexto de estrés y agotamiento hídrico Aqueduct 4.0, baseline objetivo 2019, y proporción de superficie válida con estrés ≥40%. No es caudal industrial disponible ni sequía del mes actual.
- Logística ferroviaria: proximidad a TTM y TTM intermodal del catálogo PISERVI. No se utilizan estaciones de viajeros como sustituto.
- Logística viaria: proximidad al eje de autovías/autopistas del catálogo nacional HERMES. No es distancia a un enlace de acceso ni una ruta.
- Suelo industrial: hectáreas y porcentaje municipal calculados a partir de los 11.968 polígonos MSI del IGN. Se reparan geometrías, se cruzan con municipios y se unen las superficies solapadas antes de sumar. Los municipios sin polígonos tienen 0 cartografiado y un estado explícito; no significa ausencia de industrias ni suelo vacante.

Las distancias parten del punto interior municipal de v0.1, no necesariamente del casco urbano. Se separan componentes terrestres para evitar conexiones ficticias entre islas y Península. Las infraestructuras se describen como **catalogadas**, sin certificar capacidad, apertura ni condiciones de contratación actuales.

## Qué falta de verdad

Consulta `data/processed/sitewise_v02/requisitos_pendientes.csv`:

- Suelo **libre/disponible** con fecha y condiciones: delimitar un área industrial existente no prueba que haya parcelas vacantes.
- Caudal industrial contratable cuando la actividad lo exija: necesita información del operador de abastecimiento/concesiones.
- Acceso real/ruta a autovía y validación del servicio/capacidad ferroviaria si se utilizan como requisito eliminatorio.

No conviertas los requisitos desconocidos en cero ni en un requisito superado. El cero cartografiado del catálogo industrial tiene otro significado: no intersecta polígonos del catálogo, sin demostrar ausencia física. No se han inventado pesos, mínimos por actividad ni puntuaciones de viabilidad.

## Archivos útiles

- `notebooks/02_ampliacion_solar_agua_logistica_suelo.ipynb`: explicación y ETL ejecutado, con gráficos.
- `data/raw/sitewise_v02/fuentes_ampliacion.json`: enlaces, consultas, fechas, atribuciones y SHA-256.
- `data/processed/sitewise_v02/indicadores.csv`: diccionario y limitaciones.
- `data/processed/sitewise_v02/valores.csv`: valores largos con estado, fuente, método y fecha.
- `data/processed/sitewise_v02/solar_municipal.csv`, `agua_municipal.csv`, `logistica_municipal.csv`: resultados por bloque.
- `data/processed/sitewise_v02/agua_intersecciones.csv`: auditoría del cruce de subcuencas y municipios.
- `data/processed/sitewise_v02/suelo_industrial_municipal.csv` y `suelo_intersecciones.csv`: superficie cartografiada y cruce de polígonos.
- `docs/data/sitewise_v02/balance_suelo_industrial.json`: áreas, reparaciones, solapes y superficies fuera de los límites generalizados.
- `docs/data/sitewise_v02/`: cobertura, validación, incidencias y gráficos.

Los recortes de PVGIS y Aqueduct conservan los valores de las fuentes, sin simplificar geometrías ni redondear los datos. El cuaderno muestra cómo reconstruirlos a partir de los originales. Los originales mundiales/continentales no se incluyen para evitar cientos de MB; sus URL y hashes sí.

## Atribución y comprobaciones

PVGIS: Comisión Europea, JRC; Gounari, Martinez y Taylor (2026), doi:10.2905/JRC.A6GJ5R0, CC BY4.0. Aqueduct: Kuzma et al. (2023), WRI, doi:10.46830/writn.23.00061, CC BY4.0. Catálogos logísticos: ADIF/PISERVI y Ministerio de Transportes/HERMES. Geometrías: GISCO/Eurostat/EuroGeographics; identificadores: INE. La consulta pública de un servicio no se presenta como una licencia CC: se preservan las atribuciones y las condiciones identificadas en el manifiesto.

El cuaderno se comprueba con las copias incluidas en Linux y pandas2.3.3. Se verifica por separado la resolución de ruedas binarias para Python3.14/Windows64; no se afirma haberlo ejecutado en el PC de Elena. Los cambios de disponibilidad del servicio original no afectan a la repetición desde las copias incluidas.

## Antes de subir el volumen 2 al repositorio

El GeoPackage peninsular original pesa unos 200 MB. Los dos originales están incluidos para repetir el ETL, en `data/raw/sitewise_v02/suelo_industrial/`. La regla existente del `.gitignore` excluye los datos de `data/raw/` y `data/processed/`: no uses `git add -f` para forzarlos. Puedes subir el notebook y la documentación; acordad cómo distribuir los datos entre el equipo. No se ha realizado ningún push.

La red ferroviaria de líneas no hace falta para la distancia a terminales de mercancías del catálogo ADIF que ya calculamos. Haría falta si se añade análisis de trazados, conectividad o rutas, y una línea cercana no prueba la existencia de una terminal o un servicio de mercancías.
