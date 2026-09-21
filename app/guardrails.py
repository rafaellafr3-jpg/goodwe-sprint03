"""
guardrails.py
Camada de segurança do agente GoodWe.

Além das instruções de segurança no system prompt (defesa "soft", via
instrução ao modelo), esta camada implementa uma defesa "hard" adicional,
independente do modelo de linguagem: um filtro de entrada baseado em
heurísticas para tentativas óbvias de prompt injection / jailbreak, e um
filtro de saída que verifica se o próprio system prompt vazou na resposta.

Isso segue a boa prática de "defesa em profundidade" (defense in depth):
nunca confiar apenas na obediência do modelo às instruções do system prompt.
"""

import re
from app.config import SYSTEM_PROMPT

# Padrões comuns de tentativa de manipulação / prompt injection.
# Lista não exaustiva - pode (e deve) ser expandida pelo grupo com mais casos.
INJECTION_PATTERNS = [
    r"ignore\s+(todas\s+)?(as\s+)?(suas\s+)?instru[cç][oõ]es",
    r"esque[cç]a\s+(suas\s+)?instru[cç][oõ]es",
    r"revele\s+(seu|o)\s+system\s*prompt",
    r"mostre\s+(seu|o)\s+prompt",
    r"qual\s+[eé]\s+(o\s+)?seu\s+system\s*prompt",
    r"modo\s+desenvolvedor",
    r"modo\s+debug",
    r"voc[eê]\s+n[aã]o\s+trabalha\s+mais\s+para",
    r"a\s+partir\s+de\s+agora\s+voc[eê]\s+[eé]",
    r"finja\s+que\s+voc[eê]\s+[eé]",
    r"you\s+are\s+now",
    r"ignore\s+previous\s+instructions",
    r"reveal\s+your\s+system\s+prompt",
    r"disregard\s+(all\s+)?(prior|previous)\s+instructions",
    r"act\s+as\s+if\s+you\s+(have\s+)?no\s+restrictions",
]

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]

INJECTION_REFUSAL_MESSAGE = (
    "Não posso seguir esse tipo de instrução. Continuo sendo o assistente "
    "GoodWe para o EV Challenge e não revelo minhas instruções internas. "
    "Posso te ajudar com alguma dúvida sobre mobilidade elétrica ou "
    "eletropostos?"
)

# Termos que sinalizam pedido de aconselhamento jurídico/financeiro/elétrico
# especializado, usados apenas para LOGGING/observabilidade dos testes
# (a recusa principal é feita pelo próprio modelo via system prompt).
SENSITIVE_TOPIC_HINTS = {
    "juridico": [r"processo\s+judicial", r"aconselhamento\s+jur[ií]dico", r"posso\s+processar", r"contrato\s+.*legal"],
    "financeiro": [r"devo\s+investir", r"financiamento", r"vale\s+a\s+pena\s+investir", r"aconselhamento\s+financeiro"],
    "eletrico_perigoso": [r"como\s+(fa[cç]o\s+para\s+)?(abrir|desmontar|religar)\s+o\s+quadro", r"mexer\s+na\s+fia[cç][aã]o", r"trocar\s+o\s+disjuntor"],
}
_SENSITIVE_COMPILED = {
    k: [re.compile(p, re.IGNORECASE) for p in v] for k, v in SENSITIVE_TOPIC_HINTS.items()
}


def detect_prompt_injection(user_message: str) -> bool:
    """Retorna True se a mensagem do usuário bater com padrões conhecidos
    de tentativa de manipulação/prompt injection."""
    return any(p.search(user_message) for p in _COMPILED_PATTERNS)


def detect_sensitive_topic(user_message: str) -> str | None:
    """Retorna a categoria de tópico sensível detectada (ou None), apenas
    para fins de log/observabilidade nos testes de segurança."""
    for category, patterns in _SENSITIVE_COMPILED.items():
        if any(p.search(user_message) for p in patterns):
            return category
    return None


def response_leaks_system_prompt(response_text: str) -> bool:
    """Verificação de saída: checa se trechos significativos do system
    prompt vazaram na resposta do modelo (defesa extra caso o modelo falhe)."""
    # Heurística simples: se um trecho longo o suficiente do system prompt
    # aparece quase literalmente na resposta, consideramos vazamento.
    # IMPORTANTE: estas frases precisam ser mantidas em sincronia com
    # app/config.py:SYSTEM_PROMPT — se o system prompt mudar de texto,
    # atualize aqui também (bug corrigido: frases antigas da persona
    # genérica não existiam mais no SYSTEM_PROMPT atual e por isso este
    # guardrail nunca disparava).
    marker_phrases = [
        "Você é o Chatbot GoodWe, assistente operacional do ChargeGrid",
        "LIMITES OBRIGATÓRIOS",
        "NÃO ULTRAPASSAR",
    ]
    return any(phrase.lower() in response_text.lower() for phrase in marker_phrases)


def apply_input_guardrail(user_message: str) -> tuple[bool, str | None]:
    """
    Guardrail de ENTRADA.
    Retorna (bloqueado: bool, mensagem_de_recusa: str|None).
    Se bloqueado=True, o agente não deve nem chamar o LLM: já responde
    com a mensagem de recusa padrão.
    """
    if detect_prompt_injection(user_message):
        return True, INJECTION_REFUSAL_MESSAGE
    return False, None


def apply_output_guardrail(response_text: str) -> str:
    """
    Guardrail de SAÍDA.
    Se detectar vazamento do system prompt na resposta do modelo,
    substitui a resposta pela mensagem de recusa padrão.
    """
    if response_leaks_system_prompt(response_text):
        return INJECTION_REFUSAL_MESSAGE
    return response_text
