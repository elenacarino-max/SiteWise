"""
Módulo schemas.py: Punto central de contratos de datos y esquemas del sistema de agentes.

Incluye:
1. Esquemas Pydantic para argumentos de herramientas (Tools).
2. Esquema Pydantic estructurado para el veredicto del Supervisor (LLM Judge).
3. Esquema TypedDict para el estado compartido en el grafo (LangGraph).
4. Catálogo estructurado de especificaciones de herramientas para Function Calling.
"""

from typing import Any, TypedDict
from pydantic import BaseModel, Field


# ==============================================================================
# 1. ESQUEMAS DE ENTRADA PARA LAS HERRAMIENTAS (TOOLS)
# ==============================================================================

class BuscarMunicipiosSchema(BaseModel):
    """Parámetros de búsqueda semántica e híbrida de municipios."""
    query: str = Field(
        ...,
        description="Descripción o consulta sobre el perfil del municipio o actividad económica buscada."
    )
    k: int = Field(
        4,
        ge=1,
        le=6,
        description="Número de municipios a recuperar (por defecto 4, máximo 6)."
    )
    min_suelo_industrial_ha: float = Field(
        0.0,
        description="Mínimo de hectáreas de suelo industrial requeridas."
    )
    max_estres_hidrico_pct: float = Field(
        100.0,
        description="Porcentaje máximo de estrés hídrico tolerado."
    )
    provincia: str | None = Field(
        None,
        description="Nombre opcional de la provincia (ej. 'Bizkaia', 'Madrid', 'Zaragoza')."
    )
    ccaa: str | None = Field(
        None,
        description="Nombre opcional de la Comunidad Autónoma (ej. 'País Vasco', 'Aragón', 'Navarra')."
    )
    cluster: str | None = Field(
        None,
        description="Etiqueta opcional del clúster municipal (ej. 'Polo Industrial')."
    )


class ConsultarMunicipioPorINESchema(BaseModel):
    """Parámetros para recuperar una ficha municipal exacta por código INE."""
    cod_ine: str = Field(
        ...,
        description="Código INE de 5 dígitos del municipio a consultar (ej. '48083', '28079')."
    )


class ConsultarMetodologiaSchema(BaseModel):
    """Parámetros para consultar manuales y gobernanza de SiteWise."""
    query: str = Field(
        ...,
        description="Pregunta sobre la metodología de cálculo, fuentes o gobernanza del dataset de SiteWise."
    )


# ==============================================================================
# 2. ESQUEMA DE EVALUACIÓN Y AUDITORÍA DEL SUPERVISOR (LLM JUDGE)
# ==============================================================================

class JudgeEvaluation(BaseModel):
    """Dictamen de auditoría y evaluación estructurada devuelto por el LLM Judge."""
    aprobado: bool = Field(
        ...,
        description="True si la recomendación es sólida, fiel a los datos y analiza riesgos; False si contiene alucinaciones o deficiencias graves."
    )
    puntuacion_calidad: int = Field(
        ...,
        ge=1,
        le=5,
        description="Puntuación global del 1 al 5 sobre la calidad y rigurosidad del análisis."
    )
    datos_contrastados: bool = Field(
        ...,
        description="True si los datos numéricos citados (ha, km, % paro, etc.) coinciden con los datos reales devueltos por el sistema y no fueron inventados."
    )
    analisis_riesgos_adecuado: bool = Field(
        ...,
        description="True si se analizan explícitamente los riesgos (hídrico, calidad de acuíferos, incendios, eventos extremos CNIH)."
    )
    analisis_logistica_adecuado: bool = Field(
        ...,
        description="True si se valora la distancia a autovía, terminales de mercancías (TTM) o conectividad."
    )
    feedback_mejora: str = Field(
        ...,
        description="Explicación detallada de los puntos fuertes y de las correcciones necesarias que el agente debe corregir si aprobado es False."
    )


# ==============================================================================
# 3. ESQUEMA DEL ESTADO DEL GRAFO (LANGGRAPH STATE)
# ==============================================================================

class SiteWiseGraphState(TypedDict):
    """Estado compartido en el grafo multi-agente supervisado."""
    user_query: str
    agent_response: str
    context_docs: list[str]
    judge_evaluation: dict[str, Any] | None
    feedback_history: list[str]
    revision_count: int
    is_approved: bool
    final_output: str


# ==============================================================================
# 4. ESPECIFICACIÓN JSON SCHEMA PARA FUNCTION CALLING (API DE MODELOS)
# ==============================================================================

AGENT_TOOLS_SCHEMA: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "buscar_municipios_sitewise",
            "description": "Busca fichas municipales reales en España utilizando semántica y filtros de suelo industrial, estrés hídrico, provincia, CCAA o clúster.",
            "parameters": BuscarMunicipiosSchema.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_municipio_ine",
            "description": "Recupera la ficha detallada de un municipio mediante su código INE exacto de 5 dígitos.",
            "parameters": ConsultarMunicipioPorINESchema.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_metodologia_sitewise",
            "description": "Consulta la documentación técnica, manuales y gobernanza del proyecto SiteWise.",
            "parameters": ConsultarMetodologiaSchema.model_json_schema(),
        },
    },
]



# ==============================================================================
# 3. ESQUEMA DEL ESTADO DEL GRAFO (LANGGRAPH STATE)
# ==============================================================================

class SiteWiseGraphState(TypedDict):
    """Estado compartido en el grafo multi-agente supervisado."""
    user_query: str
    agent_response: str
    context_docs: list[str]
    judge_evaluation: dict[str, Any] | None
    feedback_history: list[str]
    revision_count: int
    is_approved: bool
    final_output: str


# ==============================================================================
# 4. ESPECIFICACIÓN JSON SCHEMA PARA FUNCTION CALLING (API DE MODELOS)
# ==============================================================================

AGENT_TOOLS_SCHEMA: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "buscar_municipios_sitewise",
            "description": "Busca fichas municipales reales en España utilizando semántica y filtros de suelo industrial, estrés hídrico, provincia, CCAA o clúster.",
            "parameters": BuscarMunicipiosSchema.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_municipio_ine",
            "description": "Recupera la ficha detallada de un municipio mediante su código INE exacto de 5 dígitos.",
            "parameters": ConsultarMunicipioPorINESchema.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_metodologia_sitewise",
            "description": "Consulta la documentación técnica, manuales y gobernanza del proyecto SiteWise.",
            "parameters": ConsultarMetodologiaSchema.model_json_schema(),
        },
    },
]