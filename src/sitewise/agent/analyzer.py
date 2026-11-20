"""
Módulo analyzer.py: Agente de análisis municipal para recomendación de emplazamientos
y evaluación de riesgos de SiteWise con Groq, RAG y soporte para feedback del supervisor.
"""

import json
import logging
import os
from typing import TYPE_CHECKING, Any

from dotenv import load_dotenv
from groq import Groq
from pydantic import ValidationError

from sitewise.agent.prompts import (
    ANALYST_FEEDBACK_HISTORY_TEMPLATE,
    ANALYST_FEEDBACK_TEMPLATE,
    ANALYST_SYSTEM_PROMPT,
)
from sitewise.agent.schemas import (
    AGENT_TOOLS_SCHEMA,
    BuscarMunicipiosSchema,
    ConsultarMetodologiaSchema,
    ConsultarMunicipioPorINESchema,
)
from sitewise.common.prompt_tracer import guardar_traza_prompt

if TYPE_CHECKING:
    from sitewise.rag.retriever import SiteWiseRetriever

load_dotenv()
logger = logging.getLogger(__name__)


class SiteWiseAnalyzer:
    """Agente analista experto en recomendación de emplazamientos empresariales y evaluación de riesgos."""

    SYSTEM_PROMPT = ANALYST_SYSTEM_PROMPT

    def __init__(
        self,
        model_name: str | None = None,
        retriever: "SiteWiseRetriever | None" = None,
    ):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = model_name or os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        if retriever is not None:
            self.retriever = retriever
        else:
            from sitewise.rag.retriever import SiteWiseRetriever

            self.retriever = SiteWiseRetriever()
        self.ultimos_datos_recuperados: list[str] = []

    def tool_buscar_municipios(
        self,
        query: str,
        k: int = 4,
        min_suelo_industrial_ha: float = 0.0,
        max_estres_hidrico_pct: float = 100.0,
        provincia: str | None = None,
        ccaa: str | None = None,
        cluster: str | None = None,
    ) -> str:
        """Busca fichas municipales detalladas en SiteWise por semántica y filtros combinados."""
        k_seguro = min(max(1, k), 3)
        resultados = self.retriever.buscar(
            query=query,
            k=k_seguro,
            source_type="ficha_municipal",
            min_suelo_industrial_ha=min_suelo_industrial_ha if min_suelo_industrial_ha > 0 else None,
            max_estres_hidrico_pct=max_estres_hidrico_pct if max_estres_hidrico_pct < 100 else None,
            provincia=provincia if provincia else None,
            ccaa=ccaa if ccaa else None,
            cluster=cluster if cluster else None,
        )

        if not resultados:
            return "No se han encontrado municipios que cumplan con todos los criterios especificados."

        salida = []
        for i, res in enumerate(resultados, 1):
            meta = res["metadata"]
            bloque = (
                f"--- Resultado {i} ---\n"
                f"Municipio: {meta.get('nombre')} (INE: {meta.get('cod_ine')}, {meta.get('provincia')}, {meta.get('ccaa')})\n"
                f"Puntuación de similitud: {res['distance_score']}\n"
                f"{res['content']}\n"
            )
            salida.append(bloque)
            self.ultimos_datos_recuperados.append(res["content"])

        return "\n".join(salida)

    def _formatear_historial_feedback(
        self,
        feedback_history: list[str] | None = None,
        feedback_supervisor: str | None = None,
    ) -> str | None:
        if feedback_history:
            bloques = [
                f"--- Ronda {idx} ---\n{item.strip()}"
                for idx, item in enumerate(feedback_history, start=1)
                if item and item.strip()
            ]
            if bloques:
                return ANALYST_FEEDBACK_HISTORY_TEMPLATE.format(
                    historial_formateado="\n\n".join(bloques)
                )

        if feedback_supervisor and feedback_supervisor.strip():
            return ANALYST_FEEDBACK_TEMPLATE.format(feedback=feedback_supervisor.strip())

        return None

    def tool_consultar_municipio_ine(self, cod_ine: str) -> str:
        """Recupera la ficha completa y exacta de un municipio dado su código INE."""
        ficha = self.retriever.buscar_municipio_por_ine(cod_ine)
        if not ficha:
            return f"No se encontró ningún municipio con el código INE '{cod_ine}'."

        self.ultimos_datos_recuperados.append(ficha["content"])
        return f"--- Ficha Municipal Exacta (INE {cod_ine}) ---\n{ficha['content']}"

    def tool_consultar_metodologia(self, query: str) -> str:
        """Consulta la documentación técnica, fuentes y metodologías de SiteWise."""
        resultados = self.retriever.buscar_documentacion(query=query, k=2)
        if not resultados:
            return "No se ha encontrado documentación técnica relacionada."

        salida = []
        for res in resultados:
            bloque = f"Fuente: {res['metadata'].get('source')}\n{res['content']}\n"
            salida.append(bloque)
            self.ultimos_datos_recuperados.append(res["content"])

        return "\n---\n".join(salida)

    @property
    def available_tools(self):
        return {
            "buscar_municipios_sitewise": self.tool_buscar_municipios,
            "consultar_municipio_ine": self.tool_consultar_municipio_ine,
            "consultar_metodologia_sitewise": self.tool_consultar_metodologia,
        }

    @property
    def tools_schema(self):
        return AGENT_TOOLS_SCHEMA

    def ejecutar(
        self,
        user_prompt: str,
        feedback_supervisor: str | None = None,
        feedback_history: list[str] | None = None,
        max_turns: int = 5,
        max_ine_consults: int = 2,
    ) -> tuple[str, list[str]]:
        """
        Ejecuta la consulta del usuario.
        Devuelve una tupla (respuesta_texto, lista_de_datos_recuperados_crudos).
        """
        self.ultimos_datos_recuperados = []

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        bloque_feedback = self._formatear_historial_feedback(
            feedback_history=feedback_history,
            feedback_supervisor=feedback_supervisor,
        )
        if bloque_feedback:
            messages.append({
                "role": "user",
                "content": bloque_feedback,
            })

        turn = 0
        ine_consults = 0
        llm_call_idx = 0

        while turn < max_turns:
            llm_call_idx += 1

            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=self.tools_schema,
                    tool_choice="auto",
                    temperature=0.1,
                )
            except Exception as e:  # noqa: BLE001
                logger.error("Error de comunicación con el modelo de lenguaje: %s", e)
                guardar_traza_prompt(
                    componente="analyzer",
                    model=self.model,
                    messages=messages,
                    response={"error": str(e)},
                    extra={"turn": turn + 1, "call": llm_call_idx},
                )
                docs_unicos = list(dict.fromkeys(self.ultimos_datos_recuperados))
                return f"Error de comunicación con el modelo de lenguaje: {e}", docs_unicos

            response_message = response.choices[0].message
            guardar_traza_prompt(
                componente="analyzer",
                model=self.model,
                messages=messages,
                response=response_message,
                extra={"turn": turn + 1, "call": llm_call_idx},
            )
            messages.append(response_message)

            tool_calls = response_message.tool_calls or []
            if not tool_calls:
                docs_unicos = list(dict.fromkeys(self.ultimos_datos_recuperados))
                return response_message.content or "", docs_unicos

            solo_ine = all(
                tc.function.name == "consultar_municipio_ine" for tc in tool_calls
            )

            for tool_call in tool_calls:
                function_name = tool_call.function.name
                tool_output = ""

                try:
                    raw_args = json.loads(tool_call.function.arguments)

                    if function_name == "buscar_municipios_sitewise":
                        validated_args = BuscarMunicipiosSchema(**raw_args).model_dump()
                    elif function_name == "consultar_municipio_ine":
                        validated_args = ConsultarMunicipioPorINESchema(**raw_args).model_dump()
                    elif function_name == "consultar_metodologia_sitewise":
                        validated_args = ConsultarMetodologiaSchema(**raw_args).model_dump()
                    else:
                        validated_args = raw_args

                except (json.JSONDecodeError, ValidationError) as jde:
                    logger.warning("Argumentos inválidos para '%s': %s", function_name, jde)
                    tool_output = f"Error: Argumentos devueltos no válidos ({jde})."
                    validated_args = {}

                logger.info(
                    "Ejecutando herramienta '%s' con argumentos: %s",
                    function_name,
                    validated_args,
                )

                if function_name in self.available_tools and not tool_output.startswith("Error:"):
                    try:
                        tool_to_call = self.available_tools[function_name]
                        tool_output = tool_to_call(**validated_args)
                    except Exception as te:  # noqa: BLE001
                        logger.error("Error al ejecutar herramienta '%s': %s", function_name, te)
                        tool_output = f"Error al ejecutar {function_name}: {te}"
                elif not tool_output.startswith("Error:"):
                    logger.warning("Herramienta solicitada no disponible: '%s'", function_name)
                    tool_output = f"Error: Herramienta '{function_name}' no disponible."

                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": tool_output,
                })

            if solo_ine and ine_consults < max_ine_consults:
                ine_consults += 1
            else:
                turn += 1

        docs_unicos = list(dict.fromkeys(self.ultimos_datos_recuperados))

        if docs_unicos:
            logger.warning(
                "Se alcanzó el límite de %d turnos; forzando redacción final sin herramientas con datos recuperados.",
                max_turns,
            )
            messages.append({
                "role": "user",
                "content": (
                    "Se ha alcanzado el límite de pasos de búsqueda. Con los datos reales ya recuperados "
                    "en esta conversación, redacta ahora la respuesta final completa, estructurada y contrastada "
                    "sin solicitar más herramientas."
                ),
            })
            try:
                final_response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.1,
                )
                final_msg = final_response.choices[0].message
                guardar_traza_prompt(
                    componente="analyzer",
                    model=self.model,
                    messages=messages,
                    response=final_msg,
                    extra={"turn": "fallback_no_tools", "call": llm_call_idx + 1},
                )
                return final_msg.content or "", docs_unicos
            except Exception as fe:  # noqa: BLE001
                logger.error("Error en llamada de cierre sin herramientas: %s", fe)
                guardar_traza_prompt(
                    componente="analyzer",
                    model=self.model,
                    messages=messages,
                    response={"error": str(fe)},
                    extra={"turn": "fallback_no_tools", "call": llm_call_idx + 1},
                )
                return f"Error de comunicación con el modelo de lenguaje: {fe}", docs_unicos

        logger.warning("Se alcanzó el límite máximo de %d turnos sin completar la respuesta.", max_turns)
        return (
            "Se alcanzó el límite máximo de turnos sin completar la respuesta.",
            docs_unicos,
        )


SiteWiseAgentDirect = SiteWiseAnalyzer


if __name__ == "__main__":
    print("\n--- TEST AGENTE ANALIZADOR ---")
    agente = SiteWiseAnalyzer()
    pregunta = (
        "Quiero montar una planta de producción industrial en Bizkaia que requiere al menos 15 ha de suelo "
        "y buena conexión por autovía. Evalúa los riesgos hídricos y ambientales."
    )
    respuesta, docs = agente.ejecutar(pregunta)
    print("\n" + "=" * 80)
    print("RESPUESTA:\n", respuesta)
    print("=" * 80)
    print(f"Total fragmentos recuperados para supervisión: {len(docs)}")