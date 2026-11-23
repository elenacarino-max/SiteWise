# Frontend de SiteWise

Aplicación para explorar municipios de España y comparar posibles ubicaciones empresariales. Usa React, TypeScript y Vite. La cartografía se muestra con Leaflet y React Leaflet.

## Qué incluye

- **Explorar.** Mapa de 8.132 municipios, con Canarias en un recuadro, y búsqueda por municipio o provincia. Además de la vista base, el mapa ofrece cinco capas de datos con leyenda: suelo industrial cartografiado, distancia a autovía, fibra, 5G y estrés hídrico.
- **Detalle.** Ficha con 17 indicadores agrupados en suelo y logística, conectividad, población y empleo, energía, y agua y riesgos históricos. Muestra la fuente y el periodo cuando están disponibles.
- **Comparar.** Tabla para hasta tres municipios, con indicaciones como «Mayor cobertura de fibra» cuando los datos permiten distinguir una ubicación. La selección se borra al recargar la página.
- **Asistente SiteWise.** Panel con preguntas de ejemplo y un campo para escribir. El envío se habilitará al integrar la API del asistente.

## Cómo arrancarlo y probarlo

Usa una versión LTS de Node.js compatible con Vite (22.12 o posterior) con npm. Desde la raíz del repositorio:

```bash
cd apps/frontend
npm ci
npm run dev
```

Abre la URL `Local` que imprime Vite. Puedes usar el mapa y consultar o comparar los indicadores incluidos en el repositorio sin iniciar la API.

1. En **Explorar**, cambia **Capa del mapa** a **Cobertura de fibra** y revisa la leyenda.
2. Busca un municipio, selecciónalo y pulsa **Ver ficha**.
3. En **Detalle**, pulsa **Añadir a comparar**. Vuelve al buscador y repite con otro municipio.
4. Abre **Comparar** y revisa los indicadores, incluidos los valores aproximados y sin dato.

Para compilar y comprobar el código, ejecuta desde `apps/frontend`:

```bash
npm run build
npm run lint
```

## Evaluación por actividad

Para probarla, arranca la [API](../api/README.md) desde la raíz del repositorio en otra terminal:

```bash
python -m pip install -e ".[api]"
python -m uvicorn --app-dir apps/api sitewise_api.main:app
```

El backend necesita los CSV municipales locales o una conexión a PostgreSQL. Vite reenvía `/api` a `http://127.0.0.1:8000` en desarrollo y vista previa. Puedes cambiar el destino con `SITEWISE_API_TARGET` al iniciar Vite. En producción, configura el proxy de `/api` para que lo reenvíe sin ese prefijo, o define `VITE_SITEWISE_API_BASE_URL` al compilar. Si la URL apunta a otro origen, este debe permitir el origen del frontend mediante CORS.

Selecciona una actividad en **Explorar**, **Detalle** o **Comparar**. Detalle consulta la evaluación del municipio. Comparar solicita la evaluación de dos o tres municipios y conserva la tabla de indicadores descriptivos. En Explorar, las capas de riesgo y atractivo usan las notas del endpoint `GET /actividades/{actividad}/mapa`. Las dimensiones se muestran por separado, con el aviso de reglas provisionales cuando corresponda. El mapa distingue las notas parciales con un contorno discontinuo.

## Datos municipales

La aplicación cruza las geometrías de [municipios.geojson](public/mapas/municipios.geojson) y los valores de [indicadores-municipales.json](public/indicadores-municipales.json) por código INE de cinco dígitos. Los indicadores publicados se definen en [gruposIndicadores.json](src/gruposIndicadores.json).

**Detalle**, el resumen de **Explorar** y la tabla descriptiva de **Comparar** piden los valores a `GET /municipios/{cod_ine}/ficha`. Si falla una ficha, la vista usa la copia local para ese municipio y lo indica. Los contornos y las capas descriptivas del mapa se siguen cargando desde los archivos del repositorio.

- **Aproximado** indica que el dataset clasifica el valor como estimación o proxy. En las estimaciones de agua subterránea preparadas para la app, la ficha muestra el método.
- **Sin dato** significa que el extracto no contiene un valor utilizable para ese indicador y municipio.
- **0 ha cartografiadas** significa que el catálogo no recoge polígonos en el municipio. Por sí solo, ese dato no determina si hay suelo industrial disponible.
- Las distancias a autovías y terminales se miden en línea recta. Los tramos de color de las capas representan los valores que indica su leyenda.

### Regenerar los indicadores

Desde la raíz del repositorio, con Python y los archivos `indicadores.csv` y `valores_app.csv` de `data/processed/sitewise_v03/` disponibles:

```bash
python apps/frontend/exportar_indicadores.py
```

El comando actualiza `apps/frontend/public/indicadores-municipales.json`. La preparación de `valores_app.csv` se documenta en el [notebook 09](../../notebooks/09_preparacion_datos_app.ipynb) y la estructura de los datos en el [contrato del dataset](../../docs/data/contrato_dataset.md).

## Integraciones pendientes

- Incorporar los perfiles territoriales cuando se valide la versión de clustering que se publicará.
- Conectar el envío de preguntas con la API del asistente.
