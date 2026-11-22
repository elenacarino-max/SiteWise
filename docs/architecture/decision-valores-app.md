# Decisión D10: el backend lee `valores_app.csv`, pero decide con el estado original

- **Fecha:** 22 de noviembre de 2026
- **Decide:** Adriana (backend). Se documenta para el frontend (Gema), el agente (Josema) y Elena.
- **Relacionada con:** D1 a D9 (`decisiones-backend.md`), notebook 09, `apps/frontend/exportar_indicadores.py`.

## Contexto

El notebook 09 genera `valores_app.csv` a partir de `valores.csv`. Añade dos cosas:

1. 722 valores **estimados** de agua subterránea cuantitativa (media de los 5 municipios con dato más
   cercanos) para los municipios sin masa de agua catalogada. Llevan `estimado_app = True`, el método, el
   número de vecinos y las distancias.
2. Una columna `estado_app` que resume los 18 estados originales en tres: `real`, `aproximado` y
   `pendiente`. El notebook dice que la interfaz debe usarla.

El problema es que `estado_app` agrupa cosas que el cálculo necesita distinguir. En particular,
`sin_poligonos_en_catalogo` (8.866 filas, unos 2.959 municipios sin suelo industrial utilizable) pasa a
`aproximado`. Su valor es 0, pero significa "el catálogo no recoge polígonos", no "hay 0 hectáreas".

## Decisión

1. El backend lee `valores_app.csv` si existe en la carpeta de datos; si no, `valores.csv`. (`/health`
   indica cuál en `valores_fichero`.) La carga a PostgreSQL hace lo mismo y guarda las columnas nuevas.
2. **Para calcular uso el estado original (`estado`), no `estado_app`**, con una sola excepción: las filas
   con `estimado_app = True` pasan a contar como `aproximado` (su estado de origen, `sin_masa_catalogada`,
   es un estado sin valor, pero ahora sí tienen uno).
3. Resto de estados: no cambian. `sin_poligonos_en_catalogo` sigue sin ser utilizable, así que el mínimo de
   suelo de esos municipios es `no_evaluable` y no `no_cumple`.
4. Las estimaciones se marcan en la ficha (`estimado`, `metodo`, `vecinos`, `distancia_media_km`,
   `distancia_maxima_km`) y cuentan como aproximadas (D2): pueden entrar en la nota, con aviso.

## Efecto

- 722 municipios que antes no tenían dato de agua subterránea cuantitativa ahora lo tienen, aproximado.
  Afecta al riesgo de `industria_agua`, que antes salía como nota parcial para ellos.
- Los textos de las tres partes deben coincidir: lo que el frontend muestra como "0 ha cartografiadas" la
  API lo cuenta como "sin polígonos en el catálogo (no evaluable)".

## Limitaciones

El método de vecinos no acredita caudal ni suministro, y el error medio medido en el notebook 08 no
garantiza el error de cada uno de los 722 municipios (lo dice el propio notebook 09). Por eso son
`aproximado` y nunca certifican un mínimo.

## Pendiente de confirmar con el equipo

- Que Gema use la misma regla de `sin_poligonos_en_catalogo` en la pantalla (hoy lo exporta como
  `aproximado` con valor 0, aunque su README lo aclara).
- Si el dataset oficial congelado de Elena incluye `valores_app.csv`.
