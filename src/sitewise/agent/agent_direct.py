"""
Módulo agent_direct.py: Agente de análisis municipal nativo con la API de Groq
y el recuperador de SiteWise, utilizando esquemas de Pydantic externos.
"""

import json
import os

from dotenv import load_dotenv
from groq import Groq
from pydantic import ValidationError

from sitewise.agent.schemas import BuscarMunicipiosSchema, ConsultarMetodologiaSchema
from sitewise.rag.retriever import SiteWiseRetriever

# Cargamos variables de entorno (GROQ_API_KEY)
load_dotenv()


class SiteWiseAgentDirect:
    """Agente autónomo basado en la API nativa de Groq, ChromaDB y validación Pydantic."""

    def __init__(self, model_name: str | None = None):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = model_name or os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self.retriever = SiteWiseRetriever()

    # --- 1. Funciones reales de las herramientas ---
    def tool_buscar_municipios(
        self,
        query: str,
        k: int = 4,
        min_suelo_industrial_ha: float = 0.0,
        max_estres_hidrico_pct: float = 100.0,
        provincia: str | None = None,
    ) -> str:
        """Busca fichas municipales detalladas en SiteWise por semántica y filtros."""
        resultados = self.retriever.buscar(
            query=query,
            k=k,
            source_type="ficha_municipal",
            min_suelo_industrial_ha=min_suelo_industrial_ha if min_suelo_industrial_ha > 0 else None,
            max_estres_hidrico_pct=max_estres_hidrico_pct if max_estres_hidrico_pct < 100 else None,
            provincia=provincia if provincia else None,
        )

        if not resultados:
            return "No se han encontrado municipios que cumplan con los criterios especificados."

        salida = []
        for i, res in enumerate(resultados, 1):
            meta = res["metadata"]
            salida.append(
                f"--- Resultado {i} ---\n"
                f"Municipio: {meta.get('nombre')} ({meta.get('provincia')}, {meta.get('ccaa')})\n"
                f"Puntuación de similitud: {res['distance_score']}\n"
                f"{res['content']}\n"
            )
        return "\n".join(salida)

    def tool_consultar_metodologia(self, query: str) -> str:
        """Consulta la documentación técnica y manuales de fuentes de SiteWise."""
        resultados = self.retriever.buscar_documentacion(query=query, k=2)
        if not resultados:
            return "No se ha encontrado documentación relacionada."

        salida = []
        for res in resultados:
            salida.append(f"Fuente: {res['metadata'].get('source')}\n{res['content']}\n")
        return "\n---\n".join(salida)

    @property
    def available_tools(self):
        return {
            "buscar_municipios_sitewise": self.tool_buscar_municipios,
            "consultar_metodologia_sitewise": self.tool_consultar_metodologia,
        }

    # --- 2. Generación automática de esquemas JSON a partir de Pydantic ---
    @property
    def tools_schema(self):
        return [
            {
                "type": "function",
                "function": {
                    "name": "buscar_municipios_sitewise",
                    "description": "Busca fichas municipales reales en España utilizando semántica y filtros numéricos de suelo industrial o estrés hídrico.",
                    "parameters": BuscarMunicipiosSchema.model_json_schema(),
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

    # --- 3. Bucle de ejecución con control de errores y límite de turnos ---
    def ejecutar(self, user_prompt: str) -> str:
        messages = [
            {
                "role": "system",
                "content": (
                    "Eres SiteWise Agent, un experto en análisis municipal en España para la selección "
                    "de emplazamientos de negocio y evaluación de riesgos. Utiliza las herramientas disponibles "
                    "para consultar datos reales de la base de datos municipal. No inventes datos numéricos ni códigos INE."
                ),
            },
            {"role": "user", "content": user_prompt},
        ]

        max_turns = 5
        turn = 0

        while turn < max_turns:
            turn += 1
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=self.tools_schema,
                    tool_choice="auto",
                    temperature=0.0,
                )
            except Exception as e:  # noqa: BLE001
                return f"Error de comunicación con el modelo de lenguaje: {e}"

            response_message = response.choices[0].message
            messages.append(response_message)

            if not response_message.tool_calls:
                return response_message.content

            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                tool_output = ""

                try:
                    raw_args = json.loads(tool_call.function.arguments)

                    if function_name == "buscar_municipios_sitewise":
                        validated_args = BuscarMunicipiosSchema(**raw_args).model_dump()
                    elif function_name == "consultar_metodologia_sitewise":
                        validated_args = ConsultarMetodologiaSchema(**raw_args).model_dump()
                    else:
                        validated_args = raw_args

                except (json.JSONDecodeError, ValidationError) as jde:
                    tool_output = f"Error: Los argumentos devueltos por el modelo no son válidos ({jde})."
                    validated_args = {}

                print(f"\n[Agente] 🛠️ Ejecutando herramienta nativa: '{function_name}' con argumentos: {validated_args}")

                if function_name in self.available_tools and not tool_output.startswith("Error:"):
                    try:
                        tool_to_call = self.available_tools[function_name]
                        tool_output = tool_to_call(**validated_args)
                    except Exception as te:  # noqa: BLE001
                        tool_output = f"Error al ejecutar la herramienta {function_name}: {te}"
                elif not tool_output.startswith("Error:"):
                    tool_output = f"Error: Herramienta {function_name} no encontrada."

                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": tool_output,
                })

        return "Lo siento, he alcanzado el límite máximo de iteraciones permitidas sin completar la consulta."


if __name__ == "__main__":
    print("\n--- INICIALIZANDO AGENTE NATIVO CON GROQ Y PYDANTIC ---")
    try:
        agente = SiteWiseAgentDirect()

        pregunta = (
            "Busca un municipio en la provincia de Bizkaia que tenga al menos 10 hectáreas "
            "de suelo industrial y un estrés hídrico bajo, y dime cuáles son sus principales fortalezas."
        )

        print(f"\nPregunta: {pregunta}\n")
        respuesta_final = agente.ejecutar(pregunta)

        print("\n" + "=" * 80)
        print("RESPUESTA FINAL DEL AGENTE NATIVO:")
        print("=" * 80)
        print(respuesta_final)

    except Exception as e:  # noqa: BLE001
        print(f"\n[Error] Comprueba tu configuración en el archivo .env: {e}")