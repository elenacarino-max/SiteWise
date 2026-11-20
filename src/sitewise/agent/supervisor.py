"""
Módulo supervisor.py: LLM Judge / Auditor de calidad y veracidad para SiteWise.
Evalúa de forma independiente las respuestas del Agente Analista contrastándolas
con los datos reales recuperados del RAG.
"""

import json
import logging
import os

from dotenv import load_dotenv
from groq import Groq
from pydantic import ValidationError

from sitewise.agent.prompts import (
    SUPERVISOR_AUDIT_TEMPLATE,
    SUPERVISOR_SYSTEM_PROMPT,
)
from sitewise.agent.schemas import JudgeEvaluation
from sitewise.common.prompt_tracer import guardar_traza_prompt

load_dotenv()
logger = logging.getLogger(__name__)


class SiteWiseSupervisor:
    """LLM Judge / Agente Supervisor que audita fidelidad factual, riesgos y adecuación logística."""

    SUPERVISOR_PROMPT = SUPERVISOR_SYSTEM_PROMPT

    def __init__(self, model_name: str | None = None):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = (
            model_name
            or os.getenv("GROQ_SUPERVISOR_MODEL")
            or os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        )

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
        docs_unicos = list(dict.fromkeys(doc for doc in context_docs if doc and doc.strip()))
        contexto_unificado = (
            "\n---\n".join(docs_unicos)
            if docs_unicos
            else "No se aportó contexto del retriever."
        )

        user_content = SUPERVISOR_AUDIT_TEMPLATE.format(
            user_query=user_query,
            contexto_unificado=contexto_unificado,
            agent_response=agent_response,
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
            veredicto = JudgeEvaluation(**parsed)
            guardar_traza_prompt(
                componente="supervisor",
                model=self.model,
                messages=messages,
                response={
                    "raw_json": raw_json,
                    "parsed_evaluation": veredicto.model_dump(),
                },
                extra={"user_query": user_query},
            )
            return veredicto

        except (json.JSONDecodeError, ValidationError) as ve:
            logger.warning("Error parseando veredicto del juez (%s). Dictamen: NO VERIFICADO.", ve)
            guardar_traza_prompt(
                componente="supervisor",
                model=self.model,
                messages=messages,
                response={"error": str(ve)},
                extra={"user_query": user_query},
            )
            return JudgeEvaluation(
                aprobado=False,
                puntuacion_calidad=1,
                datos_contrastados=False,
                analisis_riesgos_adecuado=False,
                analisis_logistica_adecuado=False,
                feedback_mejora=f"No verificado: Error al validar o decodificar el veredicto del juez ({ve}). La recomendación debe ser auditada nuevamente.",
            )
        except Exception as e:  # noqa: BLE001
            logger.error("Error en llamada a Groq desde el supervisor: %s", e)
            guardar_traza_prompt(
                componente="supervisor",
                model=self.model,
                messages=messages,
                response={"error": str(e)},
                extra={"user_query": user_query},
            )
            return JudgeEvaluation(
                aprobado=False,
                puntuacion_calidad=1,
                datos_contrastados=False,
                analisis_riesgos_adecuado=False,
                analisis_logistica_adecuado=False,
                feedback_mejora=f"No verificado: Fallo técnico en la comunicación con el modelo juez ({e}). No se puede dar por aprobada la recomendación.",
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