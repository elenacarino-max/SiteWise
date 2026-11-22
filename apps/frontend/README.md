# Frontend de SiteWise

Interfaz desarrollada con React, TypeScript y Vite.
El mapa utiliza Leaflet y React Leaflet.

## Requisitos

Instalar Node.js en su versión LTS, que incluye npm.

Las dependencias del frontend se encuentran en `package.json`.
No se instalan mediante el `requirements.txt` de Python.

## Instalación

Desde la raíz del repositorio:

```bash
cd apps/frontend
npm ci
```

Este comando instala las versiones registradas en `package-lock.json`.
Solo es necesario al preparar el proyecto o cuando cambien las dependencias.

## Preparar el mapa

El frontend necesita el archivo:

`apps/frontend/public/mapas/municipios.geojson`

Si no está disponible, copiarlo desde los datos procesados.
Desde la raíz del repositorio, en Git Bash:

```bash
mkdir -p apps/frontend/public/mapas
cp data/processed/sitewise_v01/municipios.geojson apps/frontend/public/mapas/municipios.geojson
```

Si tampoco está el archivo de origen, solicitar al equipo de datos
los datos procesados o seguir las instrucciones de generación del dataset.

## Arrancar la aplicación

Desde `apps/frontend`:

```bash
npm run dev
```

Abrir la dirección que aparece junto a `Local` en la terminal.
Mantener la terminal abierta. Para detener la aplicación, pulsar Ctrl + C.

No es necesario activar el entorno de Python para ejecutar el frontend.

## Comprobaciones

Desde `apps/frontend`:

```bash
npm run build
npm run lint
```

## Estado actual

- Mapa con contornos municipales de España y Canarias en un recuadro.
- Selección de municipios desde el mapa.
- Buscador limitado a cinco municipios de ejemplo.
- Ficha municipal y selección de hasta tres municipios para comparar.
- Indicadores, puntuaciones y asistente todavía pendientes de conexión.
- Los colores del mapa son provisionales y no representan riesgo.
- La selección se borra al recargar la página.

## Actualizar los indicadores de suelo y logística

Detalle y Comparar leen el extracto local `public/indicadores-municipales.json`.
Cuando cambien los CSV de la entrega v0.3, regenerarlo desde la raíz del repositorio:

```bash
python apps/frontend/exportar_indicadores.py
```

Los selectores de inversión usan un catálogo provisional en `src/ConfiguracionInversion.tsx`.
La evaluación por actividad y el asistente siguen pendientes de integración con el backend.
