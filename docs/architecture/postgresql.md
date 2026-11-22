# PostgreSQL como origen de datos (opcional)

La API puede leer los datos de PostgreSQL en vez de los CSV. Es opcional: si no se configura nada,
sigue leyendo los CSV de `data/processed/sitewise_v03`.

## Cómo se usa

1. Instalar el soporte: `python -m pip install -e ".[db]"`
2. Arrancar la base de datos: `docker compose up -d` (usa las variables `POSTGRES_*` de `.env`).
3. Cargar el dataset (borra y vuelve a crear las tres tablas, así que se puede repetir):

   ```
   python -m sitewise.db.cargador --datos data/processed/sitewise_v03
   ```

4. Arrancar la API apuntando a la base:

   ```
   SITEWISE_DATABASE_URL=postgresql://USUARIO:CLAVE@127.0.0.1:5432/sitewise uvicorn sitewise_api.main:app
   ```

   `GET /health` muestra `"origen": "postgresql"` (o `"csv"`).

Variables: `SITEWISE_DATABASE_URL` (activa PostgreSQL) y `SITEWISE_DB_SCHEMA` (esquema, por defecto `public`).
El cargador, si no se le da `--url`, usa `SITEWISE_DATABASE_URL` o monta la dirección con `POSTGRES_*`.

## Qué hay en la base

Las tres tablas del diccionario del dataset: `municipios`, `indicadores` y `valores` (formato largo),
más una columna `orden` que conserva la posición de cada fila en el CSV. `valor` es NULL cuando falta el
dato (nunca 0) y `estado` explica por qué. `valores` tiene claves foráneas a municipios e indicadores.

- La carga es una sola transacción: si algo falla, la base se queda como estaba.
- La base tiene que ser UTF8 (la imagen oficial de PostgreSQL ya lo es); si no, el cargador se detiene.
- Si la base tiene PostGIS, se añade a `municipios` una columna `geom` con índice espacial. Si no, se
  sigue con `lat` y `lon`, que se guardan siempre. El resto del backend solo usa `lat` y `lon`.

## Cómo lee la API

`RepositorioPostgres` hereda de `RepositorioCSV`: lee las tres tablas una vez al arrancar y consulta en
memoria, igual que con los CSV. El motor y los endpoints no notan la diferencia (hay una prueba que
compara las respuestas de ambos orígenes).

## Pruebas

Las pruebas de PostgreSQL se omiten si no se define `SITEWISE_TEST_DATABASE_URL`. Cada prueba trabaja en
su propio esquema y lo borra al terminar:

```
SITEWISE_TEST_DATABASE_URL=postgresql://USUARIO:CLAVE@127.0.0.1:5432/sitewise python -m pytest -q
```

## Pendiente de verificar

PostGIS no está probado: mi entorno de pruebas no lo incluye. La carga con PostGIS se comprueba con la
imagen `postgis/postgis` de Docker.
