"""
Punto de entrada CLI para ejecutar el flujo completo de SiteWise (RAG + Agente + Supervisor).
"""

import argparse
import sys

from sitewise.agent.agent_graph import SiteWiseGraphOrchestrator
from sitewise.agent.analyzer import SiteWiseAnalyzer
from sitewise.agent.supervisor import SiteWiseSupervisor
from sitewise.common.logging_config import setup_logging
from sitewise.rag.retriever import SiteWiseRetriever


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ejecuta SiteWise Agent supervisado por LLM Judge."
    )
    parser.add_argument(
        "-q",
        "--query",
        type=str,
        default=None,
        help="Consulta sobre emplazamiento industrial, suelo, logística o riesgos.",
    )
    parser.add_argument(
        "--max-revisions",
        type=int,
        default=2,
        help="Número máximo de rondas de corrección del supervisor (por defecto: 2).",
    )
    parser.add_argument(
        "--persist-dir",
        type=str,
        default="data/interim/vector_db",
        help="Ruta al índice vectorial de Chroma (por defecto: data/interim/vector_db).",
    )
    return parser.parse_args()


def main() -> int:
    setup_logging()
    args = parse_args()

    query = args.query
    if not query:
        try:
            query = input("\nEscribe tu consulta para SiteWise Agent: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nEjecución cancelada.")
            return 0

    if not query:
        print("No se introdujo ninguna consulta.")
        return 1

    try:
        retriever = SiteWiseRetriever(persist_directory=args.persist_dir)
    except RuntimeError as exc:
        print(f"\n⚠️ Aviso con el índice vectorial: {exc}")
        print("Continuando sin retriever pre-cargado...")
        retriever = None

    analyst = SiteWiseAnalyzer(retriever=retriever)
    supervisor = SiteWiseSupervisor()
    orchestrator = SiteWiseGraphOrchestrator(
        analyst_agent=analyst,
        supervisor=supervisor,
        max_revisions=args.max_revisions,
    )

    resultado = orchestrator.run(query)

    print("\n" + "=" * 80)
    print("RESULTADO FINAL:")
    print("=" * 80)
    print(resultado.get("final_output", ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())