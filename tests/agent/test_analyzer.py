"""
Pruebas unitarias para el Agente Analista (SiteWiseAnalyzer) con LLM y Retriever simulados.
"""

import json
import unittest
from unittest.mock import MagicMock, patch

from sitewise.agent.analyzer import SiteWiseAnalyzer


class TestSiteWiseAnalyzer(unittest.TestCase):
    """Batería de pruebas para las herramientas y el loop de ejecución del Analista."""

    def setUp(self):
        with patch("sitewise.agent.analyzer.Groq"):
            self.mock_retriever = MagicMock()
            self.analyzer = SiteWiseAnalyzer(
                model_name="mock-llama",
                retriever=self.mock_retriever,
            )
            self.mock_client = MagicMock()
            self.analyzer.client = self.mock_client

    # --- Pruebas de las herramientas individuales ---
    def test_tool_buscar_municipios_con_resultados(self):
        """Verifica que la herramienta formatee correctamente los resultados devueltos por el retriever."""
        self.mock_retriever.buscar.return_value = [
            {
                "content": "PERFIL DE ORTUELLA...",
                "metadata": {
                    "nombre": "Ortuella",
                    "cod_ine": "48083",
                    "provincia": "Bizkaia",
                    "ccaa": "País Vasco",
                },
                "distance_score": 0.12,
            }
        ]

        resultado = self.analyzer.tool_buscar_municipios(
            query="Bizkaia suelo industrial",
            k=4,
            min_suelo_industrial_ha=10.0,
            provincia="Bizkaia",
        )

        self.assertIn("Ortuella", resultado)
        self.assertIn("48083", resultado)
        self.assertEqual(len(self.analyzer.ultimos_datos_recuperados), 1)

    def test_tool_buscar_municipios_sin_resultados(self):
        """Verifica el mensaje retornado cuando no hay municipios que cumplan los filtros."""
        self.mock_retriever.buscar.return_value = []

        resultado = self.analyzer.tool_buscar_municipios(query="inexistente")
        self.assertIn("No se han encontrado municipios", resultado)

    def test_tool_consultar_municipio_ine_existente(self):
        """Verifica la recuperación exacta de un municipio por INE."""
        self.mock_retriever.buscar_municipio_por_ine.return_value = {
            "content": "PERFIL EXACTO ORTUELLA",
            "metadata": {"nombre": "Ortuella"},
        }

        resultado = self.analyzer.tool_consultar_municipio_ine("48083")
        self.assertIn("Ficha Municipal Exacta (INE 48083)", resultado)
        self.assertIn("PERFIL EXACTO ORTUELLA", resultado)

    def test_tool_consultar_municipio_ine_no_encontrado(self):
        """Verifica el mensaje cuando el código INE no existe."""
        self.mock_retriever.buscar_municipio_por_ine.return_value = None

        resultado = self.analyzer.tool_consultar_municipio_ine("99999")
        self.assertIn("No se encontró ningún municipio", resultado)

    # --- Pruebas del bucle de ejecución con LLM simulado ---
    def test_ejecutar_respuesta_directa_sin_tools(self):
        """Verifica que el agente devuelva la respuesta si el LLM no solicita herramientas."""
        mock_msg = MagicMock()
        mock_msg.tool_calls = None
        mock_msg.content = "Respuesta directa del consultor."
        self.mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=mock_msg)]
        )

        respuesta, docs = self.analyzer.ejecutar("Pregunta directa")
        self.assertEqual(respuesta, "Respuesta directa del consultor.")
        self.assertEqual(docs, [])

    def test_ejecutar_con_llamada_a_herramienta(self):
        """Verifica el flujo completo donde el LLM llama a buscar_municipios y luego responde."""
        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_123"
        mock_tool_call.function.name = "buscar_municipios_sitewise"
        mock_tool_call.function.arguments = json.dumps({
            "query": "suelo industrial Bizkaia",
            "k": 2,
            "min_suelo_industrial_ha": 15.0,
            "provincia": "Bizkaia",
        })

        turn1_msg = MagicMock()
        turn1_msg.tool_calls = [mock_tool_call]
        turn1_msg.content = None

        turn2_msg = MagicMock()
        turn2_msg.tool_calls = None
        turn2_msg.content = "Basado en los datos, recomiendo Ortuella."

        self.mock_client.chat.completions.create.side_effect = [
            MagicMock(choices=[MagicMock(message=turn1_msg)]),
            MagicMock(choices=[MagicMock(message=turn2_msg)]),
        ]

        self.mock_retriever.buscar.return_value = [
            {
                "content": "Ficha Ortuella: 56.5 ha suelo",
                "metadata": {
                    "nombre": "Ortuella",
                    "cod_ine": "48083",
                    "provincia": "Bizkaia",
                    "ccaa": "País Vasco",
                },
                "distance_score": 0.1,
            }
        ]

        respuesta, docs = self.analyzer.ejecutar("Busca suelo en Bizkaia")
        self.assertEqual(respuesta, "Basado en los datos, recomiendo Ortuella.")
        self.assertEqual(len(docs), 1)

    def test_ejecutar_con_feedback_supervisor(self):
        """Verifica que el feedback del supervisor se incluya en los mensajes enviados al LLM."""
        mock_msg = MagicMock()
        mock_msg.tool_calls = None
        mock_msg.content = "He corregido el análisis incluyendo los riesgos hídricos."
        self.mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=mock_msg)]
        )

        respuesta, _ = self.analyzer.ejecutar(
            user_prompt="Fábrica en Navarra",
            feedback_supervisor="Falta evaluar el estrés hídrico de la zona.",
        )

        self.assertIn("He corregido", respuesta)
        llamada_args = self.mock_client.chat.completions.create.call_args[1]
        mensajes_enviados = llamada_args["messages"]
        contenidos = [m.get("content", "") for m in mensajes_enviados if isinstance(m, dict)]
        self.assertTrue(any("FEEDBACK DEL SUPERVISOR" in c for c in contenidos))


if __name__ == "__main__":
    unittest.main()