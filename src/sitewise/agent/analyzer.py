"""
Módulo analyzer.py: Agente de análisis municipal para recomendación de emplazamientos
y evaluación de riesgos de SiteWise con Groq, RAG y soporte para feedback del supervisor.
"""

import json
import os
from typing import TYPE_CHECKING, Any

from dotenv import load_dotenv
from groq import Groq
from pydantic import ValidationError

from sitewise.agent.schemas import (
    AGENT_TOOLS_SCHEMA,
    BuscarMunicipiosSchema,
    ConsultarMetodologiaSchema,
    ConsultarMunicipioPorINESchema,
)

if TYPE_CHECKING:
    from sitewise.rag.retriever import SiteWiseRetriever

# Cargamos variables de entorno (GROQ_API_KEY)
load_dotenv()


class SiteWiseAnalyzer:
    """Agente analista experto en recomendación de emplazamientos empresariales y evaluación de riesgos."""

    SYSTEM_PROMPT = """Eres SiteWise Agent, un consultor senior experto en localización territorial y evaluación de emplazamientos para nuevas empresas, fábricas y proyectos industriales en España.

Tu misión es analizar y recomendar los mejores municipios según las necesidades del usuario, basándote rigurosamente en datos reales del sistema SiteWise.

PAUTAS OBLIGATORIAS:
1. ANÁLISIS DE REQUISITOS:
   - Identifica qué tipo de actividad económica quiere desarrollar el usuario (ej. logística, fábrica química, agroalimentaria, datacenter, manufactura ligera).
   - Ten en cuenta sus requerimientos críticos: necesidades de suelo industrial (ha), distancia a autovía y terminales de mercancías (TTM/intermodal), demanda de agua y disponibilidad de mano de obra en el sector correspondiente.

2. EVALUACIÓN Y CONTRASTE DE RIESGOS:
   - Siempre debes evaluar los riesgos ambientales: estrés y agotamiento hídrico, estado de masas subterráneas (cuantitativo y químico).
   - Revisa el histórico de riesgos: siniestros forestales y eventos extremos CNIH (inundaciones, temporales). No ocultes los riesgos; si un municipio tiene buen suelo pero alto estrés hídrico o riesgo de inundación, indícalo claramente con medidas mitigadoras.

3. USO DE HERRAMIENTAS Y RIGOR:
   - Utiliza 'buscar_municipios_sitewise' para encontrar candidatos acordes y 'consultar_municipio_ine' para profundizar en una ficha concreta si es necesario.
   - Cita datos numéricos exactos (ha de suelo, km a autovía, % estrés hídrico, paro sectorial) obtenidos de las fichas. JAMÁS inventes datos ni códigos INE.
   - Si se te proporciona una corrección o feedback de un supervisor, subsana inmediatamente las deficiencias señaladas.
"""

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
        # Registro de textos crudos recuperados por las herramientas para auditoría del LLM Judge
        self.ultimos_datos_recuperados: list[str] = []

    # --- 1. Funciones reales de las herramientas ---
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
        k_seguro = min(max(1, k), 6)
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

    # --- 2. Especificación de herramientas para el modelo (desde schemas.py) ---
    @property
    def tools_schema(self):
        return AGENT_TOOLS_SCHEMA

    # --- 3. Bucle de ejecución con soporte para feedback y control de turnos ---
    def ejecutar(
        self,
        user_prompt: str,
        feedback_supervisor: str | None = None,
        max_turns: int = 5,
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

        if feedback_supervisor:
            messages.append({
                "role": "system",
                "content": (
                    f"ATENCIÓN - FEEDBACK DEL SUPERVISOR:\n{feedback_supervisor}\n"
                    "Debes corregir tu análisis anterior asegurándote de subsanar los puntos señalados."
                ),
            })

        turn = 0
        while turn < max_turns:
            turn += 1
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=self.tools_schema,
                    tool_choice="auto",
                    temperature=0.1,
                )
            except Exception as e:  # noqa: BLE001
                return f"Error de comunicación con el modelo de lenguaje: {e}", self.ultimos_datos_recuperados

            response_message = response.choices[0].message

            # Añadir mensaje del asistente a la conversación
            messages.append(response_message)

            if not response_message.tool_calls:
                return response_message.content or "", self.ultimos_datos_recuperados

            # Atender todas las llamadas a herramientas requeridas
            for tool_call in response_message.tool_calls:
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
                    tool_output = f"Error: Argumentos devueltos no válidos ({jde})."
                    validated_args = {}

                print(f"[Agente] 🛠️ Ejecutando herramienta: '{function_name}' con {validated_args}")

                if function_name in self.available_tools and not tool_output.startswith("Error:"):
                    try:
                        tool_to_call = self.available_tools[function_name]
                        tool_output = tool_to_call(**validated_args)
                    except Exception as te:  # noqa: BLE001
                        tool_output = f"Error al ejecutar {function_name}: {te}"
                elif not tool_output.startswith("Error:"):
                    tool_output = f"Error: Herramienta '{function_name}' no disponible."

                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": tool_output,
                })

        return (
            "Se alcanzó el límite máximo de turnos sin completar la respuesta.",
            self.ultimos_datos_recuperados,
        )


# Alias para compatibilidad hacia atrás
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