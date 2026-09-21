"""
agent.py
Núcleo conversacional do GoodWe EV Challenge - Sprint 03.

FRAMEWORK ESCOLHIDO: LangGraph (mesmo framework das Sprints 1-2).

A Sprint 1-2 já usava LangGraph, mas de forma mínima: um único
`add_sequence([retrieve, generate])`, sem nós de decisão, sem guardrails e
com o histórico de conversa guardado numa lista Python comum
(`chat_history`), repassada manualmente a cada chamada — ou seja, o
framework participava pouco da orquestração de fato.

O que a Sprint 03 evolui, mantendo o mesmo framework:
- O fluxo agora tem um nó de DECISÃO explícito (guardrail de entrada),
  que pode encerrar o grafo antes mesmo de chamar o LLM — algo que o
  `add_sequence` linear da Sprint 1-2 não permitia.
- A memória por sessão passa a ser gerenciada pelo mecanismo NATIVO do
  LangGraph (checkpointer / `thread_id`), em vez de uma lista Python
  mantida à mão — o que garante isolamento correto entre sessões
  diferentes (testado em `test_memory_isolada_por_sessao`).
- Continua agnóstico de provedor de LLM, o que facilita o Requisito 5
  (comparação entre modelos): trocar de modelo é trocar uma linha de
  configuração.

Optamos por NÃO trocar de framework (ex. para CrewAI ou OpenAI Agents
SDK) porque o ganho pedido pela Sprint 03 — controle de fluxo, memória
gerenciada, guardrails — já é alcançável aprofundando o uso do LangGraph
que o grupo já tinha, sem o custo de reaprender um framework novo do
zero nem reescrever o RAG já validado nas sprints anteriores.

Trade-off identificado: por ainda ser um grafo relativamente simples
(4 nós), parte da estrutura do LangGraph segue sendo "over-engineering"
para o tamanho atual do projeto — o ganho tende a aparecer mais se o
agente crescer (mais ferramentas, mais nós de decisão).
"""

from typing import TypedDict, Annotated, Literal
from operator import add

from langgraph.graph import StateGraph, END
from langchain_core.messages import (
    BaseMessage,
    SystemMessage,
    HumanMessage,
    AIMessage,
)

from app.config import SYSTEM_PROMPT, MODEL_CONFIGS, DEFAULT_MODEL_KEY, require_api_key
from app.memory import checkpointer, make_thread_config
from app.guardrails import apply_input_guardrail, apply_output_guardrail
from app.rag import knowledge_base


# ---------------------------------------------------------------------
# 1. Estado do grafo
# ---------------------------------------------------------------------
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add]
    blocked: bool  # True se a validação ou o guardrail já barrou a mensagem
    context: str   # trechos recuperados da base de conhecimento (RAG)


# ---------------------------------------------------------------------
# 2. Fábrica de chat model por provedor (permite trocar de modelo
#    facilmente para o Requisito 5 - comparação entre modelos)
# ---------------------------------------------------------------------
def build_chat_model(model_key: str = DEFAULT_MODEL_KEY):
    cfg = MODEL_CONFIGS[model_key]
    provider = cfg["provider"]
    require_api_key(provider)  # falha cedo, com mensagem clara, se faltar a chave

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=cfg["model"],
            temperature=cfg["temperature"],
            max_tokens=cfg["max_tokens"],
        )
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=cfg["model"],
            temperature=cfg["temperature"],
            max_tokens=cfg["max_tokens"],
        )
    elif provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=cfg["model"],
            temperature=cfg["temperature"],
            max_output_tokens=cfg["max_tokens"],
        )
    else:
        raise ValueError(f"Provider não suportado: {provider}")


# ---------------------------------------------------------------------
# 3. Nós do grafo
# ---------------------------------------------------------------------
EMPTY_INPUT_MESSAGE = (
    "Não recebi nenhuma pergunta. Pode me dizer o que você gostaria de saber "
    "sobre potência, faturamento, ciclos de carregamento ou comunicação com "
    "usuários do ChargeGrid?"
)

API_FAILURE_MESSAGE = (
    "Estou com uma instabilidade temporária para gerar a resposta agora. "
    "Tente novamente em instantes; se o problema persistir, procure o "
    "suporte técnico do ChargeGrid."
)


def validate_input_node(state: AgentState) -> AgentState:
    """Bloco ENTRADA/VALIDAÇÃO do fluxo: rejeita mensagens vazias ou só
    com espaços antes de gastar uma chamada de LLM ou de RAG com elas."""
    last_user_msg = state["messages"][-1]
    if not last_user_msg.content or not last_user_msg.content.strip():
        return {"messages": [AIMessage(content=EMPTY_INPUT_MESSAGE)], "blocked": True}
    return {"messages": [], "blocked": False}


