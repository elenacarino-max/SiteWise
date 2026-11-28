# Contrato de la API para el agente (y el frontend)

Este documento explica cómo consultar la API de SiteWise: qué pedir, qué se recibe y cómo hay que
contarlo. Lo escribo yo (Adriana, backend) para que quien consuma la API no tenga que adivinar nada.
Las tareas que lo usan son #17 (herramientas del agente), #21 (agente con RAG) y #18 (operaciones para
el agente).

## 1. Reglas de oro

1. **El agente no calcula notas.** Todas las notas, los mínimos y los rankings vienen de la API. Si algo
   no está en la respuesta, el agente no se lo inventa: dice que no lo sabe.
2. **Riesgo y atractivo van siempre por separado.** No existe una nota única, ni un municipio "ganador",
   ni "el mejor". Se puede decir "tiene mayor atractivo" o "tiene menor riesgo", nunca "es mejor".
3. **Una nota es una posición relativa entre municipios** (un percentil ponderado). No es una
   probabilidad ni un pronóstico.
4. **Un dato que falta no es un 0.** Si `valor` es `null`, el estado dice por qué. Un `suelo_industrial`
   con estado `sin_poligonos_en_catalogo` significa "no hay polígonos en el catálogo", no "no hay suelo".
5. **Los avisos de la respuesta no se quitan.** Si viene `reglas_provisionales: true`, o un dato
   `aproximado`, o una nota `calculada_parcial`, el agente lo dice.
6. **La valoración es municipal.** No sirve para decidir sobre una parcela concreta, y las distancias son
   en línea recta. Cada respuesta incluye `aviso_alcance`.

## 2. Conexión

- Protocolo: HTTP, solo `GET`, respuestas en JSON. Sin autenticación por ahora.
- Dirección: variable de entorno `API_BASE_URL` (en `.env.example`: `http://localhost:8000`).
- Documentación interactiva con todos los parámetros: `{API_BASE_URL}/docs`.
- Códigos de municipio: código INE de **5 dígitos como texto** (`"01001"`, nunca `1001`).
- Actividades de la demo: `centro_logistico` e `industria_agua` (se listan en `/actividades`).
- Cómo arrancarla en local: `apps/api/README.md`.

## 3. Qué herramienta del agente usa qué endpoint

| El agente quiere... | Endpoint |
| --- | --- |
| Saber si la API está viva y de dónde lee | `GET /health` |
| Encontrar un municipio por nombre | `GET /municipios?q=...` |
| Contar cómo es un municipio (todos sus indicadores, con fuente y fecha) | `GET /municipios/{cod_ine}/ficha` |
| Saber qué actividades hay y si sus reglas están aprobadas | `GET /actividades` |
| Valorar un municipio para una actividad | `GET /municipios/{cod_ine}/evaluacion/{actividad}` |
| Comparar 2 o 3 municipios | `GET /comparar?municipios=...&actividad=...` |
| Buscar candidatos para una actividad | `GET /actividades/{actividad}/ranking` |
| Todos los municipios con sus notas (mapa) | `GET /actividades/{actividad}/mapa` |
| Saber a qué perfil pertenece un municipio | `perfil` dentro de `/ficha` y de `/evaluacion` |
| Municipios geográficamente próximos (para riesgos hídricos o naturales) | `GET /municipios/{cod_ine}/cercanos` |
| Municipios con un perfil parecido ("se parece a...") | `GET /municipios/{cod_ine}/similares` |
| Qué perfiles existen y cómo son | `GET /perfiles` |

Flujo típico: `/municipios?q=` para obtener el código → `/ficha` para describirlo → `/evaluacion` para
valorarlo → `/comparar` si hay varios candidatos → `/ranking` para proponer candidatos.

## 4. Endpoints

### `GET /health`
Dice si la API tiene los datos. Nunca devuelve error.
```json
{"estado": "ok", "datos_cargados": true, "origen": "postgresql", "municipios": 8132,
 "indicadores": 36, "observaciones": 292752, "detalle": ""}
```
Si `datos_cargados` es `false`, `detalle` explica por qué.

### `GET /municipios`
Parámetros opcionales: `q` (parte del nombre, sin tildes ni mayúsculas), `provincia`, `ccaa`,
`limite` (1–200, por defecto 50), `desplazamiento` (0 o más). Devuelve `total` (los que cumplen el
filtro, no solo los de la página) y la lista `municipios`.

### `GET /municipios/{cod_ine}/ficha`
Todos los indicadores del municipio. Para cada uno: `valor`, `estado`, `unidad`, `fecha_dato`,
`fuente_id`, `limitaciones`, y dos campos que el agente debe respetar:
- `aproximado`: el dato es una aproximación (por ejemplo, provincial).
- `utilizable`: si es `false`, el dato no sirve para calcular y `motivo_no_utilizable` explica por qué.

