"""
rag.py
Recuperação de contexto (RAG) sobre a base de conhecimento do operador
comercial do ChargeGrid Intelligence — mesma ideia da Sprint 1-2
(chatbot_goodwe.py: PyPDFLoader/UnstructuredWordDocumentLoader +
InMemoryVectorStore + OpenAIEmbeddings), mas com dois ajustes:

1. Suporta também .txt/.md via TextLoader (dependência leve, mais fácil
   de rodar no Google Colab do que a biblioteca `unstructured`, que exige
   pacotes de sistema extras). .pdf e .docx continuam suportados se as
   dependências estiverem instaladas.
2. Fica isolado num módulo próprio (em vez de código solto no topo do
   arquivo principal), para poder ser chamado como um NÓ do grafo do
   LangGraph (retrieve_node em agent.py), e não apenas como script.

A pasta de documentos agora se chama `knowledge_base/` (era `docs/` na
Sprint 1-2) para não colidir com a pasta `docs/` deste projeto, usada
para gerar o relatório de evolução em PDF.
"""

import os
from pathlib import Path

from langchain_openai import OpenAIEmbeddings
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import require_api_key

KNOWLEDGE_BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "knowledge_base")


def _load_documents(folder: str = KNOWLEDGE_BASE_DIR) -> list[Document]:
    docs: list[Document] = []
    for file_path in sorted(Path(folder).glob("*")):
        suffix = file_path.suffix.lower()
        try:
            if suffix in {".txt", ".md"}:
                from langchain_community.document_loaders import TextLoader
                docs.extend(TextLoader(str(file_path), encoding="utf-8").load())
            elif suffix == ".pdf":
                from langchain_community.document_loaders import PyPDFLoader
                docs.extend(PyPDFLoader(str(file_path)).load())
            elif suffix in {".docx", ".doc"}:
                from langchain_community.document_loaders import UnstructuredWordDocumentLoader
                docs.extend(UnstructuredWordDocumentLoader(str(file_path)).load())
        except ImportError as e:
            print(f"[rag] Aviso: dependência ausente para ler {file_path.name} ({e}). Pulando.")
    return docs


class KnowledgeBase:
    """Encapsula o índice vetorial em memória, construído uma única vez."""

    def __init__(self, folder: str = KNOWLEDGE_BASE_DIR):
        self.folder = folder
        self._vector_store = None

    def _ensure_built(self):
        if self._vector_store is not None:
            return
        docs = _load_documents(self.folder)
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200, add_start_index=True)
        splits = splitter.split_documents(docs) if docs else []

        require_api_key("openai")  # embeddings do RAG sempre usam OpenAI
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        store = InMemoryVectorStore(embeddings)
        if splits:
            store.add_documents(splits)
        self._vector_store = store

    def retrieve(self, query: str, k: int = 2) -> list[Document]:
        self._ensure_built()
        if not query.strip():
            return []
        return self._vector_store.similarity_search(query, k=k)


# Instância única, reaproveitada entre chamadas (evita reindexar a cada turno)
knowledge_base = KnowledgeBase()
