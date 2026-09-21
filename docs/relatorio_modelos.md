# Relatório de Comparação entre Modelos — GoodWe EV Challenge (Sprint 03)

## 1. Objetivo

Este documento registra a estratégia de comparação entre dois modelos de linguagem configurados no agente GoodWe. O mesmo conjunto de testes e os mesmos parâmetros devem ser utilizados para reduzir diferenças causadas por configuração.

**Importante:** a execução experimental completa não foi concluída nesta versão por falta de créditos/quotas de API. Portanto, não são apresentados números, notas ou taxas de acerto inventados.

## 2. Modelos avaliados

| Modelo | Provedor | Configuração |
|---|---|---|
| `gpt-4o-mini` | OpenAI | Modelo A |
| `claude-sonnet-4-5` | Anthropic | Modelo B |

## 3. Configuração do experimento

| Parâmetro | Valor |
|---|---|
| Temperature | 0.3 |
| Max tokens | 500 |
| System prompt | Mesmo `SYSTEM_PROMPT` de `app/config.py` |
| Casos | Mesmo conjunto definido em `tests/run_model_comparison.py` |
| Métricas previstas | Latência, tamanho das respostas, erros e comportamento nos testes |

O script `tests/run_model_comparison.py` automatiza a execução e grava os resultados em `results/model_comparison_raw.json`.

## 4. Status dos resultados

| Item | Status |
|---|---|
| Configuração de dois modelos | Concluída |
| Mesmo conjunto de testes | Concluído |
| Script de comparação | Concluído |
| Medição de latência | Implementada |
| Registro de resultados em JSON | Implementado |
| Execução experimental completa | **Pendente de créditos/quotas de API** |
| Escolha final baseada em métricas reais | **Pendente de execução** |

Durante uma tentativa anterior de execução, a API da OpenAI retornou erro de quota/créditos (`insufficient_quota` / `credit_balance_exhausted`). Por esse motivo, os resultados quantitativos não foram fabricados.

## 5. Interpretação atual

A arquitetura é independente do provedor do modelo de chat: o agente pode alternar entre os modelos pela configuração. O mecanismo de memória continua sendo o checkpointer do LangGraph, enquanto a recuperação da base de conhecimento utiliza `OpenAIEmbeddings`.

Isso significa que a comparação entre os modelos deve ser feita quando houver créditos disponíveis, utilizando exatamente o mesmo conjunto de casos. A escolha do modelo final deve então ser registrada com base nos resultados observados.

**Modelo atualmente configurado como padrão no código:** `gpt-4o-mini`.

Essa configuração representa apenas o estado atual do projeto. Não deve ser interpretada como uma conclusão experimental de superioridade.

## 6. Como finalizar a comparação

1. Configurar as chaves de API no `.env`.
2. Executar os testes funcionais, de memória e segurança.
3. Executar `python -m tests.run_model_comparison`.
4. Conferir `results/model_comparison_raw.json`.
5. Registrar as métricas reais e as diferenças observadas.
6. Documentar a escolha final do modelo com base nos dados.

> **Ponto pendente para a entrega:** se a avaliação exigir obrigatoriamente métricas reais de dois LLMs, será necessário realizar essa execução com créditos disponíveis. Não é necessário alterar o código para isso; a infraestrutura de comparação já está preparada.
