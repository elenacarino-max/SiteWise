"""
Módulo retriever.py: Recuperación semántica e híbrida (con filtros de metadatos)
sobre el índice vectorial Chroma de SiteWise.
"""

from typing import Any

from sitewise.rag.indexer import SiteWiseIndexer


class SiteWiseRetriever:
    """Recuperador de fichas municipales y documentación técnica para el agente."""

    def __init__(self, persist_directory: str = "data/interim/vector_db"):
        self.indexer = SiteWiseIndexer(persist_directory=persist_directory)
        self.vector_store = self.indexer.load_existing_index()
        if self.vector_store is None:
            raise RuntimeError(
                f"No se encontró ningún índice vectorial en '{persist_directory}'. "
                "Ejecuta primero el proceso de indexación (indexer.py)."
            )

    @staticmethod
    def _construir_filtro_chroma(
        source_type: str | None = None,
        provincia: str | None = None,
        ccaa: str | None = None,
        cod_ine: str | None = None,
        cluster: str | None = None,
        min_suelo_industrial_ha: float | None = None,
        max_estres_hidrico_pct: float | None = None,
    ) -> dict[str, Any] | None:
        """Construye la cláusula `where` compatible con ChromaDB a partir de filtros opcionales."""
        condiciones: list[dict[str, Any]] = []

        if source_type:
            condiciones.append({"source_type": source_type})
        if provincia:
            condiciones.append({"provincia": provincia})
        if ccaa:
            condiciones.append({"ccaa": ccaa})
        if cod_ine:
            condiciones.append({"cod_ine": str(cod_ine)})
        if cluster:
            condiciones.append({"cluster": str(cluster)})
        if min_suelo_industrial_ha is not None:
            condiciones.append({"suelo_industrial_ha": {"$gte": float(min_suelo_industrial_ha)}})
        if max_estres_hidrico_pct is not None:
            condiciones.append({"estres_hidrico_pct": {"$gte": 0.0}})
            condiciones.append({"estres_hidrico_pct": {"$lte": float(max_estres_hidrico_pct)}})

        if not condiciones:
            return None
        if len(condiciones) == 1:
            return condiciones[0]
        return {"$and": condiciones}

    def buscar(
        self,
        query: str,
        k: int = 5,
        source_type: str | None = None,
        provincia: str | None = None,
        ccaa: str | None = None,
        cod_ine: str | None = None,
        cluster: str | None = None,
        min_suelo_industrial_ha: float | None = None,
        max_estres_hidrico_pct: float | None = None,
    ) -> list[dict[str, Any]]:
        """Realiza búsqueda semántica con filtros opcionales de metadatos."""
        filtro = self._construir_filtro_chroma(
            source_type=source_type,
            provincia=provincia,
            ccaa=ccaa,
            cod_ine=cod_ine,
            cluster=cluster,
            min_suelo_industrial_ha=min_suelo_industrial_ha,
            max_estres_hidrico_pct=max_estres_hidrico_pct,
        )

        resultados = self.vector_store.similarity_search_with_score(
            query=query,
            k=k,
            filter=filtro,
        )

        salida: list[dict[str, Any]] = []
        for doc, score in resultados:
            salida.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "distance_score": round(float(score), 4),
            })

        return salida

    def buscar_municipio_por_ine(self, cod_ine: str) -> dict[str, Any] | None:
        """Recupera directamente la ficha exacta de un municipio por su código INE de forma determinista y rápida."""
        res = self.vector_store.get(where={"cod_ine": str(cod_ine)})
        if res and res.get("documents") and len(res["documents"]) > 0:
            return {
                "content": res["documents"][0],
                "metadata": res["metadatas"][0] if res.get("metadatas") else {},
                "distance_score": 0.0,
            }
        return None

    def buscar_municipios_por_ines(self, codigos_ine: list[str]) -> list[dict[str, Any]]:
        """Recupera fichas de varios municipios simultáneamente a partir de una lista de códigos INE."""
        salida: list[dict[str, Any]] = []
        for cod in codigos_ine:
            ficha = self.buscar_municipio_por_ine(cod)
            if ficha:
                salida.append(ficha)
        return salida

    def buscar_documentacion(self, query: str, k: int = 4) -> list[dict[str, Any]]:
        """Consulta exclusivamente la documentación metodológica (docs/)."""
        return self.buscar(query=query, k=k, source_type="documentacion")

if __name__ == "__main__":
    # Prueba rápida de consulta mostrando la información completa
    retriever = SiteWiseRetriever()

    query="Municipio con buena conectividad fibra, acceso a autovía y suelo industrial"

    print("\n" + "="*80)
    print("--- PRUEBA 1: Búsqueda semántica con filtros (Fichas Completas) ---")
    print(f"--- QUERY: {query} ---")
        
    print("="*80)
    hits = retriever.buscar(
        query=query,
        k=2,  # Mostramos 2 resultados para que la lectura sea cómoda y detallada
        source_type="ficha_municipal",
        min_suelo_industrial_ha=20.0,
        max_estres_hidrico_pct=30.0,
    )
    for i, hit in enumerate(hits, 1):
        print(f"\n[{i}] Municipio: {hit['metadata'].get('nombre')} ({hit['metadata'].get('provincia')})")
        print(f"    CCAA: {hit['metadata'].get('ccaa')} | Distancia de similitud: {hit['distance_score']}")
        print("-" * 80)
        print(hit["content"])  
        print("=" * 80)

    print("\n" + "="*80)
    print("--- PRUEBA 2: Consulta sobre metodología (Documentación Completa) ---")
    print("="*80)
    doc_hits = retriever.buscar_documentacion("Cómo se calculan riesgo y atractivo", k=1)
    for hit in doc_hits:
        print(f"\nFuente: {hit['metadata'].get('source')}")
        print("-" * 80)
        print(hit["content"])  # Imprime todo el fragmento de la documentación
        print("=" * 80)