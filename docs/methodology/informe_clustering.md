# Informe de clustering de municipios

Issue #16 (ML-04) · Versión del modelo: `v02` · Responsable: Helen · Noviembre de 2026 · Estado: borrador

Este informe cuenta **cómo se llegó** a los 4 perfiles de municipios actuales (v02), por qué se sustituyó el primer modelo (v01) y qué conviene saber antes de usarlos. La descripción corta del modelo está en la ficha (`model_card_clustering.md`) y los criterios de variables, en `seleccion_variables_ml.md`.

## 1. Resumen

- Se agrupan los municipios de España en **4 perfiles** con K-Means (K=4), usando **tres índices de 0 a 100**: logística, hídrica y conectividad. Sin PCA ni escalado, porque los tres ya están en la misma escala.
- Tienen perfil **7.975 de 8.132 municipios (98,1 %)**. Los 157 restantes no tienen distancia a terminal de mercancías y no se imputan.
- **K=4 se eligió por interpretación, no por una métrica.** El silhouette es más alto con K=2 (0,307) y baja hasta 0,253 con K=8 (0,290 con K=4). K=3 también sería defendible.
- Los grupos son **estables**: con distintas semillas el resultado es casi igual (ARI mínimo 0,995 con K=4).
- **Un perfil no es un riesgo.** Describe el territorio; no dice si es bueno o malo para una actividad. El riesgo se calcula aparte.
- Es un análisis **exploratorio**. Los nombres de los perfiles son provisionales (los cierra Gema).

## 2. Por qué se cambió el modelo (v01 → v02)

El primer modelo (v01) usaba 7 variables (población, suelo industrial, autovía, terminal, paro, viento y agua), PCA y K=5. Tras la revisión técnica con el stakeholder (Juan Miguel) se acordó priorizar el **significado sobre el ajuste**:

| | v01 | v02 |
|---|---|---|
| Entradas | 7 variables sueltas | 3 índices temáticos (máximo acordado: 3–4 entradas) |
| Preparación | log, recorte, estandarizado y PCA | Percentiles de 0 a 100; sin PCA |
| K | 5 (por interpretación) | 4 (por interpretación) |
| Atípicos | DBSCAN (360 marcados) | No se evalúan (`es_atipico` = 0) |
| Cobertura | 8.132 (huecos rellenados con máximo o mediana) | 7.975 (sin imputar la logística) |
| Variables de población, paro y viento | Dentro del perfil | Fuera: datos sueltos para filtros, scoring y RAG |

Motivos principales: con PCA los perfiles dependían de una transformación difícil de explicar a una empresa; el paro de los grupos rurales dependía en parte de valores rellenados; y el grupo de agua era el único que se explicaba con una variable. Los notebooks y ficheros de v01 siguen en el historial de Git (commit `bc30250`).

## 3. Datos y variables

| Índice | Componentes | Sentido |
|---|---|---|
| Logística | `suelo_industrial_cartografiado_pct`, `dist_recta_eje_autovia_km`, `dist_recta_ttm_km` | Más alto, mejor (las distancias se invierten) |
| Hídrica | `estres_hidrico_pct`, `agua_subterranea_mal_estado_cuantitativo_pct` | Más alto, más presión |
| Conectividad | `cobertura_ftth_pct`, `cobertura_5g_pct` | Más alto, mejor |

Cada componente se convierte en percentil (rango medio) sobre los municipios con dato y el índice es la media de sus componentes (código en `src/sitewise/ml/indices.py`).

### Huecos

**Regla general: los valores estimados se marcan y se muestran como `aproximado`.**

| Hueco | Municipios | Tratamiento |
|---|---|---|
| Distancia a terminal de mercancías | 157 | No se imputa: sin perfil (`sin_dato_logistica(terminal)`) |
| Agua subterránea sin masa catalogada | 722 | Media de los 5 municipios cercanos con dato; se marca |
| Estrés hídrico | 24 | Igual |

