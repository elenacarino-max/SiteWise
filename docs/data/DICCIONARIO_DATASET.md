# Diccionario de datos · Sidewise v0.3

Última actualización del dataset: **14 de noviembre de 2026**.

## Alcance

El dataset contiene **8.132 municipios**, **36 indicadores** y **292.752 observaciones**. La clave municipal es `cod_ine`, siempre tratada como texto de cinco caracteres para conservar ceros iniciales.

Los ficheros principales se encuentran en `data/processed/sidewise_v03/`:

| Fichero | Granularidad | Clave | Contenido |
|---|---|---|---|
| `municipios.csv` | Una fila por municipio | `cod_ine` | Maestro territorial y coordenadas de referencia |
| `indicadores.csv` | Una fila por indicador | `id_indicador` | Catálogo canónico de definiciones, fuentes y metodología |
| `valores.csv` | Una fila por municipio e indicador | `cod_ine` + `id_indicador` | Valores en formato largo con trazabilidad |
| `dataset_municipal.csv` | Una fila por municipio | `cod_ine` | Matriz ancha para análisis, visualización y ML |

Los campos vacíos representan información no disponible o no publicable. **No deben convertirse automáticamente en cero.** El motivo se conserva en `estado` o en la columna `estado__<id_indicador>`.

## 1. Maestro de municipios

Fichero: `municipios.csv`.

| Campo | Tipo lógico | Nulo | Definición |
|---|---|---:|---|
| `cod_ine` | texto(5) | No | Código oficial del municipio. Clave primaria; conserva ceros iniciales. |
| `nombre` | texto | No | Denominación del municipio. |
| `cod_provincia` | texto(2) | No | Dos primeros caracteres de `cod_ine`. |
| `provincia` | texto | No | Nombre de la provincia. |
| `ccaa` | texto | No | Comunidad o ciudad autónoma. |
| `superficie_km2` | decimal | No | Superficie de la geometría municipal GISCO, en km². |
| `lat` | decimal | No | Latitud del punto interior de referencia, WGS84. |
| `lon` | decimal | No | Longitud del punto interior de referencia, WGS84. |
| `anio_geometria` | entero | No | Año de referencia de la geometría municipal; actualmente 2024. |

`lat` y `lon` son puntos de referencia para el municipio; no identifican una parcela ni garantizan que sean su centroide geométrico exacto.

## 2. Catálogo de indicadores

Fichero: `indicadores.csv`. Es la fuente canónica para interpretar cada indicador.

| Campo | Tipo lógico | Nulo | Definición |
|---|---|---:|---|
| `id_indicador` | texto | No | Identificador estable usado como nombre de columna en la matriz ancha. |
| `nombre` | texto | No | Nombre legible del indicador. |
| `bloque` | categoría | No | Área temática: demografía, empleo, agua, logística, etc. |
| `tipo` | categoría | No | Papel descriptivo: `riesgo`, `atractivo`, `contexto` o `recurso`. |
| `unidad` | texto | No | Unidad del valor. |
| `sentido` | categoría | No | Interpretación ordinal propuesta; puede depender de la actividad. |
| `fuente_id` | texto | No | Identificador corto de la fuente. |
| `fuente` | texto | No | Organismo o proveedor de origen. |
| `url` | URL/texto | No | Página o recurso de procedencia. |
| `fecha_dato` | texto | No | Fecha, periodo o referencia temporal del dato. |
| `nivel_origen` | categoría | No | Escala espacial original antes de asignarlo al municipio. |
| `metodo` | texto | No | Transformación o cálculo aplicado. |
| `naturaleza` | categoría | No | Observado, derivado, calculado, proxy o modelizado. |
| `limitaciones` | texto | Sí | Advertencias para interpretar y utilizar el indicador. |

### Indicadores disponibles

La cobertura se expresa como municipios con valor utilizable sobre 8.132.

