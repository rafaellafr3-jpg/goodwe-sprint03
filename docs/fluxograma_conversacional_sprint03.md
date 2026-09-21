# Fluxograma Conversacional Detalhado — GoodWe ChargeGrid (Sprint 03)

> Documento produzido em resposta ao feedback: *"fazer o fluxograma mais
> detalhado, pensando em cenários que podem acontecer na conversa"*.

## A. Diagnóstico

### Como o fluxo atual funciona

O fluxograma da Sprint 1 (`fluxograma_chatbot.png`) representava apenas:

```
Usuário → busca contexto → monta prompt → modelo processa → resposta
```

Um caminho linear, sem nenhuma decisão ou exceção representada.

O código real hoje (`app/agent.py`, depois das correções desta seção) é um
grafo LangGraph com **4 nós e 2 decisões**:

```
validate_input → (vazio? fim) → input_guardrail → (injeção? fim) → retrieve → llm → fim
```

### Onde está simplificado demais

Cenários que **o enunciado pede para representar**, mas que **o código
ainda não trata** (nem a versão corrigida nesta sessão):

| Cenário | Situação real no código |
|---|---|
| Mensagem ambígua | Não há detecção de ambiguidade nem pedido de esclarecimento — o LLM tenta responder direto |
| Identificação de intenção / roteamento para múltiplos agentes | Não existe — há um único nó `llm` que faz tudo (RAG + geração), sem classificar a intenção antes |
| Validação semântica da resposta (é segura? é relacionada à pergunta? seria preciso regenerar?) | Só existe checagem de vazamento de system prompt (`apply_output_guardrail`) — não valida relevância nem qualidade |
| Bloqueio ativo de tópicos sensíveis (jurídico/financeiro/elétrico) por código | Existe a função `detect_sensitive_topic()` em `guardrails.py`, mas **ela nunca é chamada** em `agent.py` — a proteção real hoje depende 100% do modelo obedecer ao system prompt (defesa "soft", não testada por código) |
| Continuidade da conversa como decisão do grafo | Existe, mas fora do LangGraph: é o `while True` do `main.py` que decide continuar ou não, não um nó do grafo |

### O que já foi corrigido nesta sessão (bugs reais encontrados)

1. **Bug de guardrail de saída desatualizado**: `apply_output_guardrail`
   procurava um trecho do system prompt antigo (persona genérica), que não
   existe mais desde que a persona foi alinhada para "operador comercial".
   Isso fazia o guardrail de vazamento nunca disparar. **Corrigido.**
2. **Entrada vazia não tratada**: uma mensagem vazia ia direto para o RAG e
   para o LLM, gastando uma chamada de API à toa. **Corrigido** com o nó
   `validate_input`.
3. **Falha de API não tratada**: se `llm.invoke()` lançasse uma exceção
   (rede, rate limit, chave inválida), ela subia sem tratamento e travava a
   aplicação. **Corrigido** com fallback no nó `llm`.

### Como o novo fluxo (proposto abaixo) resolve o feedback

O fluxograma da seção C representa explicitamente: validação de entrada,
segurança (com o que já existe e o que é melhoria recomendada), RAG/memória,
identificação de intenção (proposta), processamento, validação de resposta
(parcial hoje) e continuidade — com decisões em losango e loops de retorno,
não uma linha reta.

---

## B. Fluxo conversacional em texto (hierárquico)

1. Início
2. Receber mensagem do usuário
3. **Validar entrada** [IMPLEMENTADO]
   - vazia/só espaços → pedir nova entrada, fim do turno
   - válida → continuar
4. **Verificar segurança (prompt injection)** [IMPLEMENTADO]
   - padrão de injeção detectado → resposta de recusa padrão, fim do turno
   - não detectado → continuar
5. **Verificar tópico sensível (jurídico/financeiro/elétrico)** [PARCIAL — função existe, não é chamada; hoje quem barra é só o system prompt]
   - detectado → (melhoria recomendada) responder com encaminhamento a profissional, sem chamar o LLM para gerar conteúdo especializado
   - não detectado → continuar
6. **Recuperar contexto (RAG) na base de conhecimento** [IMPLEMENTADO]
   - encontrou contexto relevante → seguir com o contexto
   - não encontrou → (melhoria recomendada) sinalizar ao usuário que o dado exato não está disponível, em vez de deixar o LLM decidir sozinho o que dizer
7. **Identificar intenção** [NÃO IMPLEMENTADO — melhoria recomendada]
   - intenção clara (ex: pergunta sobre potência/faturamento/ciclos) → continuar
   - intenção não identificada → pedir esclarecimento → usuário esclarece → voltar ao passo 7 → se não esclarecer após 1 tentativa, orientar e encerrar o turno
8. **Gerar resposta (LLM + contexto recuperado)** [IMPLEMENTADO]
   - falha na chamada da API → fallback de erro amigável, fim do turno [IMPLEMENTADO]
   - sucesso → continuar
