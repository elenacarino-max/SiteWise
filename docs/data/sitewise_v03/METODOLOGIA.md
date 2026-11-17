# Decisiones de integración v0.3

## Alcance y unidad

Referencia: 8.132 municipios del maestro de las entregas anteriores. Se conservan sin cambios las 25 series v0.2. La geometría GISCO 1:1 millón es una aproximación territorial: sus bordes pueden diferir de catastros y del litoral de otros proveedores. No se busca coincidencia por nombre, sino por código y/o intersección espacial documentada.

No se asignan valores agregados de comunidades autónomas. El agua parte de masas de agua con geometría, no de un agregado autonómico: se reparte por intersección física, sin extender el mismo valor a toda una provincia o comunidad.

## SEPE

- Se identifican períodos en cabeceras de hojas. Los nombres descargados no codifican el mes.
- Se elimina un archivo byte a byte repetido; se conserva en el inventario con su SHA-256 y el original correspondiente.
- Se leen 52 hojas de paro y 52 de contratos por mes. Se toleran espacios iniciales y la errata CONTRTOS, pero se comprueba el total de hojas y la cabecera TOTAL.
- Un dato `<5` permanece ausente con estado `ocultado_menor5`. No se estima ni se reconstruye indirectamente.
- Originales y armonizados van separados. Las fusiones Cesuras/Oza dos Ríos y Cerdedo/Cotobade quedan documentadas con códigos de origen y traza de filas.
- Se descartan como cifras municipales los totales de provincia y filas sin municipio; se entregan por separado. Los totales provinciales publicados sí sirven para representar el contexto nacional.
- Se compara el último mes con el mismo mes del año anterior, únicamente con cifras publicadas y denominador positivo. No se calcula un total anual de 2026 incompleto.

Referencias: [SEPE](https://www.sepe.es/HomeSepe/que-es-el-sepe/estadisticas/datos-estadisticos/municipios.html), [INE Oza-Cesuras](https://www.ine.es/intercensal/intercensal.do?search=3&codigoProvincia=15&codigoMunicipio=902), [BOE Cerdedo-Cotobade](https://www.boe.es/buscar/doc.php?id=BOE-A-2017-898).

## Viento

Media de velocidades de celdas ponderada por área de intersección exacta en EPSG:6933. Se usan todos los píxeles válidos que tocan el polígono, se recortan en el borde y se conserva un indicador de cobertura. Si no alcanza 95 %, el valor final queda ausente. No se rellena con valores provinciales.

Fuente aportada: `ESP_wind-speed_100m.tif`, descargada del [Global Wind Atlas](https://globalwindatlas.info/en/download/gis-files). Unidad m/s y altura 100 m según el contexto de descarga. No se afirma una versión ni un período de observación que los metadatos de la copia no permiten verificar. No se calcula energía generada, factor de capacidad, rachas ni idoneidad legal de un aerogenerador.

## Agua subterránea

804 masas del CSV enlazadas uno a uno mediante `euGroundWaterBodyCode` / `cod_masa` con la geometría del WFS público MITECO `agua:masas_aguasub_2027`. Se conserva la descarga para repetir el cálculo; no se automatizan formularios con captcha.

Se reparan geometrías inválidas antes y después de proyectar. Se intersectan con los municipios y se disuelven por municipio: (a) toda la superficie catalogada, (b) masas en mal estado cuantitativo, (c) masas en mal estado químico. Cada porcentaje = área de b o c / área de a × 100. Se evita contar dos veces la superficie de horizontes superpuestos. Se mide presencia territorial de al menos una masa en mal estado, no un volumen ni proporción del agua extraíble.

El diccionario [WFD2022](https://dd.eionet.europa.eu/schema/WFD2022/GWB_2022.xsd/view) establece 2 bueno, 3 malo, U desconocido. Esta copia contiene estados 2 y 3. El notebook detiene el cálculo si aparecen desconocidos en una actualización, para revisar el denominador en vez de clasificarlos automáticamente como buenos.

Los años e intervalos de evaluación se guardan literalmente por masa. Las fechas previstas para lograr buen estado son objetivos, no predicciones garantizadas. La superficie sin masa no se considera buena ni mala.

Fuentes: [estado PHC 2022–2027](https://www.miteco.gob.es/es/cartografia-y-sig/ide/descargas/agua/estado-masas-agua-phc-2022-2027.html) y [geometrías PHC](https://www.miteco.gob.es/es/cartografia-y-sig/ide/descargas/agua/masas-de-agua-phc-2022-2027.html).

## Uso en la aplicación

Mostrar fecha, fuente y estado junto con cada valor. Los riesgos y recursos no comparten necesariamente sentido: más paro no se interpreta automáticamente como más disponibilidad de personal. Los indicadores con `depende_actividad` requieren una regla de actividad definida antes de puntuarlos. Las ausencias no deben convertirse en puntuación cero. Mantener separados los requisitos verificables sobre una parcela y el contexto municipal.

## Cobertura temporal municipal del SEPE

Enero de 2025 carece de fila para Usansolo (48916) en las tablas originales de paro y contratos. No se crea una cifra para ese municipio/mes. Los restantes meses incorporados tienen los 8.132 códigos actuales tras la armonización. El archivo `sepe_municipios_sin_fila.csv` permite auditar estas ausencias; el último mes usado por la aplicación sí se cruza con el maestro completo.

## Tablas posteriores al dataset

El diseño de Helen contempla también pesos por actividad y puntuaciones. No se rellenan sin criterios aprobados. Se entregan plantillas vacías en esta carpeta, fuera de las tablas de datos. Que una variable sea de contexto o recurso en el diccionario describe su contenido; antes de puntuarla, el equipo debe decidir su uso como riesgo o atractivo para una actividad. No hay que tratar todos los campos numéricos del archivo ancho como criterios de puntuación.

Cuando falte información para un requisito mínimo, el resultado debe ser `no_evaluable`; se descarta por incumplimiento únicamente cuando existe evidencia que permite evaluarlo. Para el agua industrial, ni Aqueduct ni el estado de una masa verifican por sí solos un caudal mínimo disponible.

La sismicidad que figura como propuesta añadida en la guía de Helen no se incorpora en esta versión. Tampoco se añade un indicador Seveso. Si el equipo confirma estos bloques como obligatorios, requerirán fuentes y un tratamiento específico; no se dan por cubiertos por los históricos de incendios o inundaciones.
