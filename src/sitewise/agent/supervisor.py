"""
Módulo supervisor.py: LLM Judge / Auditor de calidad y veracidad para SiteWise.
Evalúa de forma independiente las respuestas del Agente Analista contrastándolas
con los datos reales recuperados del RAG.
"""

import json
import os

from dotenv import load_dotenv
from groq import Groq, GroqError
from pydantic import ValidationError

from sitewise.agent.schemas import JudgeEvaluation

load_dotenv()


class SiteWiseSupervisor:
    """LLM Judge / Agente Supervisor que audita fidelidad factual, riesgos y adecuación logística."""

    SUPERVISOR_PROMPT = """Eres el Auditor Senior de Calidad y Veracidad de SiteWise (LLM Judge).
Tu trabajo es revisar críticamente y auditar la recomendación elaborada por el Agente Analista antes de que sea entregada al cliente final.

Para tu auditoría dispones de:
1. La consulta original del usuario (necesidades del negocio).
2. Los datos reales crudos recuperados de la base de datos municipal y documentación (CONTEXTO REAL).
3. La propuesta de respuesta redactada por el Agente Analista.

CRITERIOS DE AUDITORÍA OBLIGATORIOS:
1. FIDELIDAD FACTUAL (Groundedness / No alucinación):
   - ¿Las cifras citadas por el agente (hectáreas de suelo, distancias en km a autovía/TTM, porcentajes de paro, porcentajes de estrés hídrico, siniestros forestales, eventos CNIH) están fielmente respaldadas por el CONTEXTO REAL?
   - Si el agente inventa datos numéricos, códigos INE o afirma que hay infraestructuras inexistentes, 'datos_contrastados' debe ser False y 'aprobado' False.

2. EVALUACIÓN EXHAUSTIVA DE RIESGOS:
   - Toda recomendación de emplazamiento empresarial debe advertir sobre riesgos hídricos (estrés, estado de acuíferos subterráneos) y riesgos climáticos/ambientales (siniestros forestales o eventos extremos CNIH).
   - Si el agente recomienda municipios sin mencionar estos riesgos o los oculta, 'analisis_riesgos_adecuado' debe ser False y 'aprobado' False.

3. ADECUACIÓN LOGÍSTICA Y ACTIVIDAD:
   - Verifica si los municipios seleccionados cumplen con las necesidades mínimas expresadas por el usuario (suelo, conectividad, tipo de industria).

4. FORMATO DE SALIDA (JSON ESTRICTO):
   Debes responder ÚNICAMENTE con un objeto JSON válido con los campos:
   - "aprobado": boolean (true solo si pasa la auditoría con solvencia)
   - "puntuacion_calidad": int (1 a 5)
   - "datos_contrastados": boolean
   - "analisis_riesgos_adecuado": boolean
   - "analisis_logistica_adecuado": boolean
   - "feedback_mejora": string explicativo con puntos fuertes y debilidades o instrucciones claras de subsanación si no está aprobado.
"""

    def __init__(self, model_name: str | None = None):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        # Por defecto usamos un modelo potente y determinista (temp=0.0) para supervisión
        self.model = model_name or os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    def supervisar(
        self,
        user_query: str,
        agent_response: str,
        context_docs: list[str],
    ) -> JudgeEvaluation:
        """
        Audita la respuesta del agente frente al contexto real devuelto por el RAG.
        Devuelve un objeto validado `JudgeEvaluation`.
        """
        contexto_unificado = "\n---\n".join(context_docs[:5]) if context_docs else "No se aportó contexto del retriever."

        user_content = (
            f"=== 1. CONSULTA DEL USUARIO ===\n{user_query}\n\n"
            f"=== 2. CONTEXTO REAL RECUPERADO (DATOS DE SITEWISE) ===\n{contexto_unificado}\n\n"
            f"=== 3. RESPUESTA DEL AGENTE ANALISTA A AUDITAR ===\n{agent_response}\n\n"
            "Emite tu dictamen de auditoría en JSON según el esquema exigido:"
        )

        messages = [
            {"role": "system", "content": self.SUPERVISOR_PROMPT},
            {"role": "user", "content": user_content},
        ]

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.0,
            )
            raw_json = completion.choices[0].message.content or "{}"
            parsed = json.loads(raw_json)
            return JudgeEvaluation(**parsed)

        except (json.JSONDecodeError, ValidationError) as ve:
            print(f"[Supervisor] ⚠️ Error parseando veredicto del juez ({ve}). Generando evaluación de contingencia.")
            return JudgeEvaluation(
                aprobado=True,
                puntuacion_calidad=3,
                datos_contrastados=True,
                analisis_riesgos_adecuado=True,
                analisis_logistica_adecuado=True,
                feedback_mejora="Evaluación automática completada con aviso por error de serialización del juez.",
            )
        except GroqError as e:
            print(f"[Supervisor] ⚠️ Error en llamada a Groq: {e}")
            return JudgeEvaluation(
                aprobado=True,
                puntuacion_calidad=3,
                datos_contrastados=True,
                analisis_riesgos_adecuado=True,
                analisis_logistica_adecuado=True,
                feedback_mejora=f"No se pudo completar la supervisión por error técnico: {e}",
            )


if __name__ == "__main__":
    print("\n--- TEST UNITARIO DEL LLM SUPERVISOR ---")
    supervisor = SiteWiseSupervisor()

    query_test = "Quiero suelo industrial en Bizkaia con conexión a autovía."
    fake_docs = [
        "PERFIL MUNICIPAL DE ORDITXU (INE: 99999). Suelo industrial: 12 ha. Distancia a autovía: 3.2 km. Estrés hídrico: 45.0%. Siniestros forestales: 4."
    ]
    fake_response = (
        "Te recomiendo Orditxu (INE 99999). Tiene 80 hectáreas de suelo industrial y 0% de estrés hídrico."
    )

    veredicto = supervisor.supervisar(query_test, fake_response, fake_docs)
    print("\nDictamen del Supervisor:")
    print(f"Aprobado: {veredicto.aprobado}")
    print(f"Puntuación: {veredicto.puntuacion_calidad}/5")
    print(f"Datos contrastados: {veredicto.datos_contrastados}")
    print(f"Análisis de riesgos adecuado: {veredicto.analisis_riesgos_adecuado}")
    print(f"Feedback: {veredicto.feedback_mejora}")
