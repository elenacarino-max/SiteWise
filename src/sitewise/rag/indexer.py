"""
Módulo indexer.py: Chunking selectivo e indexación vectorial para SiteWise.
"""

import logging
import os
import shutil
from typing import Any

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


class SiteWiseIndexer:
    """Indexador vectorial que respeta fichas municipales completas y trocea documentación."""

    def __init__(self, persist_directory: str = "data/interim/vector_db"):
        self.persist_directory = persist_directory
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        self.doc_splitter = RecursiveCharacterTextSplitter(
            chunk_size=600,
            chunk_overlap=80,
            separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " "],
        )

    def _preparar_chunks(self, raw_documents: list[dict[str, Any]]) -> tuple[list[str], list[dict[str, Any]]]:
        texts: list[str] = []
        metadatas: list[dict[str, Any]] = []

        for doc in raw_documents:
            source_type = doc.get("metadata", {}).get("source_type", "documentacion")

            if source_type == "ficha_municipal":
                texts.append(doc["content"])
                metadatas.append(doc["metadata"])
            else:
                chunks = self.doc_splitter.split_text(doc["content"])
                for idx, chunk in enumerate(chunks):
                    chunk_meta = {**doc["metadata"], "chunk_index": idx}
                    texts.append(chunk)
                    metadatas.append(chunk_meta)

        return texts, metadatas

    def create_and_save_index(self, raw_documents: list[dict[str, Any]], batch_size: int = 1000):
        """
        Genera los embeddings en lotes y persiste la base vectorial en disco,
        limpiando el índice previo para evitar duplicidades.
        """
        if os.path.exists(self.persist_directory):
            logger.info("Limpiando índice anterior en '%s' para evitar duplicados...", self.persist_directory)
            shutil.rmtree(self.persist_directory)

        texts, metadatas = self._preparar_chunks(raw_documents)

        if not texts:
            logger.warning("No hay fragmentos para indexar.")
            return None

        logger.info("Iniciando indexación de %d fragmentos en lotes de %d...", len(texts), batch_size)

        vector_store = None
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

            logger.info("Indexados %d / %d fragmentos...", min(i + batch_size, len(texts)), len(texts))

        logger.info("Índice vectorial guardado en %s", self.persist_directory)
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