### Perfiles: `perfil`, `/perfiles` y `/municipios/{cod_ine}/similares`
Helen agrupa los municipios en 4 perfiles (v02) para describirlos en lenguaje sencillo.
**Un perfil NO es una nota ni un riesgo**: dice a qué otros municipios se parece, no si es bueno o malo
para una actividad. El agente nunca lo mezcla con riesgo o atractivo.

- `/ficha` y `/evaluacion` incluyen `perfil`: `cluster` (0–4), `nombre`, `descripcion`, `es_atipico`
  (solo una pista), `version_modelo` y un `aviso`. Es `null` si la API no tiene perfiles cargados.
- `GET /perfiles`: los perfiles (4 en la v02) con su descripción, las medianas de cada variable y los índices medios
  (`indices`: logística, hídrica y conectividad, de 0 a 100).
- `GET /municipios/{cod_ine}/similares`: municipios con el mismo perfil, **del más cercano al más lejano**
  (`distancia_km` en línea recta). Parámetros: `provincia`, `ccaa`, `limite` (1–200, por defecto 10),
  `desplazamiento`. Devuelve `total`, el `perfil` del municipio consultado y la lista `similares`.
  Si el municipio no tiene perfil: 404 `perfil_no_disponible`. En la v02, 157 municipios no tienen perfil
  (les falta el dato de terminal ferroviaria) y su `perfil` es `null`.
- Limitación (la dice Helen en su ficha del modelo): los perfiles se solapan; un municipio en la frontera
  entre dos podría estar en cualquiera. El grupo 0 es muy amplio (de pueblos grandes a grandes ciudades).

### `GET /municipios/{cod_ine}/cercanos`

Los **5 municipios geográficamente más próximos** (distancia en línea recta entre centroides), de Helen
(`municipios_cercanos_v01.csv`). Cada uno trae sus datos de municipio, `posicion` (1 = el más cerca) y
`distancia_km`. No mira el perfil ni la nota: sirve para razonar sobre riesgos que dependen del entorno
(agua, riesgos naturales). Ojo: unos pocos vecinos están lejos (hay 85 casos de más de 25 km y 5 de más de
100 km), así que el agente debe leer `distancia_km` antes de decir "cerca". Si no hay datos de cercanos
devuelve 404 `cercanos_no_disponibles`; no se inventan vecinos.

### `GET /actividades`
Actividades con reglas y su `estado_reglas`: `aprobadas` solo si **todas** las reglas están firmadas; si
no, `provisionales`. Con reglas provisionales el campo `aviso` lo dice.

### `GET /municipios/{cod_ine}/evaluacion/{actividad}`
La valoración de un municipio. Estructura (sección 5 explica cada campo):
- `municipio`
- `evaluacion.riesgo` y `evaluacion.atractivo`: cada uno con `estado`, `nota`, `confianza`, `motivo` y
  `componentes` (qué indicadores entran, su peso, su valor y su percentil)
- `evaluacion.cumple_minimos`, `evaluacion.motivo_minimos` y `evaluacion.minimos` (uno por requisito)
- `evaluacion.reglas_provisionales` y `evaluacion.version_reglas`

### `GET /comparar?municipios=01001,28001&actividad=centro_logistico`
Entre **2 y 3** municipios (repetidos `?municipios=A&municipios=B` o separados por comas, sin repetir).
Devuelve:
- `resumen`: una fila por municipio, con las dos notas, su estado, su confianza y `cumple_minimos`
- `indicadores`: para cada indicador de las reglas, el valor de cada municipio (`null` si no hay dato)
- `evaluaciones`: la evaluación completa de cada uno
- `aviso_comparacion`: "no hay nota única ni municipio ganador"

### `GET /actividades/{actividad}/ranking`
Municipios ordenados por **una** dimensión. Parámetros opcionales:
- `ordenar_por`: `atractivo` (por defecto) o `riesgo`
- `orden`: `mejor_primero` (por defecto) o `peor_primero`. Atractivo: mejor = más alto. Riesgo: mejor = más bajo.
- `provincia`, `ccaa`, `cumple_minimos` (`cumple`, `no_cumple` o `no_evaluable`)
- `limite` (1–200, por defecto 50), `desplazamiento`

Devuelve `total` (con nota en esa dimensión), `sin_nota` (municipios que cumplen el filtro pero no tienen
nota), y `filas` con `posicion`. La primera llamada a una actividad tarda unos segundos (calcula todos los
municipios); las siguientes son inmediatas.

### `GET /actividades/{actividad}/mapa`
Todos los municipios con coordenadas y notas, sin paginar (unos 2 MB comprimibles). Pensado para el
frontend; el agente normalmente usa `/ranking`.

