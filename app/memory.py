"""
memory.py
Memória conversacional por sessão (Requisito 3.2).

Usamos o MemorySaver do LangGraph, que é o mecanismo NATIVO de
checkpointing/memória do framework: cada `thread_id` (= session_id)
mantém seu próprio histórico de mensagens, persistido automaticamente
pelo grafo a cada turno, sem que precisemos reimplementar buffer de
histórico manualmente (como era feito "na mão" nas Sprints 1 e 2).

Isso é o "ganho arquitetural" citado no enunciado: antes, o histórico
era gerenciado manualmente pelo código da aplicação; agora, é o próprio
framework de agentes que injeta o histórico correto a cada chamada,
por thread/sessão.
"""

from langgraph.checkpoint.memory import MemorySaver

# Um único checkpointer em memória, compartilhado por todas as sessões
# do processo. Cada sessão é isolada pelo seu `thread_id`.
# Para persistência em disco entre execuções, troque por
# langgraph.checkpoint.sqlite.SqliteSaver (ver comentário abaixo).
checkpointer = MemorySaver()

# --- Persistência em disco (opcional, recomendado para produção) ---
# from langgraph.checkpoint.sqlite import SqliteSaver
# import sqlite3
# conn = sqlite3.connect("goodwe_sessions.db", check_same_thread=False)
# checkpointer = SqliteSaver(conn)


def make_thread_config(session_id: str) -> dict:
    """Monta o dicionário de config que o LangGraph usa para saber
    a qual sessão/thread uma chamada pertence."""
    return {"configurable": {"thread_id": session_id}}
