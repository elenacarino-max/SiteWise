# apps/api

API REST con FastAPI: rutas y validación de peticiones y respuestas. Responsable: Persona 2; apoyo: Persona 3.
La lógica de cálculo pertenece a `src/sitewise/scoring`; la lectura de datos, a `src/sitewise/db`.

## Arranque

Desde la raíz del repo, con el entorno activado:

```bash
python -m pip install -e ".[api]"
python -m uvicorn --app-dir apps/api sitewise_api.main:app --reload
```

Documentación interactiva: <http://127.0.0.1:8000/docs>

Los datos se leen de `data/processed/sitewise_v03/` (`municipios.csv`, `indicadores.csv` y `valores.csv`,
que no están en Git). Para usar otra carpeta, define `SITEWISE_DATA_DIR`. Sin datos, `/health` responde
`datos_cargados: false` y el resto de rutas devuelven un 503 con `error: datos_no_disponibles`.

## Endpoints

| Método y ruta | Qué devuelve |
|---|---|
| `GET /health` | Estado de la API y si hay datos cargados |
| `GET /municipios` | Búsqueda paginada (`q`, `provincia`, `ccaa`, `limite`, `desplazamiento`) |
| `GET /municipios/{cod_ine}` | Datos del municipio |
| `GET /municipios/{cod_ine}/ficha` | Indicadores con valor, estado, fecha, fuente y limitaciones |

## Reglas de la API

- Los errores tienen siempre la forma `{"error": "<codigo>", "mensaje": "<texto>"}`.
- `cod_ine` es un texto de 5 dígitos con ceros iniciales (`01001`, no `1001`).
- Un dato ausente es `null`, nunca `0`. `utilizable` y `motivo_no_utilizable` explican cuándo un dato no sirve.
- Un dato aproximado se marca con `aproximado: true`.
- La valoración es municipal: no garantiza la aptitud de una parcela.

## Pruebas

```bash
python -m pytest tests/api -q
```
