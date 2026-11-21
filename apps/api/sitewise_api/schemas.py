"""Forma de las respuestas de la API (lo que reciben el frontend y el agente)."""

from __future__ import annotations

from pydantic import BaseModel

AVISO_ALCANCE = (
    "Valoración a escala municipal: no garantiza la aptitud de una parcela concreta. "
    "Las distancias son rectas, no tiempos ni distancias por carretera."
)


class Salud(BaseModel):
    estado: str  # "ok"
    datos_cargados: bool
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
    utilizable: bool = True
    motivo_no_utilizable: str | None = None


class FichaMunicipio(BaseModel):
    municipio: Municipio
    indicadores: list[ValorIndicador]
    aviso_alcance: str = AVISO_ALCANCE
