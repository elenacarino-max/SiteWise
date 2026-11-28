# Selección de variables para el perfil municipal (v02)

Issue #12 (ML-01), rediseñada el 27 de noviembre de 2026 tras la revisión técnica · Responsable: Helen · Revisión: Elena

La decisión se recoge, con la cobertura de cada variable, en `notebooks/04_decision_variables_perfil.ipynb`, sobre `data/processed/sitewise_v04_candidata`.

## Resumen

El perfil de municipio usa **7 variables agrupadas en 3 índices** (logística, hídrica y conectividad), que son las **3 entradas** del clustering final. El resto de las variables no se agrupa: queda como **dato suelto** para filtros, scoring por actividad y RAG.

El perfil describe cómo es un municipio; no es una nota de riesgo ni de atractivo. El riesgo se calcula aparte, en la puntuación de cada actividad.

## Criterios (revisión técnica)

1. Solo se agrupan variables cuyo sentido **bueno/malo es claro y consistente**.
2. El cluster final usa **como máximo 3–4 entradas**. Es un techo, no un mínimo.
3. Lo que no tiene un sentido claro (población, paro, viento) no se agrupa.
4. Los datos en bruto y los derivados quedan disponibles para el RAG.
5. Los huecos no se rellenan con 0 ni con la media: se estiman con municipios cercanos y se marcan, o el municipio queda sin esa dimensión.

## Variables que entran en el perfil

| Índice | Variable | Sentido | Huecos |
| --- | --- | --- | --- |
| Logística | `suelo_industrial_cartografiado_pct` | mayor, mejor | Ninguno |
| Logística | `dist_recta_eje_autovia_km` | menor, mejor | 52 (no se imputa) |
| Logística | `dist_recta_ttm_km` | menor, mejor | 157 (no se imputa) |
| Hídrica | `estres_hidrico_pct` | mayor, más presión | 24 (estimados con vecinos) |
| Hídrica | `agua_subterranea_mal_estado_cuantitativo_pct` | mayor, más presión | 722 (estimados con vecinos) |
| Conectividad | `cobertura_ftth_pct` | mayor, mejor | Ninguno |
| Conectividad | `cobertura_5g_pct` | mayor, mejor | Ninguno |

Cada índice es la media de los percentiles de rango medio de sus variables (0 a 100), con las distancias invertidas. Si falta un componente de logística o conectividad, el índice queda vacío; en la hídrica se usa el valor estimado. El cálculo está en `src/sitewise/ml/indices.py`.

## Variables que no entran en el perfil (datos sueltos)

| Variable | Uso | Motivo |
| --- | --- | --- |
| `poblacion_2025` | Filtro RAG | Depende del cliente; su rango enorme dominaría la agrupación |
| `densidad_hab_km2`, `variacion_poblacion_pct` | Dato suelto | Sin sentido bueno/malo único |
| `paro_total` (y el resto de paro) | Dato suelto | Cobertura irregular, cifras protegidas por el SEPE y tasa que depende de la población por construcción |
| `viento_100m_media_m_s`, `irradiacion_ghi_kwh_m2_anio` | Scoring por actividad | Sirven a unas actividades y no a otras |
| `incendios_ge1ha_100km2_anio`, `jrc_t100_area_positiva_pct` | Riesgo (dato suelto) | Cobertura parcial; añadirlos dejaría el perfil con el 49,5 % de los municipios |

## Variables descartadas por redundancia

Correlación de Spearman calculada sobre los pares con dato (notebook 03A). Una correlación alta no demuestra que dos indicadores sean equivalentes.

| Variable descartada | Representada por | ρ |
| --- | --- | --- |
| `suelo_industrial_cartografiado_ha` | `suelo_industrial_cartografiado_pct` | 0,977 |
| `dist_recta_ttm_intermodal_km` | `dist_recta_ttm_km` | 0,847 |
| `agotamiento_hidrico_pct` | `estres_hidrico_pct` | 0,990 |
| `superficie_estres_ge40_pct` | `estres_hidrico_pct` | 0,774 |
| `cobertura_100mbps_pct`, `cobertura_1gbps_pct` | `cobertura_ftth_pct` | 0,808 y 0,894 |
| `tiepi_horas_prov_2021`, `niepi_prov_2021` | (ninguna) | Dato provincial repetido: el modelo agruparía por provincias |

## Huecos

Regla general: los valores estimados **solo se usan para el índice hídrico**, y la aplicación los muestra siempre como **aproximados**, nunca como dato observado.

| Variable | Municipios sin dato | Quiénes son | Tratamiento |
| --- | --- | --- | --- |
| `dist_recta_ttm_km` | 157 | Baleares (67), Canarias (88), Ceuta y Melilla | No se imputa: esos municipios no tienen perfil |
| `dist_recta_eje_autovia_km` | 52 | Canarias (36), Baleares (14), Ceuta y Melilla | No se imputa (el municipio ya queda sin perfil por la terminal) |
| `estres_hidrico_pct` | 24 | Repartidos por varias provincias | Media de los 5 municipios cercanos con dato |
| `agua_subterranea_mal_estado_cuantitativo_pct` | 722 | Municipios sin masa de agua catalogada | Media de los 5 municipios cercanos con dato. Error medio de 12,8 puntos validado con vecinos de otras provincias (notebook 08) |

Hacinas, Monasterio de la Sierra, Llívia y A Illa de Arousa tenían las dos distancias vacías por cómo se calculaban; se corrigieron el 27 de noviembre de 2026 (PR #61, notebook 02) y ahora entran en el perfil.

## Pendiente

1. **Incendios (≈ 54-74 % de cobertura según la variable) e inundaciones.** Los huecos no son aleatorios: rellenar con cero haría parecer más seguros a los municipios pequeños solo porque se miden peor. Quedan fuera del perfil y como dato suelto (con el dato de los municipios cercanos como opción para mostrar).
2. **Qué estados cuentan como dato válido.** El dataset usa 18 estados y el contrato solo 3 (real, aproximado, pendiente). Relacionado con el issue #11.
3. **La columna `sentido` del diccionario mezcla dos nomenclaturas** (`mas_es_peor` / `menor_mejor` y `mas_es_mejor` / `mayor_mejor`). Convendría unificarla, también en el #11.

Los puntos 2 y 3 vienen de la versión anterior de este documento y no se han revisado en el rediseño.

## Historial: selección v01

La versión anterior usaba 7 variables (población, suelo industrial, autovía, terminal, paro, viento y agua) con transformaciones, PCA (85 % de varianza) y K-Means con K=5. Se descartó tras la revisión técnica porque mezclaba características territoriales, demográficas, logísticas y ambientales sin un sentido bueno/malo común. Sus notebooks (04 a 08 y 10 antiguos) siguen en el historial de Git (commit `bc30250`) y sus ficheros en `data/reference/perfiles_*_v01.csv`.
