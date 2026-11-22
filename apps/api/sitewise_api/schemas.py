"""Forma de las respuestas de la API (lo que reciben el frontend y el agente)."""

from __future__ import annotations

from pydantic import BaseModel

from sitewise.scoring.modelos import Evaluacion

AVISO_ALCANCE = (
    "Valoración a escala municipal: no garantiza la aptitud de una parcela concreta. "
    "Las distancias son rectas, no tiempos ni distancias por carretera."
)


class Salud(BaseModel):
    estado: str  # "ok"
    datos_cargados: bool
    origen: str | None = None  # "csv" o "postgresql"
    valores_fichero: str | None = None  # "valores_app.csv" o "valores.csv" (solo con origen csv)
    municipios: int | None = None
    indicadores: int | None = None
    observaciones: int | None = None
    detalle: str = ""


class Municipio(BaseModel):
    cod_ine: str
    nombre: str
    cod_provincia: str | None = None
    provincia: str | None = None
    ccaa: str | None = None
    superficie_km2: float | None = None
    lat: float | None = None
    lon: float | None = None


class ListaMunicipios(BaseModel):
    total: int  # cuántos cumplen el filtro (no solo los de esta página)
    limite: int
    desplazamiento: int
    municipios: list[Municipio]


class ValorIndicador(BaseModel):
    """Un indicador de un municipio, con su trazabilidad.

    `utilizable` dice si el dato sirve para calcular; si no, `motivo_no_utilizable` explica por qué.
    Un valor NUNCA se interpreta como 0 cuando falta: `valor` es null y el estado lo explica.
    """

    id_indicador: str
    nombre: str | None = None
    bloque: str | None = None
    tipo: str | None = None
    unidad: str | None = None
    limitaciones: str | None = None
    valor: float | None = None
    estado: str | None = None
    nivel_origen: str | None = None
    fecha_dato: str | None = None
    fuente_id: str | None = None
    naturaleza: str | None = None
    aproximado: bool = False
    # Valor estimado con los vecinos (agua subterránea, notebook 09): cómo se estimó y con qué distancias.
    estimado: bool = False
    metodo: str | None = None
    vecinos: int | None = None
    distancia_media_km: float | None = None
    distancia_maxima_km: float | None = None
    utilizable: bool = True
    motivo_no_utilizable: str | None = None


class FichaMunicipio(BaseModel):
    municipio: Municipio
    indicadores: list[ValorIndicador]
    aviso_alcance: str = AVISO_ALCANCE


class ResumenActividad(BaseModel):
    """Una actividad y el estado de sus reglas (para listarla antes de evaluar nada)."""

    actividad: str
    estado_reglas: str  # "aprobadas" solo si TODAS las reglas están firmadas; si no, "provisionales"
    n_reglas: int
    n_minimos: int
    n_puntuables: int
    n_aprobadas: int
    version_reglas: str


class ListaActividades(BaseModel):
    actividades: list[ResumenActividad]
    aviso: str = ""  # por ejemplo: todavía no hay reglas, o hay reglas provisionales


class RespuestaEvaluacion(BaseModel):
    """Evaluación de un municipio para una actividad: riesgo y atractivo por separado."""

    municipio: Municipio
    evaluacion: Evaluacion
    aviso_alcance: str = AVISO_ALCANCE


class FilaResumen(BaseModel):
    """Una fila de la tabla comparativa: lo esencial de cada municipio, sin mezclar riesgo y atractivo."""

    cod_ine: str
    nombre: str
    riesgo_nota: float | None = None
    riesgo_estado: str
    riesgo_confianza: float = 0.0
    atractivo_nota: float | None = None
    atractivo_estado: str
    atractivo_confianza: float = 0.0
    cumple_minimos: str


class IndicadorComparado(BaseModel):
    """Un indicador de las reglas con el valor de cada municipio (clave = cod_ine).

    Si un municipio no tiene observación de ese indicador, su valor es null.
    """

    id_indicador: str
    nombre: str | None = None
    unidad: str | None = None
    uso: str  # riesgo | atractivo | contexto, según las reglas de la actividad
    valores: dict[str, ValorIndicador | None]


class RespuestaComparacion(BaseModel):
    actividad: str
    version_reglas: str
    reglas_provisionales: bool
    resumen: list[FilaResumen]
    indicadores: list[IndicadorComparado]
    evaluaciones: list[RespuestaEvaluacion]
    aviso_comparacion: str = (
        "Riesgo y atractivo se muestran por separado: no hay nota única ni un municipio 'ganador'."
    )
    aviso_alcance: str = AVISO_ALCANCE


class FilaMapa(BaseModel):
    """Un municipio con sus dos notas para una actividad. Pensada para pintar un mapa o una tabla."""

    cod_ine: str
    nombre: str
    provincia: str | None = None
    ccaa: str | None = None
    lat: float | None = None
    lon: float | None = None
    riesgo_nota: float | None = None
    riesgo_estado: str
    riesgo_confianza: float = 0.0
    atractivo_nota: float | None = None
    atractivo_estado: str
    atractivo_confianza: float = 0.0
    cumple_minimos: str


class FilaRanking(FilaMapa):
    posicion: int  # 1 = primero según el orden pedido


class RespuestaRanking(BaseModel):
    actividad: str
    ordenado_por: str  # atractivo | riesgo
    orden: str  # mejor_primero | peor_primero
    total: int  # municipios con nota en esa dimensión que cumplen los filtros
    sin_nota: int  # municipios que cumplen los filtros pero no tienen nota en esa dimensión
    limite: int
    desplazamiento: int
    filas: list[FilaRanking]
    version_reglas: str
    reglas_provisionales: bool
    aviso_comparacion: str = (
        "Se ordena por una sola dimensión cada vez: riesgo y atractivo no se mezclan en una nota única."
    )
    aviso_alcance: str = AVISO_ALCANCE


class RespuestaMapa(BaseModel):
    actividad: str
    total: int
    filas: list[FilaMapa]
    version_reglas: str
    reglas_provisionales: bool
    aviso_alcance: str = AVISO_ALCANCE