Comprobación de la estimación del agua (ocultando municipios con dato y estimándolos con vecinos de otras provincias): error medio **12,8 puntos**, frente a 16,5 poniendo 0 y 26,1 con la media de todos los municipios; correlación con el valor real de 0,67. Es la mejor de las tres opciones, pero deja un error apreciable.

## 4. Experimentos (notebooks 05 y 06)

El notebook 05 prueba K de 2 a 8 y varias alternativas de entradas; el 06 registra los resultados en MLflow (`sitewise-perfil-v02`) sin recalcular.

| K | Silhouette | Davies-Bouldin | Grupo más pequeño | ARI mínimo |
|---|---|---|---|---|
| 2 | 0,307 | 1,29 | 45,0 % | 0,994 |
| 3 | 0,299 | 1,18 | 24,3 % | 0,993 |
| **4** | **0,290** | **1,13** | **19,9 %** | **0,995** |
| 5 | 0,278 | 1,05 | 17,0 % | 0,977 |
| 6 | 0,271 | 1,06 | 12,7 % | 0,964 |
| 7 | 0,260 | 1,10 | 11,2 % | 0,880 |
| 8 | 0,253 | 1,12 | 9,0 % | 0,908 |

- Ninguna métrica señala un K claro. Es lo esperable: los índices son percentiles casi uniformes, así que K-Means **corta un continuo**.
- **K=3** da tres perfiles claros, pero junta a los municipios aislados y mal conectados con los de poca logística pero buena fibra y 5G.
- **K=4** separa esos dos casos y es la partición más pequeña en la que cada grupo se explica con una frase.
- **K=5** añade un grupo intermedio difícil de describir.
- Alternativa descartada: añadir el índice natural (JRC) dejaría solo el 49,5 % de los municipios con perfil.
- Las silhouettes de espacios distintos (v01 y v02) **no son comparables**.

## 5. Los 4 perfiles

Los grupos se ordenan por la media del índice de logística (0 = mejor).

| Grupo | Perfil | Municipios | Logística | Hídrica | Conectividad |
|---|---|---|---|---|---|
| 0 | Buena logística y buena conectividad | 1.876 | 75 | 40 | 66 |
| 1 | Logística media-buena con mucha presión hídrica | 1.584 | 58 | 80 | 59 |
| 2 | Logística baja y mal conectados | 2.470 | 40 | 42 | 24 |
| 3 | Logística baja pero bien conectados | 2.045 | 33 | 43 | 59 |

Medias de cada índice. Las medianas de las variables originales están en `data/reference/perfiles_definicion_v02.csv`.

- **Grupo 0:** suelo industrial (mediana 0,5 %), autovía a 3 km, terminal a 29 km y fibra y 5G casi completas.
- **Grupo 1:** se define por la presión hídrica (estrés hídrico con mediana de 295 %; en los datos toma valores superiores a 100).
- **Grupo 2:** zonas aisladas: autovía a 15 km, terminal a 62 km y fibra al 75 % (5G al 89 %).
- **Grupo 3:** igual de lejos de autovía y terminal, pero con fibra al 94 % y 5G al 100 %.

## 6. Municipios cercanos

Para cada municipio, los 5 más **cercanos en el mapa**, en `data/reference/municipios_cercanos_v01.csv` (40.660 filas). Se generan con el notebook 10 y `src/sitewise/ml/cercanos.py`. No dependen del modelo de perfiles.

- **Qué es:** distancia en línea recta (haversine) entre los puntos `lat` y `lon` de cada municipio.
- **Por qué:** el agua y los riesgos naturales dependen del territorio, así que un municipio se compara con los que tiene al lado.
- **Cercano no es parecido en características.**
- El 92 % de los cercanos son de la misma provincia y el 96,6 % de la misma comunidad autónoma; la mediana de la distancia media es de 6,7 km.
- Comparten el agua y el estrés hídrico (correlación de Spearman de 0,88 a 0,97) y, en menor medida, inundaciones e incendios (de 0,52 a 0,74). Con municipios al azar sale casi 0.
- **Casos lejanos:** Melilla (164 km de media), Ceuta, Canarias y Formentera. `distancia_km` permite avisar al usuario.

