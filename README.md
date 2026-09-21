# GoodWe EV Challenge — Sprint 03

Agente conversacional GoodWe reconstruído com **LangGraph**, com memória
por sessão, guardrails de segurança e comparação entre modelos de linguagem.

## O que mudou em relação às Sprints 1 e 2

A Sprint 1-2 (repositório original: `chargegrid-chatbot`) já usava LangGraph,
mas de forma mínima: um `add_sequence([retrieve, generate])` linear, sem nós
de decisão, com histórico de conversa numa lista Python comum e RAG sobre
PDFs/Word em `./docs`. A persona é o **operador comercial do ChargeGrid
Intelligence** (potência, faturamento, ciclos de carregamento) — mantida
nesta Sprint 03.

| Antes (Sprints 1-2) | Agora (Sprint 03) |
|---|---|
| Grafo linear (`add_sequence`), sem nós de decisão | Grafo ramificado: guardrail de entrada → retrieve → llm |
| Histórico gerenciado "na mão" (lista `chat_history`) | Memória por sessão nativa do framework (`MemorySaver`, por `thread_id`) |
| RAG sobre PDF/Word em `./docs` | RAG mantido (nó `retrieve`), agora também com `.txt/.md` em `knowledge_base/` |
| Segurança dependia só do texto do system prompt | Guardrail de entrada (regex) + guardrail de saída, além do system prompt |
| Um único modelo fixo (gpt-4o-mini), sem comparação | Configuração plugável (`app/config.py:MODEL_CONFIGS`), testado com 2+ modelos |

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edite o .env com suas chaves reais
```

**Importante:** a busca em documentos (RAG) usa `OpenAIEmbeddings`, herdado
da Sprint 1-2. Isso significa que `OPENAI_API_KEY` é necessária **mesmo se
você testar o modelo de chat da Anthropic/Google** — só o modelo que gera a
resposta final muda; a busca de contexto continua sempre via OpenAI.

## Rodando o chat

```bash
python -m app.main
python -m app.main --model anthropic_claude
```

## Rodando os testes

```bash
# Testes funcionais
pytest tests/test_functional.py -v

# Testes de memória (reproduz o exemplo do enunciado: condomínio + vagas)
pytest tests/test_memory.py -v

# Testes de segurança / prompt injection
pytest tests/test_security.py -v -s
```

Os testes de segurança geram um log em `logs/security_test_results.jsonl`
com o veredito (`passed: true/false`) e uma nota de análise para cada caso —
use isso para preencher a seção 4 do relatório de evolução.

## Comparação entre modelos (Requisito 5)

```bash
python -m tests.run_model_comparison
```

Isso roda o mesmo conjunto de casos (funcional + memória + segurança) em
cada modelo listado em `app/config.py:MODEL_CONFIGS` e salva os dados
brutos (latência, tamanho de resposta, erros) em
`results/model_comparison_raw.json`.

**Importante:** esses números precisam ser gerados rodando o script de
verdade com suas próprias chaves de API — eles não podem ser inventados,
pois a rubrica exige resultados reais de experimentação. Depois de rodar,
preencha `relatorio_modelos.md` com os números obtidos.

## Estrutura

```
app/
  config.py       -> system prompt (persona: operador comercial), configs de modelo
  guardrails.py   -> detecção de prompt injection e validação de saída
  memory.py       -> memória por sessão (checkpointer do LangGraph)
  rag.py          -> recuperação de contexto (RAG) sobre knowledge_base/
  agent.py        -> grafo do agente (LangGraph): guardrail → retrieve → llm
  main.py         -> CLI de chat
knowledge_base/   -> documentos de exemplo (potência, faturamento, ciclos)
tests/
  test_functional.py
  test_memory.py
  test_security.py
  run_model_comparison.py
relatorio_modelos.md
integrantes.txt
```

## Equipe

Ver `integrantes.txt`.

## Estrutura do repositório

- `app/`: implementação do agente e componentes da aplicação.
- `knowledge_base/`: base de conhecimento utilizada pelo agente.
- `tests/`: testes funcionais, memória, segurança e comparação de modelos.
- `docs/`: relatórios e documentação do Sprint 03.
- `scripts/`: scripts auxiliares para geração do relatório.
- `results/`: resultados gerados pelos experimentos.
- `logs/`: evidências de execução dos testes de segurança.

## Configuração de API

Nunca versione o arquivo `.env`. Crie uma cópia de `.env.example` chamada `.env` e preencha as credenciais localmente.

## Observação sobre resultados experimentais

Os resultados de latência, tokens/palavras, comparação entre modelos e logs de segurança devem ser gerados por execução real. Este repositório não inventa resultados quando as credenciais necessárias não estão disponíveis.


## Status dos experimentos

A infraestrutura de testes e comparação entre modelos está implementada. Os resultados quantitativos finais dependem de chamadas reais às APIs e, nesta versão, não são simulados nem inventados. O repositório documenta essa limitação de forma explícita.
