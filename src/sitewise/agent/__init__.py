"""Módulo agent de SiteWise: Agentes analistas, LLM Judge y orquestación con LangGraph."""

# Esquemas (ligeros, sin dependencias pesadas) → importación directa
from sitewise.agent.schemas import (
    AGENT_TOOLS_SCHEMA,
    BuscarMunicipiosSchema,
    ConsultarMetodologiaSchema,
    ConsultarMunicipioPorINESchema,
    JudgeEvaluation,
    SiteWiseGraphState,
)

from sitewise.agent.prompts import (
    ANALYST_FEEDBACK_TEMPLATE,
    ANALYST_SYSTEM_PROMPT,
    SUPERVISOR_AUDIT_TEMPLATE,
    SUPERVISOR_SYSTEM_PROMPT,
)

__all__ = [
    "AGENT_TOOLS_SCHEMA",
    "BuscarMunicipiosSchema",
    "ConsultarMetodologiaSchema",
    "ConsultarMunicipioPorINESchema",
    "JudgeEvaluation",
    "SiteWiseAgentDirect",
    "SiteWiseAnalyzer",
    "SiteWiseGraphOrchestrator",
    "SiteWiseGraphState",
    "SiteWiseSupervisor",
]


# Lazy imports: las clases pesadas solo se cargan al acceder a ellas,
# evitando el RuntimeWarning cuando se ejecutan con python -m.
def __getattr__(name: str):
    if name in ("SiteWiseAnalyzer", "SiteWiseAgentDirect"):
        from sitewise.agent.analyzer import SiteWiseAnalyzer
        return SiteWiseAnalyzer
    if name == "SiteWiseSupervisor":
        from sitewise.agent.supervisor import SiteWiseSupervisor
        return SiteWiseSupervisor
    if name == "SiteWiseGraphOrchestrator":
        from sitewise.agent.agent_graph import SiteWiseGraphOrchestrator
        return SiteWiseGraphOrchestrator
    raise AttributeError(f"module 'sitewise.agent' has no attribute {name!r}")