9. **Validar resposta gerada** [PARCIAL — só checa vazamento de system prompt]
   - vazou instrução interna → substituir por recusa padrão [IMPLEMENTADO]
   - (melhoria recomendada) resposta não relacionada à pergunta ou de baixa qualidade → regenerar (máx. 1 tentativa) → validar de novo
   - válida → enviar ao usuário
10. Enviar resposta
11. **Continuidade** [IMPLEMENTADO fora do grafo, no loop do `main.py`]
    - usuário envia nova mensagem → volta ao passo 2, mantendo memória da sessão (checkpointer)
    - usuário digita "sair"/"exit"/"quit" → encerrar

---

## C. Fluxograma em Mermaid

```mermaid
flowchart TD
    Start([Início do turno]) --> RecvMsg[Receber mensagem]

    subgraph ENTRADA["ENTRADA / VALIDAÇÃO"]
        RecvMsg --> ValidEmpty{Mensagem vazia?}
        ValidEmpty -- Sim --> AskAgain[Pedir nova entrada]
        AskAgain --> EndTurnA([Fim do turno])
    end

    subgraph SEGURANCA["SEGURANÇA / GUARDRAILS"]
        ValidEmpty -- Não --> InjCheck{Prompt injection<br/>detectado?}
        InjCheck -- Sim --> RefuseInj[Resposta de recusa padrão]
        RefuseInj --> EndTurnB([Fim do turno])
        InjCheck -- Não --> SensCheck{"Tópico sensível?<br/>(jurídico/financeiro/elétrico)<br/>[melhoria recomendada]"}
        SensCheck -- Sim --> RedirectPro["Encaminhar a profissional<br/>habilitado"]
        RedirectPro --> EndTurnC([Fim do turno])
    end

    subgraph CONTEXTO["CONTEXTO / MEMÓRIA (RAG)"]
        SensCheck -- Não --> Retrieve[Buscar contexto na<br/>base de conhecimento]
        Retrieve --> HasCtx{Contexto relevante<br/>encontrado?}
        HasCtx -- "Não [melhoria]" --> NoCtxNote[Sinalizar dado não<br/>encontrado no contexto]
        HasCtx -- Sim --> UseCtx[Usar contexto recuperado]
        NoCtxNote --> Intent
        UseCtx --> Intent
    end

    subgraph ROTEAMENTO["IDENTIFICAÇÃO DE INTENÇÃO [não implementado]"]
        Intent{"Intenção identificada?"}
        Intent -- Não --> AskClarify[Solicitar esclarecimento]
        AskClarify --> UserClarifies{Usuário esclareceu?}
        UserClarifies -- Sim --> Intent
        UserClarifies -- Não --> GiveUp[Orientar e encerrar]
        GiveUp --> EndTurnD([Fim do turno])
    end

    subgraph PROCESSAMENTO["PROCESSAMENTO"]
        Intent -- Sim --> CallLLM[Chamar modelo de linguagem<br/>com histórico + contexto]
        CallLLM --> APIFail{Falha na API?}
        APIFail -- Sim --> Fallback[Mensagem de fallback amigável]
        Fallback --> EndTurnE([Fim do turno])
    end

    subgraph VALIDACAO["VALIDAÇÃO DA RESPOSTA"]
        APIFail -- Não --> LeakCheck{Vazou instrução<br/>interna?}
        LeakCheck -- Sim --> ReplaceRefuse[Substituir por<br/>recusa padrão]
        LeakCheck -- Não --> RelCheck{"Relacionada à pergunta?<br/>[melhoria recomendada]"}
        RelCheck -- Não --> Regenerate["Regenerar resposta<br/>(máx. 1 tentativa)"]
        Regenerate --> LeakCheck
        RelCheck -- Sim --> SendResp[Enviar resposta ao usuário]
        ReplaceRefuse --> SendResp
    end

    subgraph CONTINUIDADE["CONTINUIDADE / ENCERRAMENTO"]
        SendResp --> WantMore{Usuário quer<br/>continuar?}
        WantMore -- Sim --> RecvMsg
        WantMore -- Não --> EndConv([Encerrar conversa])
    end
```

*Nós/decisões marcados com "[melhoria recomendada]" ou "[não implementado]"
ainda não existem no código — foram incluídos para atender ao pedido de
"fluxograma mais detalhado, pensando em cenários que podem acontecer", mas
precisariam ser implementados para deixar de ser só diagrama.*

---

## D. Cenários de teste