| `id_indicador` | Definición | Unidad | Tipo | Periodo | Cobertura |
|---|---|---|---|---|---:|
| `poblacion_2024` | Población oficial 2024 | personas | contexto | 2024-01-01 | 8.132 |
| `poblacion_2025` | Población oficial 2025 | personas | contexto | 2025-01-01 | 8.132 |
| `variacion_poblacion_pct` | Variación de población entre 2024 y 2025 | % | contexto | 2024–2025 | 8.132 |
| `densidad_hab_km2` | Población 2025 por superficie municipal GISCO | habitantes/km² | contexto | 2025 / geometría 2024 | 8.132 |
| `cobertura_ftth_pct` | Hogares con cobertura FTTH | % hogares | atractivo | 2025-06 | 8.132 |
| `cobertura_100mbps_pct` | Hogares con cobertura de al menos 100 Mbps | % hogares | atractivo | 2025-06 | 8.132 |
| `cobertura_1gbps_pct` | Hogares con cobertura de al menos 1 Gbps | % hogares | atractivo | 2025-06 | 8.132 |
| `cobertura_5g_pct` | Hogares con cobertura 5G | % hogares | atractivo | 2025-06 | 8.132 |
| `tiepi_horas_prov_2021` | Tiempo de interrupción equivalente provincial | horas equivalentes | riesgo | 2021 | 8.132 |
| `niepi_prov_2021` | Número de interrupciones equivalentes provincial | interrupciones equivalentes | riesgo | 2021 | 8.132 |
| `siniestros_forestales_2006_2015_n` | Siniestros forestales iniciados | siniestros | riesgo | 2006–2015 | 4.375 |
| `superficie_forestal_afectada_2006_2015_ha` | Superficie forestal afectada acumulada | ha | riesgo | 2006–2015 | 4.375 |
| `siniestros_forestales_100km2_2006_2015` | Siniestros forestales normalizados por superficie | siniestros/100 km² | riesgo | 2006–2015 | 4.375 |
| `ha_afectadas_100km2_2006_2015` | Hectáreas afectadas normalizadas por superficie | ha/100 km² | riesgo | 2006–2015 | 4.375 |
| `eventos_cnih_2000_2023_n` | Eventos CNIH con daños municipales documentados | eventos codificados | riesgo | 2000–2023 | 2.480 |
| `ultimo_anio_cnih_2000_2023` | Año más reciente de un evento CNIH documentado | año | contexto | 2000–2023 | 2.480 |
| `irradiacion_ghi_kwh_m2_anio` | Irradiación horizontal global media | kWh/m²/año | atractivo | 2005–2023 | 8.132 |
| `estres_hidrico_pct` | Estrés hídrico medio del territorio municipal | % | riesgo | baseline 2019 | 8.108 |
| `agotamiento_hidrico_pct` | Agotamiento hídrico medio del territorio municipal | % | riesgo | baseline 2019 | 8.108 |
| `superficie_estres_ge40_pct` | Superficie válida con estrés hídrico igual o superior al 40 % | % | riesgo | baseline 2019 | 8.108 |
| `dist_recta_ttm_km` | Distancia recta a terminal de transporte de mercancías catalogada | km | atractivo | consulta 2026-11-13 | 7.971 |
| `dist_recta_ttm_intermodal_km` | Distancia recta a terminal intermodal catalogada | km | atractivo | consulta 2026-11-13 | 7.971 |
| `dist_recta_eje_autovia_km` | Distancia recta al eje de autopista o autovía | km | atractivo | consulta 2026-11-13 | 8.076 |
| `suelo_industrial_cartografiado_ha` | Superficie industrial presente en el catálogo cartográfico | ha | atractivo | 2020 | 8.132 |
| `suelo_industrial_cartografiado_pct` | Superficie industrial cartografiada respecto al municipio | % | contexto | 2020 | 8.132 |
| `paro_total` | Paro registrado total | personas | contexto | 2026-10 | 6.280 |
| `paro_agricultura` | Paro registrado en agricultura | personas | contexto | 2026-10 | 3.113 |
| `paro_industria` | Paro registrado en industria | personas | contexto | 2026-10 | 3.527 |
| `paro_construccion` | Paro registrado en construcción | personas | contexto | 2026-10 | 3.095 |
| `paro_servicios` | Paro registrado en servicios | personas | contexto | 2026-10 | 5.895 |
| `paro_sin_empleo_anterior` | Paro registrado sin empleo anterior | personas | contexto | 2026-10 | 3.104 |
| `contratos_total` | Contratos registrados totales | contratos | contexto | 2026-10 | 4.747 |
| `paro_variacion_interanual_pct` | Variación del paro frente al mismo mes del año anterior | % | contexto | 2025-10 / 2026-10 | 5.745 |
| `viento_100m_media_m_s` | Velocidad media modelizada del viento a 100 m | m/s | recurso | copia descargada 2026-11-14 | 8.130 |
| `agua_subterranea_mal_estado_cuantitativo_pct` | Superficie catalogada con masa en mal estado cuantitativo | % | riesgo | PHC 2022–2027 | 7.410 |
| `agua_subterranea_mal_estado_quimico_pct` | Superficie catalogada con masa en mal estado químico | % | riesgo | PHC 2022–2027 | 7.410 |

Las fórmulas, fuentes, URL y limitaciones completas de cada fila están en `indicadores.csv`. La cobertura detallada está en `cobertura_indicadores.csv`.

## 3. Valores en formato largo

Fichero: `valores.csv`. Contiene 292.752 filas: 8.132 municipios × 36 indicadores.