## 5. Cómo leer una evaluación

**Estado de una nota** (`riesgo.estado` y `atractivo.estado`):

| Estado | Significa | Cómo contarlo |
| --- | --- | --- |
| `calculada` | Están todos los datos | Se da la nota |
| `calculada_parcial` | Falta algún dato; `confianza` (0 a 1) dice qué parte de los pesos está presente | Se da la nota **y se avisa** de que es parcial |
| `no_evaluable` | No hay datos suficientes; `nota` es `null` | No se da nota; se dice por qué (`motivo`) |
| `sin_reglas` | La actividad no tiene reglas completas (peso y sentido) para esa dimensión; `nota` es `null` | No se da nota; se cuenta que esa dimensión no está definida todavía |

**Mínimos** (`cumple_minimos` y cada elemento de `minimos`):

| Estado | Significa |
| --- | --- |
| `cumple` | Todos los mínimos cumplen |
| `no_cumple` | Al menos uno no cumple (tiene prioridad) |
| `no_evaluable` | Ninguno incumple, pero falta el dato de alguno. **Nunca se cuenta como "cumple"** |

Un municipio con un mínimo `no_cumple` puede tener buen atractivo: son cosas distintas y se cuentan las dos.

**Avisos que el agente debe trasladar:**
- `reglas_provisionales: true` → las reglas no están aprobadas: "valoración orientativa".
- `aproximado: true` en un componente o mínimo (y su `aviso`) → se evaluó con un dato aproximado.
  Los datos provinciales no se usan nunca para decidir mínimos.
- `confianza` baja en una nota parcial.
- `version_reglas` identifica las reglas usadas, por si hay que citarlas.

## 6. Ejemplos

Los valores de los ejemplos 6.1 a 6.3 son **inventados** (datos de las pruebas, no reales); sirven solo
para ver la forma. El ejemplo 6.4 sí es real.

### 6.1 Ranking por atractivo (valores inventados)
`GET /actividades/logistica_prueba/ranking?limite=2`
```json
{
  "actividad": "logistica_prueba",
  "ordenado_por": "atractivo",
  "orden": "mejor_primero",
  "total": 3,
  "sin_nota": 0,
  "limite": 2,
  "desplazamiento": 0,
  "filas": [
    {"cod_ine": "01001", "nombre": "Villaverde Alta", "provincia": "Álava", "ccaa": "País Vasco",
     "lat": 42.8, "lon": -2.7,
     "riesgo_nota": 25.0, "riesgo_estado": "calculada", "riesgo_confianza": 1.0,
     "atractivo_nota": 55.56, "atractivo_estado": "calculada", "atractivo_confianza": 1.0,
     "cumple_minimos": "cumple", "posicion": 1},
    {"cod_ine": "41001", "nombre": "Río Seco", "provincia": "Sevilla", "ccaa": "Andalucía",
     "lat": 37.4, "lon": -5.9,
     "riesgo_nota": null, "riesgo_estado": "no_evaluable", "riesgo_confianza": 0.0,
     "atractivo_nota": 50.0, "atractivo_estado": "calculada_parcial", "atractivo_confianza": 0.3333,
     "cumple_minimos": "no_evaluable", "posicion": 2}
  ],
  "version_reglas": "21a505d9",
  "reglas_provisionales": true,
  "aviso_comparacion": "Se ordena por una sola dimensión cada vez: ...",
  "aviso_alcance": "Valoración a escala municipal: ..."
}
```
Lectura correcta de la segunda fila: "Río Seco tiene un atractivo de 50, pero es una nota parcial (confianza 0,33);
su riesgo no se puede evaluar y sus mínimos no se pueden comprobar por falta de datos".

### 6.2 Ficha con un dato no utilizable (valores inventados)
Fragmento de `GET /municipios/41001/ficha`:
```json
{"id_indicador": "suelo_ha", "nombre": "Suelo industrial", "unidad": "ha",
 "valor": 0.0, "estado": "sin_poligonos_en_catalogo", "aproximado": false,
 "utilizable": false,
 "motivo_no_utilizable": "estado 'sin_poligonos_en_catalogo': el dato no es utilizable"}
```
```json
{"id_indicador": "estres", "nombre": "Estrés hídrico", "unidad": "%",
 "valor": null, "estado": "pendiente", "utilizable": false,
 "motivo_no_utilizable": "sin valor (estado: pendiente)"}
```

