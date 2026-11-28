# Decisiones del backend (registro para Gema y el equipo)

Fecha: 22 de noviembre de 2026. Responsable: Adriana (Backend API y cálculo).

El equipo me delegó las decisiones de cálculo y de contrato de la API, con la condición de dejarlas
documentadas para Gema. Este fichero es el índice. Cualquier decisión se puede revisar: casi todas
se cambian editando un CSV o un ajuste, sin reescribir código.

## Resumen

| # | Decisión | Qué hace la API | Qué debe hacer la interfaz |
|---|---|---|---|
| D1 | Notas con datos parciales | Calcula con los datos que haya y marca `calculada_parcial` con su `confianza` | Rotular la nota como provisional y enseñar la confianza |
| D2 | Mínimos con datos aproximados | Un dato aproximado municipal puede evaluar un mínimo, con `aviso`. Un proxy provincial nunca | Enseñar el aviso junto al resultado y distinguir `no_evaluable` de `no_cumple` |
| D3 | Reglas sin firmar | Calcula igualmente y devuelve `reglas_provisionales: true` | Enseñar la nota como orientativa, nunca como conclusión |
| D4 | Qué significan las notas | Riesgo y atractivo por separado; son posición relativa, no probabilidad | No sumarlas, no promediarlas, no declarar un "ganador" |
| D5 | Actividades de la demo | `centro_logistico` e `industria_agua` | Ver `actividades-demo.md` |
| D6 | Fuente de los valores | Lee `valores.csv` (columna `estado`) | Nada: el cambio sería interno |
| D7 | Sesgo del recuento CNIH | Se mantiene como recuento absoluto, con peso moderado | Enseñar la limitación del indicador |
| D8 | Un indicador por grupo | Las reglas evitan contar dos veces lo mismo | Nada |
| D9 | PostgreSQL | Es el almacén del MVP; la API lee de la base si se define `SITEWISE_DATABASE_URL` (ver `postgresql.md`) | Nada |
| D10 | Valores de la app | Lee `valores_app.csv` y decide con el `estado` original (ver `decision-valores-app.md`) | Nada |
| D11 | Perfiles de municipios | Sirve el perfil de Helen aparte de las notas (`perfil`, `/similares`); nunca lo mezcla con ellas | Enseñarlo como descripción ("se parece a..."), no como puntuación |

## D1. Notas con datos parciales

Calculo la nota con los datos utilizables y no invento los que faltan. Si falta alguno, el estado es
`calculada_parcial`, y `confianza` es la parte del peso con dato (0 a 1). Solo es `no_evaluable` si no hay
ningún dato. El ajuste `min_confianza` (por defecto 0) permite exigir un mínimo si el equipo lo prefiere.
Detalle y alternativas: `decision-notas-parciales.md`.

## D2. Mínimos con datos aproximados

Un mínimo se puede evaluar con un dato `aproximado` a escala municipal, y el resultado lleva un `aviso`.
Los proxies provinciales (solo `tiepi` y `niepi`) nunca certifican un mínimo. Si falta el dato, el resultado
es `no_evaluable`, nunca `cumple`. Un solo mínimo incumplido ya da `no_cumple`, aunque otros no se puedan
evaluar. Hay un modo estricto, que no se usa en la demo. Detalle: `decision-minimos-y-datos-aproximados.md`.

## D3. Reglas sin firmar

Mientras una regla no tenga `aprobado_por` y `fecha_aprobacion`, es provisional, y la actividad aparece como
`provisionales` en `/actividades`. Decido **calcular igualmente** y avisar, en lugar de ocultar la nota,
porque sin nota la demo no enseña nada. Cumple lo que pide la matriz de riesgos (apartado 6): no presentar
como concluyente algo sin respaldo.

Para Gema: mientras `reglas_provisionales` sea `true`, la nota debe verse como **orientativa**, con el texto
«Reglas provisionales, pendientes de aprobación», y siempre con acceso a los indicadores que la explican.

## D4. Qué significan las notas

`riesgo.nota` y `atractivo.nota` (0 a 100) son la **posición relativa** del municipio frente al resto de
municipios con dato, mediante percentiles ponderados. No son probabilidades, ni riesgo calculado
(probabilidad por impacto), ni rentabilidad. Se muestran siempre por separado: no hay nota única, ni
media, ni "mejor municipio". Un ranking ordena por una dimensión a la vez.

Texto sugerido: «Posición relativa frente a otros municipios. No es una probabilidad ni garantiza la
aptitud de una parcela.»

## D5. Actividades de la demo

`centro_logistico` (principal) e `industria_agua` (contraste). Reglas, pesos, umbrales y calibración con datos
reales: `actividades-demo.md` y `configs/actividades/reglas_actividad.csv`.

## D6. Fuente de los valores

El notebook 09 genera además `valores_app.csv`, con una columna `estado_app` y 722 valores de aguas
subterráneas estimados a partir de municipios vecinos. De momento el backend lee solo `valores.csv`.
Es una decisión de trabajo: queda pendiente de que Elena y Helen confirmen cuál es el fichero que debe
alimentar la aplicación. El cambio sería interno al repositorio de datos y no alteraría la API.

## D7. Sesgo del recuento CNIH

`eventos_cnih_2000_2023_n` es un recuento absoluto, y el propio catálogo avisa de su sesgo de documentación:
un municipio grande acumula más eventos registrados. En la calibración, los municipios grandes salen con
riesgo alto (por ejemplo Torrejón de Ardoz, 90,7 en `centro_logistico`). Decido **mantenerlo** con peso
moderado y documentar la limitación, porque no hay un denominador mejor en el dataset. Se puede bajar su peso
en el CSV si el equipo lo ve excesivo.

Para Gema: mostrar siempre el campo `limitaciones` del indicador junto a su valor.

## D8. Un indicador por grupo

Para no contar dos veces lo mismo, cada actividad usa un solo indicador de cada grupo correlacionado:
una distancia a terminal (la intermodal da el mismo valor), una cobertura (1 Gbps) y una tasa de incendios.
Suelo y autovía cuentan como mínimo y también en la nota: es intencionado y se explica en `actividades-demo.md`.

## D11. Perfiles de municipios

Helen agrupa los municipios en perfiles (hoy 4, v02). La API los sirve para que el agente y la interfaz
puedan decir "se parece a...", pero **un perfil no es una nota**: no entra en el riesgo ni en el atractivo
y no dice si un municipio es adecuado. Se guardan en PostgreSQL (`perfiles_municipios`, `perfiles_definicion`)
y se leen del CSV de Helen si no hay base. Los "similares" son los del mismo perfil, ordenados por distancia
en línea recta. La ficha del modelo (`docs/methodology/model_card_clustering.md`) recuerda sus límites
(los grupos se solapan). Hay municipios sin perfil (en la v02, 157 sin dato de terminal ferroviaria).

Aparte, `GET /municipios/{cod_ine}/cercanos` sirve los 5 municipios geográficamente más próximos
(`municipios_cercanos_vNN.csv`). No usa el perfil: es solo geografía, para riesgos de agua y naturales.
La distancia viene siempre en la respuesta porque algunos vecinos están lejos (5 casos de más de 100 km).

## Qué comprueba Gema antes de la demo

- [ ] La nota nunca se enseña sin `estado` ni `confianza`.
- [ ] `no_evaluable` se distingue visualmente de `no_cumple`.
- [ ] Se enseña el aviso de dato aproximado y `reglas_provisionales`.
- [ ] Se incluye el `aviso_alcance` que devuelve la API.
- [ ] Riesgo y atractivo se ven por separado.
