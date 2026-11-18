"""
Módulo schemas.py: Definición de esquemas Pydantic para las herramientas del agente.
"""


from pydantic import BaseModel, Field


class BuscarMunicipiosSchema(BaseModel):
    query: str = Field(..., description="Descripción o consulta sobre el tipo de municipio buscado.")
    k: int = Field(4, description="Número de municipios a recuperar (por defecto 4).")
    min_suelo_industrial_ha: float = Field(0.0, description="Mínimo de hectáreas de suelo industrial requeridas.")
    max_estres_hidrico_pct: float = Field(100.0, description="Porcentaje máximo de estrés hídrico tolerado.")
    provincia: str | None = Field(None, description="Nombre opcional de la provincia.")


class ConsultarMetodologiaSchema(BaseModel):
    query: str = Field(..., description="Pregunta sobre la metodología de cálculo o fuentes de datos de SiteWise.")