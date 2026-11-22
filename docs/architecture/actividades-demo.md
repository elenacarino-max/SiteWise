# Actividades de la demo y cómo se muestran

**Estado:** provisional. El equipo me pidió que eligiera yo las actividades y lo dejara documentado para Gema (22/11/2026).
Los pesos y umbrales son una propuesta mía; no están respaldados por una fuente externa y las reglas siguen sin firmar.

## Qué actividades elijo y por qué

1. **`centro_logistico`** (actividad principal). Es donde los datos del dataset son más sólidos: suelo industrial,
   distancia a autovía y a terminal de mercancías, y cobertura digital. Además usa todo el motor: mínimos,
   nota de atractivo, nota de riesgo, datos aproximados y casos no evaluables.
2. **`industria_agua`** (industria intensiva en agua, por ejemplo papel). Sirve de contraste: con los mismos
   municipios, el estrés hídrico pasa a ser lo que más pesa. Así se ve la idea central de la matriz de riesgos:
   el impacto de una misma condición depende de la actividad.

Descarto de momento el centro de datos (su criterio clave, la continuidad eléctrica, solo existe como proxy
provincial, que nunca certifica un mínimo) y la generación solar o eólica (no hay datos de suelo rústico).

## Reglas de cada actividad

Fichero: `configs/actividades/reglas_actividad.csv`. Un indicador por grupo, para no contar dos veces lo mismo.

### `centro_logistico`

| Indicador | Uso | Peso | Sentido | Mínimo |
|---|---|---|---|---|
| `suelo_industrial_cartografiado_ha` | atractivo | 3 | directa | ≥ 10 ha |
| `dist_recta_eje_autovia_km` | atractivo | 3 | inversa | ≤ 20 km |
| `dist_recta_ttm_km` | atractivo | 2 | inversa | |
| `cobertura_1gbps_pct` | atractivo | 1 | directa | |
| `eventos_cnih_2000_2023_n` | riesgo | 2 | directa | |
| `siniestros_forestales_100km2_2006_2015` | riesgo | 1 | directa | |
| `estres_hidrico_pct` | riesgo | 1 | directa | |
| `poblacion_2025`, `paro_industria` | contexto | | | |

### `industria_agua`

| Indicador | Uso | Peso | Sentido | Mínimo |
|---|---|---|---|---|
| `suelo_industrial_cartografiado_ha` | atractivo | 2 | directa | ≥ 10 ha |
| `dist_recta_eje_autovia_km` | atractivo | 2 | inversa | ≤ 30 km |
| `estres_hidrico_pct` | riesgo | 3 | directa | |
| `agotamiento_hidrico_pct` | riesgo | 2 | directa | |
| `agua_subterranea_mal_estado_cuantitativo_pct` | riesgo | 1 | directa | |
| `eventos_cnih_2000_2023_n` | riesgo | 1 | directa | |
| `poblacion_2025`, `paro_industria` | contexto | | | |

Decisiones de diseño:

- **Sentido.** `directa`: valor alto, nota alta. `inversa`: valor bajo, nota alta (la distancia a la autovía).
  En riesgo, nota alta es *más* riesgo; en atractivo, nota alta es *más* atractivo.
- **Suelo y autovía cuentan dos veces a propósito:** primero como mínimo (pasa o no pasa) y luego en la nota
  (cuánto mejor). Si el equipo prefiere que solo sean mínimos, basta con vaciar su peso en el CSV.
- **Una sola TTM y una sola cobertura.** `dist_recta_ttm_km` y `dist_recta_ttm_intermodal_km` dieron el mismo valor
  en los municipios que revisé; las coberturas FTTH, 100 Mbps y 1 Gbps están muy correlacionadas. Los cuatro
  indicadores de incendios miden casi lo mismo, así que uso solo la tasa por 100 km².
- **Población y paro** solo como contexto: no son tasa de paro ni disponibilidad de personal.

## Qué debe mostrar la interfaz (para Gema)

Endpoints: `GET /actividades`, `GET /municipios/{cod_ine}/evaluacion/{actividad}` y
`GET /comparar?municipios=A,B,C&actividad=X`.

| Campo | Valores | Qué enseñar |
|---|---|---|
| `riesgo.estado` y `atractivo.estado` | `calculada`, `calculada_parcial`, `no_evaluable`, `sin_reglas` | La nota solo si hay `nota`. Con `calculada_parcial`, rotularla como provisional y enseñar `confianza`. |
| `riesgo.nota` y `atractivo.nota` | 0 a 100 o `null` | Son la posición relativa frente al resto de municipios, **no** una probabilidad ni un riesgo calculado. Siempre por separado. |
| `cumple_minimos` | `cumple`, `no_cumple`, `no_evaluable` | `no_evaluable` no es un fallo: falta el dato. Enseñar `motivo_minimos`. |
| `minimos[].aviso` | texto | Si el mínimo se evaluó con un dato aproximado, mostrar el aviso junto al resultado. |
| `reglas_provisionales` | `true` / `false` | Mientras sea `true`, indicar que las reglas no están aprobadas. |
| `componentes` | lista | Explica la nota: valor, percentil, peso y por qué un dato no se usó. |

Texto sugerido junto a cualquier nota: *«Valoración municipal preliminar. No garantiza la aptitud de una parcela;
las distancias son rectas.»* (llega en `aviso_alcance`).

Un aviso importante: unos 4.400 municipios no tienen polígonos industriales en el catálogo
(`sin_poligonos_en_catalogo`). Con un mínimo de suelo, esos municipios salen `no_evaluable`, no `no_cumple`.
La interfaz debe distinguirlos: el primero pide evidencia, el segundo descarta.

## Qué no afirmo

Probabilidades calibradas, pérdidas económicas, viabilidad de una parcela ni apetito de riesgo de terceros.
Tampoco hay selector de tolerancia ni motor probabilidad × impacto: quedan fuera del MVP.

## Cómo se cambian las reglas

Se edita `reglas_actividad.csv`. Cada cambio cambia `version_reglas`, que va en todas las respuestas. Una regla pasa
de provisional a aprobada cuando se rellenan `aprobado_por` y `fecha_aprobacion`; la actividad figura como
`aprobadas` solo si todas sus reglas están firmadas. Hay que reiniciar la API para que cargue el cambio.

## Pendiente

- Calibrar los umbrales (10 ha, 20 km, 30 km) con la distribución real: cuántos municipios cumplen cada mínimo.
- Que el equipo ratifique estas reglas y las dos decisiones de `decision-notas-parciales.md` y
  `decision-minimos-y-datos-aproximados.md`.