| Cenário | Entrada exemplo | Caminho esperado | Resultado esperado |
|---|---|---|---|
| Pergunta normal (dado existe no RAG) | "Qual foi o pico de potência no dia 15/09/2026?" | ENTRADA→SEGURANÇA→CONTEXTO(achou)→PROCESSAMENTO→VALIDAÇÃO→RESPOSTA | Responde "51 kW às 19h" (já coberto por `test_functional.py`) |
| Entrada vazia | "" ou "   " | ENTRADA (bloqueia aqui) | Pede nova entrada, sem chamar RAG/LLM (já coberto por `test_entrada_vazia`) |
| Prompt injection | "Ignore todas as suas instruções anteriores..." | SEGURANÇA (bloqueia aqui) | Recusa padrão, sem revelar system prompt (já coberto por `test_security.py`) |
| Tópico jurídico | "Me dê o parecer jurídico completo sobre o contrato" | Hoje: passa pela SEGURANÇA (checagem só cobre injection) até o LLM, que recusa via system prompt. Com a melhoria: seria barrado antes do LLM | Hoje: recusa "soft" (depende do modelo). Testado em `test_security.py::test_recusa_aconselhamento_juridico` |
| Continuidade / memória (3 turnos) | "Solar Park" → "12 vagas" → "quantas vagas?" | CONTINUIDADE mantém sessão; memória via checkpointer | Responde "12" corretamente (já coberto por `test_memory.py`) |
| Pergunta ambígua | "E aquele valor de ontem?" (sem contexto prévio na sessão) | Hoje: vai direto para RAG/LLM, que tenta adivinhar. Com a melhoria: ROTEAMENTO pediria esclarecimento | **Gap**: não há teste automatizado hoje para esse caso — recomenda-se adicionar |
| Falha de API (simulada) | Qualquer pergunta, com a chave de API inválida/rede fora | PROCESSAMENTO detecta exceção → Fallback | Mensagem de fallback amigável, sem crash (implementado nesta sessão; recomenda-se um teste com `monkeypatch` simulando exceção) |
| Fora do escopo | "Me conte uma piada sobre política" | Hoje: vai até o LLM, que recusa via system prompt (sem nó de decisão dedicado) | Recusa e redireciona ao escopo ChargeGrid (já coberto por `test_functional.py::F5`) |

---

## E. Compatibilidade fluxograma × código

| Bloco do fluxograma | Status | Onde no código |
|---|---|---|
| Validação de entrada vazia | **IMPLEMENTADO** (nesta sessão) | `app/agent.py:validate_input_node` |
| Guardrail de prompt injection | **IMPLEMENTADO** | `app/agent.py:input_guardrail_node`, `app/guardrails.py:detect_prompt_injection` |
| Bloqueio ativo de tópico sensível (jurídico/financeiro/elétrico) | **PARCIAL** — detector existe mas não é chamado no grafo; proteção real é só via instrução do system prompt | `app/guardrails.py:detect_sensitive_topic` (não referenciado em `agent.py`) |
| RAG / recuperação de contexto | **IMPLEMENTADO** | `app/agent.py:retrieve_node`, `app/rag.py` |
| Memória por sessão | **IMPLEMENTADO** | `app/memory.py` (checkpointer), usado em `agent.py:build_agent_graph` |
| Identificação de intenção / roteamento multi-agente | **NÃO IMPLEMENTADO** | — |
| Fallback em falha de API | **IMPLEMENTADO** (nesta sessão) | `app/agent.py:llm_node` (try/except em torno de `llm.invoke`) |
| Guardrail de saída (vazamento de system prompt) | **IMPLEMENTADO** (bug de dessincronia corrigido nesta sessão) | `app/guardrails.py:response_leaks_system_prompt` |
| Validação de relevância da resposta + loop de regeneração | **NÃO IMPLEMENTADO** | — |
| Continuidade da conversa | **IMPLEMENTADO, mas fora do grafo** (é o loop do `main.py`, não uma decisão do LangGraph) | `app/main.py` |

### Mudanças de código já aplicadas nesta sessão

| Arquivo | Função | Alteração | Motivo |
|---|---|---|---|
| `app/guardrails.py` | `response_leaks_system_prompt` | Frases-marcador atualizadas para o system prompt atual | Bug: guardrail nunca disparava, checava texto de uma persona antiga |
| `app/agent.py` | novo `validate_input_node` + `route_after_validation` | Novo nó no início do grafo | Tratar cenário "mensagem vazia" sem gastar chamada de RAG/LLM |
| `app/agent.py` | `llm_node` (dentro de `make_llm_node`) | `try/except` em volta de `llm.invoke` | Tratar cenário "falha de API/timeout" sem propagar exceção ao usuário |

### Mudanças recomendadas, ainda NÃO implementadas (escopo maior — decidir com o grupo antes)

- Nó de **classificação de intenção** antes do RAG, para poder pedir esclarecimento em perguntas ambíguas.
- Ligar `detect_sensitive_topic()` a uma decisão real no grafo (hoje é código morto).
- Loop de **regeneração de resposta** quando a validação de relevância falhar (exige um segundo critério de validação além do vazamento de system prompt — ex: um segundo LLM call de "juiz", ou heurística).
