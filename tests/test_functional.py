"""
test_functional.py
Casos de teste funcionais (Requisito 8 - "testes funcionais").

Cobrem o comportamento esperado "no caminho feliz": perguntas dentro do
escopo do projeto GoodWe devem receber respostas relevantes e coerentes.

Rode com:
    pytest tests/test_functional.py -v
(requer variáveis de ambiente configuradas em .env, pois faz chamadas reais)
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


# Casos alinhados à persona do operador comercial (mesma da Sprint 1-2) e
# aos dados de exemplo em knowledge_base/, para exercitar o RAG de verdade.
FUNCTIONAL_CASES = [
    {
        "id": "F1_saudacao",
        "input": "Olá, você pode me ajudar com dúvidas sobre a operação do ChargeGrid?",
        "expect_contains_any": ["claro", "posso", "ajudar", "operador", "chargegrid"],
    },
    {
        "id": "F2_pico_potencia",
        "input": "Qual foi o pico de potência no dia 15/09/2026?",
        "expect_contains_any": ["51", "19h"],
    },
    {
        "id": "F3_tarifacao_pico",
        "input": "Quanto devo cobrar por kWh entre 18h e 20h?",
        "expect_contains_any": ["2,10", "2.10"],
    },
    {
        "id": "F4_faturamento",
        "input": "Qual foi o faturamento total na semana de 15/09 a 21/09/2026?",
        "expect_contains_any": ["13.020", "13020"],
    },
    {
        "id": "F5_fora_de_escopo_educado",
        "input": "Pode me contar uma piada sobre política?",
        "expect_contains_any": ["escopo", "chargegrid", "eletroposto", "não posso", "foco"],
    },
]


def test_entrada_vazia(agent):
    """Bloco VALIDAÇÃO: mensagem vazia não deve chamar o LLM nem o RAG,
    e deve pedir a pergunta de volta."""
    response = agent.send("functional-entrada-vazia", "   ").lower()
    assert "não recebi" in response or "pode me dizer" in response


@pytest.mark.parametrize("case", FUNCTIONAL_CASES, ids=[c["id"] for c in FUNCTIONAL_CASES])
def test_functional_case(agent, case):
    session_id = f"functional-{case['id']}"
    response = agent.send(session_id, case["input"]).lower()

    assert len(response.strip()) > 0, "Resposta vazia"
    assert any(term in response for term in case["expect_contains_any"]), (
        f"Resposta não contém nenhum termo esperado {case['expect_contains_any']}. "
        f"Resposta recebida: {response}"
    )
