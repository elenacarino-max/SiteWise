"""
Pruebas unitarias para el Orquestador LangGraph de SiteWise con agentes simulados.
"""

import unittest
from unittest.mock import MagicMock

from sitewise.agent.agent_graph import SiteWiseGraphOrchestrator
from sitewise.agent.schemas import JudgeEvaluation, SiteWiseGraphState


class TestSiteWiseGraphOrchestrator(unittest.TestCase):
    """Batería de pruebas para los nodos, bordes y ejecución del grafo supervisado."""

    def setUp(self):
        self.mock_analyst = MagicMock()
        self.mock_supervisor = MagicMock()
        self.orchestrator = SiteWiseGraphOrchestrator(
            analyst_agent=self.mock_analyst,
            supervisor=self.mock_supervisor,
            max_revisions=2,
        )

    def test_node_analyst(self):
        """Verifica que el nodo analista invoque al agente y actualice el estado."""
        self.mock_analyst.ejecutar.return_value = (
            "Propuesta inicial de ubicación",
            ["Ficha municipal A", "Ficha municipal B"],
        )

        state: SiteWiseGraphState = {
            "user_query": "Busco parcela en Zaragoza",
            "agent_response": "",
            "context_docs": [],
            "judge_evaluation": None,
            "feedback_history": [],
            "revision_count": 0,
            "is_approved": False,
            "final_output": "",
        }

        output = self.orchestrator.node_analyst(state)
        self.assertEqual(output["agent_response"], "Propuesta inicial de ubicación")
        self.assertEqual(len(output["context_docs"]), 2)

    def test_node_supervisor(self):
        """Verifica que el nodo supervisor ejecute la auditoría y actualice los flags de aprobación."""
        mock_eval = JudgeEvaluation(
            aprobado=True,
            puntuacion_calidad=5,
            datos_contrastados=True,
            analisis_riesgos_adecuado=True,
            analisis_logistica_adecuado=True,
            feedback_mejora="Sin objeciones.",
        )
        self.mock_supervisor.supervisar.return_value = mock_eval

        state: SiteWiseGraphState = {
            "user_query": "Consulta",
            "agent_response": "Propuesta",
            "context_docs": ["Doc 1"],
            "judge_evaluation": None,
            "feedback_history": [],
            "revision_count": 0,
            "is_approved": False,
            "final_output": "",
        }

        output = self.orchestrator.node_supervisor(state)
        self.assertTrue(output["is_approved"])
        self.assertEqual(output["revision_count"], 1)
        self.assertEqual(output["judge_evaluation"]["puntuacion_calidad"], 5)

    def test_route_decision_aprobado(self):
        """Si está aprobado, debe rutear hacia 'finalizar'."""
        state = {"is_approved": True, "revision_count": 1}
        decision = self.orchestrator.route_decision(state)
        self.assertEqual(decision, "finalizar")

    def test_route_decision_rechazado_reintenta(self):
        """Si no está aprobado y quedan intentos, debe rutear hacia 'corregir'."""
        state = {"is_approved": False, "revision_count": 1}
        decision = self.orchestrator.route_decision(state)
        self.assertEqual(decision, "corregir")

    def test_route_decision_limite_revisiones_finaliza(self):
        """Si no está aprobado pero alcanzó el límite max_revisions, debe rutear hacia 'finalizar'."""
        state = {"is_approved": False, "revision_count": 2}
        decision = self.orchestrator.route_decision(state)
        self.assertEqual(decision, "finalizar")

    def test_run_flujo_completo_aprobado_a_la_primera(self):
        """Verifica la ejecución de punta a punta del grafo cuando se aprueba en el primer intento."""
        self.mock_analyst.ejecutar.return_value = ("Recomendación sólida", ["Doc 1"])
        self.mock_supervisor.supervisar.return_value = JudgeEvaluation(
            aprobado=True,
            puntuacion_calidad=5,
            datos_contrastados=True,
            analisis_riesgos_adecuado=True,
            analisis_logistica_adecuado=True,
            feedback_mejora="Perfecto.",
        )

        resultado = self.orchestrator.run("Quiero montar fábrica")

        self.assertTrue(resultado["is_approved"])
        self.assertEqual(resultado["revision_count"], 1)
        self.assertIn("Aprobado y contrastado con datos reales", resultado["final_output"])
        self.assertIn("Puntuación de rigor técnico:** 5/5", resultado["final_output"])

    def test_run_flujo_con_ronda_de_correccion(self):
        """Verifica el ciclo donde se rechaza primero y se aprueba en la segunda ronda."""
        # 1er turno: el analista genera propuesta con falta de riesgos
        # 2do turno: el analista corrige
        self.mock_analyst.ejecutar.side_effect = [
            ("Propuesta deficiente", ["Doc 1"]),
            ("Propuesta corregida y completa", ["Doc 1", "Doc 2"]),
        ]

        # 1er dictamen: rechazo
        # 2do dictamen: aprobación
        self.mock_supervisor.supervisar.side_effect = [
            JudgeEvaluation(
                aprobado=False,
                puntuacion_calidad=2,
                datos_contrastados=True,
                analisis_riesgos_adecuado=False,
                analisis_logistica_adecuado=True,
                feedback_mejora="Falta analizar el riesgo de incendios.",
            ),
            JudgeEvaluation(
                aprobado=True,
                puntuacion_calidad=4,
                datos_contrastados=True,
                analisis_riesgos_adecuado=True,
                analisis_logistica_adecuado=True,
                feedback_mejora="Riesgos analizados correctamente.",
            ),
        ]

        resultado = self.orchestrator.run("Quiero montar fábrica")

        self.assertTrue(resultado["is_approved"])
        self.assertEqual(resultado["revision_count"], 2)
        self.assertEqual(len(resultado["feedback_history"]), 1)
        self.assertIn("Propuesta corregida y completa", resultado["final_output"])
        self.assertIn("Iteraciones de supervisión:** 2", resultado["final_output"])


if __name__ == "__main__":
    unittest.main()
