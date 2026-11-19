"""
Módulo agent_graph.py: Orquestación multi-agente supervisada con LangGraph.
Implementa el ciclo de recomendación, auditoría con LLM Judge y feedback reflexivo.
"""

from typing import Any

from langgraph.graph import END, START, StateGraph

from sitewise.agent.analyzer import SiteWiseAgentDirect
from sitewise.agent.schemas import SiteWiseGraphState
from sitewise.agent.supervisor import SiteWiseSupervisor


class SiteWiseGraphOrchestrator:
    """Orquestador LangGraph que integra el Agente Analista y el LLM Judge."""

    def __init__(
        self,
        analyst_agent: SiteWiseAgentDirect | None = None,
        supervisor: SiteWiseSupervisor | None = None,
        max_revisions: int = 2,
    ):
        self.analyst = analyst_agent or SiteWiseAgentDirect()
        self.supervisor = supervisor or SiteWiseSupervisor()
        self.max_revisions = max_revisions
        self.graph = self._build_graph()

    # --- 1. Definición de los Nodos del Grafo ---
    def node_analyst(self, state: SiteWiseGraphState) -> dict[str, Any]:
        """Nodo del Agente Analista: busca datos y redacta o refina la recomendación."""
        user_query = state["user_query"]
        feedback_history = state.get("feedback_history", [])
        revision_count = state.get("revision_count", 0)

        ultimo_feedback = feedback_history[-1] if feedback_history else None

        if ultimo_feedback:
            print(f"\n[LangGraph] 🔄 Analista ejecutando ronda de corrección #{revision_count} con feedback...")
        else:
            print("\n[LangGraph] 🚀 Analista iniciando primera prospección para el usuario...")

        response_text, docs = self.analyst.ejecutar(
            user_prompt=user_query,
            feedback_supervisor=ultimo_feedback,
        )

        return {
            "agent_response": response_text,
            "context_docs": docs,
        }

    def node_supervisor(self, state: SiteWiseGraphState) -> dict[str, Any]:
        """Nodo del LLM Judge: audita la fidelidad de datos, análisis de riesgos y logística."""
        print("\n[LangGraph] ⚖️ LLM Judge auditando la propuesta del analista...")

        veredicto = self.supervisor.supervisar(
            user_query=state["user_query"],
            agent_response=state["agent_response"],
            context_docs=state.get("context_docs", []),
        )

        feedback_list = list(state.get("feedback_history", []))
        if not veredicto.aprobado and veredicto.feedback_mejora:
            feedback_list.append(veredicto.feedback_mejora)

        revision_count = state.get("revision_count", 0) + 1

        print(
            f"[LangGraph] 📋 Dictamen del Juez: Aprobado={veredicto.aprobado} | "
            f"Calidad={veredicto.puntuacion_calidad}/5 | "
            f"Datos verificados={veredicto.datos_contrastados} | "
            f"Riesgos evaluados={veredicto.analisis_riesgos_adecuado}"
        )

        return {
            "judge_evaluation": veredicto.model_dump(),
            "is_approved": veredicto.aprobado,
            "feedback_history": feedback_list,
            "revision_count": revision_count,
        }

    def node_finalizer(self, state: SiteWiseGraphState) -> dict[str, Any]:
        """Nodo de cierre: formatea la respuesta con la acreditación de auditoría del Juez."""
        dictamen = state.get("judge_evaluation", {})
        puntuacion = dictamen.get("puntuacion_calidad", 4)
        aprobado = dictamen.get("aprobado", True)
        revisado = state.get("revision_count", 1)

        insignia_estado = "Aprobado y contrastado con datos reales ✅" if aprobado else "Revisado con advertencias ⚠️"

        pie_supervision = (
            f"\n\n---\n"
            f"🛡️ **Control de Calidad SiteWise (LLM Judge):** {insignia_estado}\n"
            f"- **Puntuación de rigor técnico:** {puntuacion}/5\n"
            f"- **Auditoría de riesgos y logística:** {'Completa' if dictamen.get('analisis_riesgos_adecuado') else 'Parcial'}\n"
            f"- **Fidelidad de datos verificada:** {'100% verificada' if dictamen.get('datos_contrastados') else 'Requiere verificación manual'}\n"
            f"- **Iteraciones de supervisión:** {revisado}"
        )

        final_text = state["agent_response"] + pie_supervision
        return {"final_output": final_text}

    # --- 2. Borde Condicional ---
    def route_decision(self, state: SiteWiseGraphState) -> str:
        """Determina si la propuesta pasa la auditoría o necesita volver al analista."""
        is_approved = state.get("is_approved", False)
        revision_count = state.get("revision_count", 0)

        if is_approved:
            print("[LangGraph] ✅ Recomendación APROBADA por el supervisor. Finalizando...")
            return "finalizar"

        if revision_count >= self.max_revisions:
            print(f"[LangGraph] ⚠️ Alcanzado límite de {self.max_revisions} revisiones. Entregando con aviso...")
            return "finalizar"

        print("[LangGraph] 🔁 Recomendación RECHAZADA. Reenviando al analista con instrucciones de mejora...")
        return "corregir"

    # --- 3. Construcción y Compilación del Grafo ---
    def _build_graph(self):
        workflow = StateGraph(SiteWiseGraphState)

        # Añadimos los nodos
        workflow.add_node("analista", self.node_analyst)
        workflow.add_node("supervisor", self.node_supervisor)
        workflow.add_node("finalizador", self.node_finalizer)

        # Cableado del flujo
        workflow.add_edge(START, "analista")
        workflow.add_edge("analista", "supervisor")

        workflow.add_conditional_edges(
            "supervisor",
            self.route_decision,
            {
                "finalizar": "finalizador",
                "corregir": "analista",
            },
        )

        workflow.add_edge("finalizador", END)

        return workflow.compile()

    def run(self, user_query: str) -> dict[str, Any]:
        """Punto de entrada principal para ejecutar la consulta del usuario en el grafo."""
        initial_state: SiteWiseGraphState = {
            "user_query": user_query,
            "agent_response": "",
            "context_docs": [],
            "judge_evaluation": None,
            "feedback_history": [],
            "revision_count": 0,
            "is_approved": False,
            "final_output": "",
        }

        final_state = self.graph.invoke(initial_state)
        return final_state


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("DEMOSTRACIÓN DEL GRAFO MULTI-AGENTE SUPERVISADO (SITEWISE + LANGGRAPH)")
    print("=" * 80)

    orquestador = SiteWiseGraphOrchestrator(max_revisions=2)

    pregunta = (
        "Quiero establecer una fábrica de conservas vegetales en Navarra o Aragón con al menos 8 ha de suelo. "
        "El acceso a agua limpia y buen enlace con autovía son vitales. Analiza las alternativas y los riesgos hídricos."
    )

    print(f"\nConsulta recibida: '{pregunta}'\n")
    resultado = orquestador.run(pregunta)

    print("\n" + "=" * 80)
    print("RESULTADO FINAL SUPERVISADO ENTREGADO AL USUARIO:")
    print("=" * 80)
    print(resultado["final_output"])
