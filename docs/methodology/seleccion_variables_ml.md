# Selección de variables para el clustering municipal

Issue #12 (ML-01) · Propuesta del 17 de noviembre de 2026 · Responsable: Helen · Revisión: Elena

Análisis reproducible en `notebooks/04_seleccion_variables_ml.ipynb`, sobre `data/processed/sitewise_v03`.

## Resumen

De los 36 indicadores, **10 entran** en el clustering, **19 no entran** y **7 quedan pendientes** de decidir con Elena. Con las 10 variables, el 97,8 % de los municipios (7.951 de 8.132) tiene todos los datos; los 181 restantes son casos explicables que se tratan abajo.

El clustering describe el **perfil territorial** de cada municipio: demografía, conectividad, recursos energéticos, agua, logística y suelo industrial. En esta versión **no incluye amenazas naturales**, porque sus datos tienen huecos que no son aleatorios. El riesgo sigue calculándose aparte, en la puntuación de cada actividad.

## Criterios

1. Cobertura de al menos el 98 % de los municipios.
2. Dato propio del municipio o de una rejilla fina, no el valor de la provincia repetido.
3. Sin redundancias: de cada grupo con correlación de Spearman |ρ| ≥ 0,7 se queda una variable.
4. Variables que describan el territorio (proporciones y densidades), no su tamaño (totales).

## Variables que entran

| Variable | Bloque | Transformación | Motivo |
| --- | --- | --- | --- |
| `densidad_hab_km2` | Demografía | log(1 + x) | Representa también a la población (ρ = 0,85) |
| `variacion_poblacion_pct` | Demografía | Recortar a percentiles 1–99 | Zonas que crecen o se vacían |
| `cobertura_ftth_pct` | Conectividad | — | Representa a 1 Gbps (ρ = 0,89) y 100 Mbps (ρ = 0,81) |
| `cobertura_5g_pct` | Conectividad | — | Conectividad móvil, no redundante con la fija |
| `irradiacion_ghi_kwh_m2_anio` | Recurso solar | — | Recurso solar |
| `viento_100m_media_m_s` | Recurso eólico | — | Recurso eólico |
| `estres_hidrico_pct` | Agua | — | Representa a agotamiento (ρ = 0,99) y a superficie con estrés ≥ 40 % (ρ = 0,77) |
| `dist_recta_eje_autovia_km` | Logística | log(1 + x) | Carretera |
| `dist_recta_ttm_km` | Logística | log(1 + x) | Ferrocarril; representa a la terminal intermodal (ρ = 0,85) |
| `suelo_industrial_cartografiado_pct` | Suelo industrial | — | El 0 significa "sin polígonos en el catálogo", no ausencia de suelo |

Después de estas transformaciones, todas las variables se estandarizan con `StandardScaler` (media 0, desviación 1) para que ninguna pese más por su unidad.

## Variables que no entran

| Variables | Motivo |
| --- | --- |
| `poblacion_2024`, `poblacion_2025` | Miden tamaño; la densidad ya representa la demografía |
| `cobertura_100mbps_pct`, `cobertura_1gbps_pct` | Redundantes con FTTH |
| `agotamiento_hidrico_pct`, `superficie_estres_ge40_pct` | Redundantes con el estrés hídrico |
| `dist_recta_ttm_intermodal_km` | Redundante con la terminal de mercancías |
| `suelo_industrial_cartografiado_ha` | Redundante con el porcentaje y mide tamaño |
| `tiepi_horas_prov_2021`, `niepi_prov_2021` | Dato provincial repetido (unos 50 valores distintos): el modelo agruparía por provincias |
| `ultimo_anio_cnih_2000_2023` | Es un año, no una medida |
| `paro_*` (6 variables), `contratos_total` | Cobertura entre el 38 % y el 77 %, cifras protegidas (< 5) y miden tamaño |
| `paro_variacion_interanual_pct` | Cobertura del 71 % |

## Huecos en las variables que entran

Regla general: **los valores rellenados solo se usan para entrenar el modelo. La aplicación muestra siempre el dato observado y su estado, nunca el valor rellenado.**

| Variable | Municipios sin dato | Quiénes son | Tratamiento propuesto |
| --- | --- | --- | --- |
| `dist_recta_ttm_km` | 161 | Baleares (67), Santa Cruz de Tenerife (54), Las Palmas (34) y 6 casos peninsulares | Distancia máxima observada: sin acceso terrestre a una terminal equivale a "lo más lejos posible" |
| `dist_recta_eje_autovia_km` | 56 | Canarias (36), Baleares (14) y 6 peninsulares | Igual: distancia máxima observada |
| `estres_hidrico_pct` | 24 | Municipios costeros pequeños sin cobertura suficiente en el modelo Aqueduct | Mediana de su provincia |
| `viento_100m_media_m_s` | 2 | Ceuta y Melilla | Mediana nacional |

Los 6 casos peninsulares sin terminal ni autovía hay que revisarlos uno a uno con Elena: podrían ser enclaves o municipios isleños.

## Pendiente de decidir con Elena

1. **Incendios (EGIF, 54 %) e inundaciones (CNIH, 30 %).** Los huecos no son aleatorios: los municipios sin dato de incendios tienen una superficie mediana de 23 km², frente a 51 km² los que sí tienen; los que no tienen inundaciones registradas tienen una población mediana de 261 habitantes, frente a 3.527. Rellenar con cero haría parecer más seguros a los municipios pequeños solo porque se miden peor. Propuesta: dejarlos fuera de la versión 1 y probar en el #15 una variante con "sin registro = 0" más una columna que lo marque, comparando resultados.
2. **Agua subterránea (91 %).** Los 722 municipios sin masa catalogada no tienen un estado bueno ni malo. Misma propuesta que el punto 1.
3. **Qué estados cuentan como dato válido.** El dataset usa 18 estados y el contrato solo 3 (real, aproximado, pendiente). Relacionado con el issue #11.
4. **La columna `sentido` del diccionario mezcla dos nomenclaturas** (`mas_es_peor` / `menor_mejor` y `mas_es_mejor` / `mayor_mejor`). Convendría unificarla, también en el #11.

## Siguiente paso

Con esta lista, Elena prepara la matriz de entrenamiento (#13) y empieza el primer clustering (#14): imputación → transformaciones → `StandardScaler` → PCA (≥ 85 % de varianza, requisito del enunciado) → K-Means con K entre 2 y 10.