def input_guardrail_node(state: AgentState) -> AgentState:
    if state.get("blocked"):
        return {"messages": []}
    last_user_msg = state["messages"][-1]
    blocked, refusal = apply_input_guardrail(last_user_msg.content)
    if blocked:
        return {"messages": [AIMessage(content=refusal)], "blocked": True}
    return {"messages": [], "blocked": False}


def retrieve_node(state: AgentState) -> AgentState:
    """Busca contexto na base de conhecimento (RAG), igual à Sprint 1-2,
    usando a última mensagem do usuário como consulta. Pulado se o
    guardrail de entrada já bloqueou a mensagem."""
    if state.get("blocked"):
        return {"context": ""}

    last_user_msg = state["messages"][-1]
    docs = knowledge_base.retrieve(last_user_msg.content, k=2)
    context_text = "\n\n".join(doc.page_content for doc in docs)
    return {"context": context_text}


def make_llm_node(model_key: str = DEFAULT_MODEL_KEY):
    llm = build_chat_model(model_key)

    def llm_node(state: AgentState) -> AgentState:
        if state.get("blocked"):
            # Guardrail de entrada já respondeu; não chama o LLM.
            return {"messages": []}

        history = state["messages"]
        context = state.get("context", "")

        # Injeta o contexto recuperado (RAG) como uma mensagem de sistema
        # adicional, logo antes da última mensagem do usuário, seguindo o
        # mesmo padrão de "Contexto recuperado: ..." da Sprint 1-2.
        context_note = SystemMessage(
            content=(
                f"Contexto recuperado da base de conhecimento:\n{context}"
                if context
                else "Nenhum contexto relevante foi recuperado da base de conhecimento."
            )
        )
        full_messages = [SystemMessage(content=SYSTEM_PROMPT)] + history + [context_note]

        # Bloco FALHAS: se a API do provedor falhar (erro de rede, rate
        # limit, timeout, chave inválida, etc.), o agente não deve
        # simplesmente propagar a exceção e "morrer" — devolve uma
        # mensagem de fallback ao usuário.
        try:
            response = llm.invoke(full_messages)
            content = response.content
        except Exception as e:
            print(f"[llm_node] Falha ao chamar o modelo ({model_key}): {e}")
            return {"messages": [AIMessage(content=API_FAILURE_MESSAGE)]}

        safe_content = apply_output_guardrail(content)
        return {"messages": [AIMessage(content=safe_content)]}

    return llm_node


def route_after_validation(state: AgentState) -> Literal["input_guardrail", "end"]:
    return "end" if state.get("blocked") else "input_guardrail"


def route_after_guardrail(state: AgentState) -> Literal["retrieve", "end"]:
    return "end" if state.get("blocked") else "retrieve"


# ---------------------------------------------------------------------
# 4. Montagem do grafo
# ---------------------------------------------------------------------
def build_agent_graph(model_key: str = DEFAULT_MODEL_KEY):
    graph = StateGraph(AgentState)

    graph.add_node("validate_input", validate_input_node)
    graph.add_node("input_guardrail", input_guardrail_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("llm", make_llm_node(model_key))

    graph.set_entry_point("validate_input")
    graph.add_conditional_edges(
        "validate_input",
        route_after_validation,
        {"input_guardrail": "input_guardrail", "end": END},
    )
    graph.add_conditional_edges(
        "input_guardrail",
        route_after_guardrail,
        {"retrieve": "retrieve", "end": END},
    )
    graph.add_edge("retrieve", "llm")
    graph.add_edge("llm", END)

    # checkpointer = memória por sessão (Requisito 3.2), nativa do framework
    return graph.compile(checkpointer=checkpointer)


# ---------------------------------------------------------------------
# 5. Interface simples para o resto da aplicação (CLI, testes, etc.)
# ---------------------------------------------------------------------
class GoodWeAgent:
    """Wrapper de conveniência em torno do grafo compilado."""

    def __init__(self, model_key: str = DEFAULT_MODEL_KEY):
        self.model_key = model_key
        self.graph = build_agent_graph(model_key)

    def send(self, session_id: str, user_message: str) -> str:
        config = make_thread_config(session_id)
        result = self.graph.invoke(
            {"messages": [HumanMessage(content=user_message)], "blocked": False, "context": ""},
            config=config,
        )
        return result["messages"][-1].content

    def get_history(self, session_id: str) -> list[BaseMessage]:
        config = make_thread_config(session_id)
        snapshot = self.graph.get_state(config)
        return snapshot.values.get("messages", []) if snapshot else []
