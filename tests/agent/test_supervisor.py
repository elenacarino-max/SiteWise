"""
Pruebas unitarias para el Supervisor / LLM Judge de SiteWise con LLM simulado.
"""

import json
import unittest
from unittest.mock import MagicMock, patch

from sitewise.agent.schemas import JudgeEvaluation
from sitewise.agent.supervisor import SiteWiseSupervisor


class TestSiteWiseSupervisor(unittest.TestCase):
    """Batería de pruebas para el auditor de calidad y veracidad."""

    def setUp(self):
        # Inicializamos el supervisor simulando el cliente de Groq
        with patch("sitewise.agent.supervisor.Groq"):
            self.supervisor = SiteWiseSupervisor(model_name="mock-model")
            self.mock_client = MagicMock()
            self.supervisor.client = self.mock_client

    def test_supervisar_aprobado_exitoso(self):
        """Verifica que una respuesta aprobada por el juez devuelva un JudgeEvaluation positivo."""
        mock_veredicto = {
            "aprobado": True,
            "puntuacion_calidad": 5,
            "datos_contrastados": True,
            "analisis_riesgos_adecuado": True,
            "analisis_logistica_adecuado": True,
            "feedback_mejora": "Excelente recomendación basada en datos reales.",
        }

        mock_choice = MagicMock()
        mock_choice.message.content = json.dumps(mock_veredicto)
        self.mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

        evaluacion = self.supervisor.supervisar(
            user_query="Planta industrial en Bizkaia",
            agent_response="Recomiendo Ortuella con 56 ha de suelo.",
            context_docs=["Ficha de Ortuella: Suelo industrial 56.5 ha."],
        )

        self.assertIsInstance(evaluacion, JudgeEvaluation)
        self.assertTrue(evaluacion.aprobado)
        self.assertEqual(evaluacion.puntuacion_calidad, 5)
        self.assertTrue(evaluacion.datos_contrastados)
        self.assertTrue(evaluacion.analisis_riesgos_adecuado)

    def test_supervisar_rechazado_por_alucinacion(self):
        """Verifica que el supervisor detecte alucinaciones y rechace la propuesta."""
        mock_veredicto = {
            "aprobado": False,
            "puntuacion_calidad": 1,
            "datos_contrastados": False,
            "analisis_riesgos_adecuado": False,
            "analisis_logistica_adecuado": True,
            "feedback_mejora": "Se inventaron datos de suelo y no se evaluó el estrés hídrico.",
        }

        mock_choice = MagicMock()
        mock_choice.message.content = json.dumps(mock_veredicto)
        self.mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

        evaluacion = self.supervisor.supervisar(
            user_query="Planta industrial",
            agent_response="Recomiendo municipio X con 500 ha de suelo inventado.",
            context_docs=["Ficha municipio X: Suelo 10 ha."],
        )

        self.assertFalse(evaluacion.aprobado)
        self.assertEqual(evaluacion.puntuacion_calidad, 1)
        self.assertFalse(evaluacion.datos_contrastados)
        self.assertIn("inventaron datos", evaluacion.feedback_mejora)

    def test_supervisar_error_parseo_no_aprueba(self):
        """Comprueba que si el modelo devuelve un JSON inválido, el dictamen sea NO VERIFICADO (rechazado)."""
        mock_choice = MagicMock()
        mock_choice.message.content = "Texto sin formato JSON válido {"
        self.mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

        evaluacion = self.supervisor.supervisar(
            user_query="Consulta X",
            agent_response="Respuesta Y",
            context_docs=["Doc Z"],
        )

        # Regla de seguridad: NUNCA aprobar ante fallo de parseo
        self.assertFalse(evaluacion.aprobado)
        self.assertEqual(evaluacion.puntuacion_calidad, 1)
        self.assertFalse(evaluacion.datos_contrastados)
        self.assertIn("No verificado", evaluacion.feedback_mejora)

    def test_supervisar_error_api_no_aprueba(self):
        """Comprueba que si falla la comunicación con la API, el dictamen sea NO VERIFICADO (rechazado)."""
        self.mock_client.chat.completions.create.side_effect = RuntimeError("Conexión perdida con Groq")

        evaluacion = self.supervisor.supervisar(
            user_query="Consulta X",
            agent_response="Respuesta Y",
            context_docs=["Doc Z"],
        )

        # Regla de seguridad: NUNCA aprobar ante error de API
        self.assertFalse(evaluacion.aprobado)
        self.assertEqual(evaluacion.puntuacion_calidad, 1)
        self.assertFalse(evaluacion.datos_contrastados)
        self.assertIn("No verificado", evaluacion.feedback_mejora)


if __name__ == "__main__":
    unittest.main()