### 6.3 Comparación (valores inventados)
`GET /comparar?municipios=01001,28001&actividad=logistica_prueba`, campo `resumen`:
```json
[
  {"cod_ine": "01001", "nombre": "Villaverde Alta",
   "riesgo_nota": 25.0, "riesgo_estado": "calculada", "riesgo_confianza": 1.0,
   "atractivo_nota": 55.56, "atractivo_estado": "calculada", "atractivo_confianza": 1.0,
   "cumple_minimos": "cumple"},
  {"cod_ine": "28001", "nombre": "Vallehondo",
   "riesgo_nota": 75.0, "riesgo_estado": "calculada", "riesgo_confianza": 1.0,
   "atractivo_nota": 44.44, "atractivo_estado": "calculada", "atractivo_confianza": 1.0,
   "cumple_minimos": "cumple"}
]
```
Lectura correcta: "Villaverde Alta tiene mayor atractivo y menor riesgo que Vallehondo". Nunca "Villaverde Alta es la mejor".

### 6.4 Evaluación real: Madrid, `centro_logistico` (datos reales, reglas provisionales)
`GET /municipios/28079/evaluacion/centro_logistico`, resumen de la respuesta:
```json
{
  "evaluacion": {
    "riesgo":    {"estado": "calculada", "nota": 77.14, "confianza": 1},
    "atractivo": {"estado": "calculada", "nota": 98.41, "confianza": 1},
    "cumple_minimos": "cumple",
    "minimos": [
      {"id_indicador": "suelo_industrial_cartografiado_ha", "operador": ">=", "umbral": 10,
       "unidad": "ha", "estado": "cumple", "valor": 1623.6, "aproximado": true,
       "aviso": "evaluado con un dato aproximado (estado: aproximado, nivel: poligono_industrial)"},
      {"id_indicador": "dist_recta_eje_autovia_km", "operador": "<=", "umbral": 20,
       "unidad": "km", "estado": "cumple", "valor": 0.03, "aproximado": true,
       "aviso": "evaluado con un dato aproximado (estado: aproximado, nivel: eje_infraestructura)"}
    ],
    "reglas_provisionales": true,
    "version_reglas": "80f85bd9"
  }
}
```
Lectura correcta: "Madrid tiene un atractivo muy alto (98) para un centro logístico y cumple los
mínimos de suelo y de cercanía a autovía, aunque esos datos son aproximados. Su riesgo es alto (77), sobre
todo por el número de eventos CNIH, que es un recuento absoluto y favorece que los municipios grandes
puntúen alto. Las reglas son provisionales: es una valoración orientativa."

## 7. Errores

Los errores de la propia API tienen siempre esta forma. El `error` es un código estable (se puede
comparar en código); el `mensaje` es para personas:
```json
{"error": "municipio_no_encontrado", "mensaje": "No existe el municipio '99999'."}
```

| HTTP | `error` | Cuándo | Qué hace el agente |
| --- | --- | --- | --- |
| 404 | `municipio_no_encontrado` | El código INE no existe | Pide aclarar el municipio o lo busca con `/municipios?q=` |
| 404 | `cercanos_no_disponibles` | Piden `/cercanos` y no hay datos de cercanos cargados o el municipio no aparece | Dice que ese dato no está disponible |
| 404 | `perfil_no_disponible` | Piden `/similares` y no hay perfiles cargados o el municipio no tiene | Dice que ese dato no está disponible; no inventa parecidos |
| 404 | `actividad_no_encontrada` | No hay reglas para esa actividad | Consulta `/actividades` y ofrece las disponibles |
| 400 | `comparacion_invalida` | Menos de 2 o más de 3 municipios, códigos mal formados o repetidos | Corrige la petición |
| 503 | `datos_no_disponibles` | La API no tiene datos (falta la carga o la base está caída) | Dice que el servicio no está disponible; no inventa |
| 500 | `reglas_invalidas` | El CSV de reglas tiene un error | Dice que hay un fallo del servicio; no inventa |
| 422 | (sin `error`) | Un parámetro no es válido (código INE que no son 5 dígitos, `limite` fuera de 1–200...) | Es un fallo de la petición; revisar el código |

**Atención con el 422:** lo genera el propio FastAPI y su formato es distinto:
`{"detail": [{"loc": ["path", "cod_ine"], "msg": "...", ...}]}`. No lleva `error` ni `mensaje`.
El cliente debe tratar cualquier código HTTP ≥ 400 como error, aunque no tenga el campo `error`.

Ante cualquier error el agente **no rellena el hueco con datos propios**: lo dice y propone qué hacer.

## 8. Pendiente

- **Perfiles:** la API sirve la versión más alta de Helen (hoy `v02`). Si ella saca una versión nueva, basta con dejar sus CSV
  en `data/reference/` y volver a cargar la base: la API usa la versión más alta que encuentre.
- **Reglas sin firmar:** mientras `reglas_provisionales` sea `true`, todo resultado es orientativo.
- **Dataset:** la API lee ahora el dataset v0.3; si el dataset oficial congelado cambia, las notas se
  recalculan solas, pero hay que volver a cargar los datos (`docs/architecture/postgresql.md`).
