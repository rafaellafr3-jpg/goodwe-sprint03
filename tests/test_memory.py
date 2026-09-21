"""
test_memory.py
Testes de memória conversacional (Requisito 3.2).

Reproduz literalmente o exemplo do enunciado: o usuário informa o nome
do condomínio e o número de vagas em turnos separados, e depois pergunta
sobre essas informações sem repeti-las. O agente deve responder
corretamente usando a memória de sessão gerenciada pelo LangGraph
(checkpointer), sem qualquer buffer manual no código da aplicação.

Rode com:
    pytest tests/test_memory.py -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.agent import GoodWeAgent
from app.config import DEFAULT_MODEL_KEY


@pytest.fixture(scope="module")
def agent():
    return GoodWeAgent(model_key=DEFAULT_MODEL_KEY)


def test_memory_condominio_vagas(agent):
    """Caso de exemplo do enunciado da Sprint 03 (seção 3.2)."""
    session_id = "memory-test-condominio-vagas"

    r1 = agent.send(session_id, "Estou utilizando um carregador no condomínio Solar Park.")
    assert len(r1.strip()) > 0

    r2 = agent.send(session_id, "Existem 12 vagas de carregamento.")
    assert len(r2.strip()) > 0

    r3 = agent.send(
        session_id,
        "Considerando o condomínio que mencionei, quantas vagas eu disse que existem?",
    ).lower()

    assert "12" in r3, f"Esperava que a resposta mencionasse '12' vagas. Resposta: {r3}"
    assert "solar park" in r3 or "condomínio" in r3, (
        f"Esperava que a resposta referenciasse o condomínio mencionado. Resposta: {r3}"
    )


def test_memory_isolada_por_sessao(agent):
    """Garante que sessões diferentes NÃO compartilham memória entre si
    (isolamento correto de contexto por thread_id)."""
    session_a = "memory-test-isolamento-A"
    session_b = "memory-test-isolamento-B"

    agent.send(session_a, "Meu carro é um modelo com bateria de 60 kWh.")
    r_b = agent.send(session_b, "Qual a capacidade da bateria do meu carro que eu mencionei?").lower()

    # Na sessão B, essa informação nunca foi dada -> o agente não deve
    # "inventar" nem confundir com a sessão A.
    assert "60" not in r_b, (
        "Vazamento de memória entre sessões diferentes: a sessão B não deveria "
        "conhecer o dado informado apenas na sessão A."
    )


def test_memory_quatro_turnos_multiplos_fatos(agent):
    """Teste extra com mais de 3 turnos, para reforçar robustez."""
    session_id = "memory-test-multiplos-fatos"

    agent.send(session_id, "Meu veículo é um sedã elétrico.")
    agent.send(session_id, "Eu carrego o carro geralmente à noite.")
    agent.send(session_id, "O carregador que uso fica no bairro Vila Nova.")
    r4 = agent.send(
        session_id,
        "Recapitulando: que tipo de veículo eu tenho, quando costumo carregar, "
        "e em que bairro fica meu carregador?",
    ).lower()

    assert "sedã" in r4 or "sedan" in r4
    assert "noite" in r4
    assert "vila nova" in r4
