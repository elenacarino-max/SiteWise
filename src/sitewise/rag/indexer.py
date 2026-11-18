"""
Módulo indexer.py: Chunking selectivo e indexación vectorial para SiteWise.
"""

import os
from typing import Any, Dict, List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings


class SiteWiseIndexer:
    """Indexador vectorial que respeta fichas municipales completas y trocea documentación."""

    def __init__(self, persist_directory: str = "data/interim/vector_db"):
        self.persist_directory = persist_directory
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        # Splitter exclusivo para documentación larga (Markdown, guías, metodología)
        self.doc_splitter = RecursiveCharacterTextSplitter(
            chunk_size=600,
            chunk_overlap=80,
            separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " "],
        )

    def _preparar_chunks(self, raw_documents: List[Dict[str, Any]]) -> tuple[List[str], List[Dict[str, Any]]]:
        """
        Aplica chunking inteligente según el tipo de fuente:
        - Ficha municipal (CSV): se mantiene íntegra como unidad semántica (1 municipio = 1 chunk).
        - Documentación (MD): se divide en fragmentos con solapamiento.
        """
        texts: List[str] = []
        metadatas: List[Dict[str, Any]] = []

        for doc in raw_documents:
            source_type = doc.get("metadata", {}).get("source_type", "documentacion")

            if source_type == "ficha_municipal":
                # No troceamos el municipio para no perder la relación entre el nombre y sus indicadores
                texts.append(doc["content"])
                metadatas.append(doc["metadata"])
            else:
                # Troceamos documentación extensa (metodología, fuentes, gobernanza)
                chunks = self.doc_splitter.split_text(doc["content"])
                for idx, chunk in enumerate(chunks):
                    chunk_meta = {**doc["metadata"], "chunk_index": idx}
                    texts.append(chunk)
                    metadatas.append(chunk_meta)

        return texts, metadatas

    def create_and_save_index(self, raw_documents: List[Dict[str, Any]], batch_size: int = 1000):
        """
        Genera los embeddings en lotes (batches) y persiste la base vectorial en disco.
        """
        texts, metadatas = self._preparar_chunks(raw_documents)

        if not texts:
            print("[Aviso] No hay fragmentos para indexar.")
            return None

        print(f"[Info] Iniciando indexación de {len(texts)} fragmentos en lotes de {batch_size}...")

        vector_store = None
        # Insertamos en lotes para mostrar progreso con los 8.000 municipios y evitar saturar RAM
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]
            batch_metas = metadatas[i : i + batch_size]

            if vector_store is None:
                vector_store = Chroma.from_texts(
                    texts=batch_texts,
                    embedding=self.embeddings,
                    metadatas=batch_metas,
                    persist_directory=self.persist_directory,
                )
            else:
                vector_store.add_texts(texts=batch_texts, metadatas=batch_metas)

            print(f"  -> Indexados {min(i + batch_size, len(texts))} / {len(texts)} fragmentos...")

        print(f"[Éxito] Índice vectorial guardado en {self.persist_directory}")
        return vector_store

    def load_existing_index(self):
        """Carga el índice vectorial ya guardado en disco."""
        if os.path.exists(self.persist_directory):
            return Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings,
            )
        return None


if __name__ == "__main__":
    from sitewise.rag.loader import SiteWiseLoader

    loader = SiteWiseLoader()
    docs = loader.load_all()

    indexer = SiteWiseIndexer()
    indexer.create_and_save_index(docs)