## 7. Limitaciones

1. **Es un continuo, no cuatro bloques separados.** Un municipio cerca de la frontera entre dos perfiles podría estar en cualquiera.
2. **K=4 se decide por interpretación**; K=3 sería igualmente defendible.
3. **157 municipios sin perfil:** Baleares, Canarias, Ceuta y Melilla, sin distancia a terminal de mercancías por tierra. Hacinas, Monasterio de la Sierra, Llívia y A Illa de Arousa tenían el dato vacío por cómo se calculaba y se corrigió el 27 de noviembre de 2026 (PR #61, notebook 02): ahora tienen perfil.
4. **El índice hídrica usa datos estimados** (722 de agua subterránea y 24 de estrés hídrico), con error medio de 12,8 puntos. El agua química no está incluida.
5. **El grupo 1 se define por la presión hídrica.**
6. **`es_atipico` vale 0 en todos:** en v02 no se evalúan atípicos.
7. **Ajustado con todos los municipios a la vez:** no se ha medido con municipios nuevos.
8. **El perfil no incluye** población, paro, viento ni riesgos naturales (incendios, inundaciones): se consultan aparte.
9. **Los nombres de los perfiles son provisionales.**
10. **Modelo exploratorio:** no usar para decidir inversiones.

## 8. Cómo se usa

- **Perfiles:** `data/reference/perfiles_municipios_v02.csv` (7.975 filas, ordenado por `cod_ine`) con `cod_ine` (texto de 5 dígitos), `cluster` (0–3), `cluster_perfil`, `es_atipico` y `version_modelo`.
- **Definición:** `data/reference/perfiles_definicion_v02.csv`.
- **Estado por municipio:** `data/reference/perfiles_estado_v02.csv` (8.132 filas): si tiene perfil, motivo si no, datos estimados e índices.
- **API (Adriana):** carga la versión más alta común a los dos CSV de perfiles. Los municipios sin perfil devuelven `perfil_no_disponible` (404). Faltan en `esquema.py` seis columnas de la definición nueva (medianas de estrés hídrico, fibra y 5G y las tres medias de índices), que hoy se ignoran.
- **Endpoint de cercanos:** todavía no existe; queda para un PR aparte.
- **Regla para el agente y la aplicación:** un perfil describe el territorio y **nunca** se mezcla con riesgo o atractivo.

### Pendiente

- Confirmar con Gema los nombres de los perfiles.
- Enseñar a Juan Miguel la justificación de K=4 (y la alternativa K=3).
- Decidir qué hace la API con los cercanos muy lejanos (umbral de `distancia_km`).

## 9. Archivos y reproducibilidad

| Fichero | Para qué |
|---|---|
| `notebooks/04_decision_variables_perfil.ipynb` | Qué variable va a cada uso |
| `notebooks/05_clustering_kmeans.ipynb` | Experimentos de K y de entradas |
| `notebooks/06_mlflow_experimentos.ipynb` | Registro en MLflow |
| `notebooks/07_perfiles_municipios.ipynb` | Perfiles y ficheros de salida |
| `notebooks/08_estimaciones_vecinos_app.ipynb` | Agua estimada para la app |
| `notebooks/10_municipios_cercanos.ipynb` | Municipios cercanos |
| `src/sitewise/ml/indices.py` | Índices y estimación con vecinos |
| `src/sitewise/ml/experimentos.py` | Barrido de K y estabilidad |
| `src/sitewise/ml/perfiles.py` | Nombres y descripciones de los perfiles |
| `src/sitewise/ml/cercanos.py` | Municipios cercanos |

Para regenerar, ejecutar los notebooks 04 a 08 y 10 **en orden** (Restart & Run All en cada uno) y después:

```bash
PYTHONPATH=src python -m pytest tests/ml -q
```

Si cambian los datos o las variables, hay que revisar nombres y descripciones, porque las cifras de la descripción son medianas actuales. `src/sitewise/ml/pipeline.py` es del modelo v01 y no se usa en v02.