| Campo | Tipo lógico | Nulo | Definición |
|---|---|---:|---|
| `cod_ine` | texto(5) | No | Clave foránea a `municipios.csv`. |
| `valor` | decimal | Sí | Valor del indicador en la unidad declarada. |
| `id_indicador` | texto | No | Clave foránea a `indicadores.csv`. |
| `estado` | categoría | No | Calidad, disponibilidad o tratamiento de esa observación. |
| `nivel_origen` | categoría | No | Escala espacial de la fuente o del cálculo. |
| `fecha_dato` | texto | No | Periodo aplicable a la observación. |
| `fuente_id` | texto | No | Identificador de la fuente principal. |
| `naturaleza` | categoría | No | Naturaleza del dato o transformación. |
| `metodo` | texto | No | Método concreto aplicado al valor. |
| `url_fuente` | URL/texto | No | Recurso principal de procedencia. |
| `fuentes_adicionales` | texto | Sí | Fuentes auxiliares usadas en cruces o cálculos. |

### Valores controlados de `estado`

| Estado | Interpretación operativa |
|---|---|
| `real`, `publicado` | Valor observado o publicado por la fuente. |
| `aproximado`, `aproximado_modelo` | Valor asignado o estimado mediante una aproximación documentada. |
| `derivado_mismos_meses` | Cálculo derivado de periodos comparables. |
| `calculado_sobre_masas_catalogadas` | Cálculo restringido a la superficie con masas de agua catalogadas. |
| `agregado_fusion_documentada` | Valor agregado tras una fusión municipal documentada. |
| `base_cero` | No se calcula una variación porque el denominador es cero. |
| `blanco_fuente` | La fuente contiene una celda en blanco. |
| `ocultado_menor5` | El SEPE oculta una cifra inferior a cinco; no se imputa. |
| `fusion_con_celdas_no_publicadas` | La fusión incluye cifras protegidas o no publicadas. |
| `cobertura_insuficiente`, `sin_cobertura_suficiente` | La cobertura espacial no alcanza el umbral requerido. |
| `sin_datos_comparables` | Faltan periodos compatibles para el cálculo. |
| `sin_destino_catalogado_en_tierra` | No existe una infraestructura válida en el mismo componente terrestre. |
| `sin_masa_catalogada` | El municipio no intersecta una masa subterránea catalogada. |
| `sin_poligonos_en_catalogo` | No hay suelo industrial registrado en el catálogo utilizado. |
| `pendiente` | No existe un valor utilizable con las fuentes incorporadas. |

Los estados distintos de `real` o `publicado` no implican necesariamente que el dato sea inválido; obligan a consultar el método y sus limitaciones.

## 4. Matriz municipal ancha

Fichero: `dataset_municipal.csv`. Tiene 8.132 filas y 119 columnas:

- 9 columnas del maestro municipal.
- 36 columnas de valor, una por `id_indicador`.
- 36 columnas `estado__<id_indicador>`.
- 36 columnas `nivel_origen__<id_indicador>`.
- 2 columnas auxiliares de cobertura espacial.

| Patrón/campo | Tipo lógico | Definición |
|---|---|---|
| `<id_indicador>` | decimal nullable | Valor del indicador. |
| `estado__<id_indicador>` | categoría | Estado del valor correspondiente. |
| `nivel_origen__<id_indicador>` | categoría | Escala espacial de origen del valor. |
| `cobertura_viento_pct` | decimal nullable | Porcentaje de superficie municipal cubierto por celdas válidas del raster de viento. |
| `cobertura_masas_pct` | decimal nullable | Porcentaje de superficie municipal cubierto por masas de agua subterránea catalogadas. |

## 5. Reglas de uso

1. Leer `cod_ine` y `cod_provincia` como texto, nunca como entero.
2. Distinguir ausencia de dato de valor cero mediante `estado`.
3. No usar un proxy provincial como si fuera una medición municipal.
4. No interpretar automáticamente todos los indicadores numéricos como puntuaciones.
5. Los campos con sentido `depende_actividad` requieren una regla de negocio por actividad.
6. Si falta un dato imprescindible para un requisito mínimo, el resultado es `no_evaluable`.
7. Las distancias son rectas, no tiempos ni distancias por carretera.
8. El suelo industrial cartografiado no equivale a suelo libre o disponible.
9. Los indicadores hídricos no acreditan por sí solos caudal ni concesión de agua industrial.
10. Mantener fecha, fuente, estado y limitaciones visibles en la aplicación.

## 6. Relaciones

```text
municipios.cod_ine 1 ─── N valores.cod_ine
indicadores.id_indicador 1 ─── N valores.id_indicador

dataset_municipal = municipios + pivot(valores)
```

La metodología ampliada de empleo, viento y aguas subterráneas está documentada en `docs/data/sidewise_v03/METODOLOGIA.md`.
