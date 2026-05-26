---
status: pending
title: IA Analyzer — LLM client com fallback cloud/local, retry e parsing
type: backend
complexity: high
dependencies:
  - task_02, task_04
---

# Tarefa 07: IA Analyzer — LLM client com fallback cloud/local, retry e parsing

## Visão Geral
Implementar o cliente de IA que se comunica com LLMs (cloud como Gemini API ou local como Ollama), com estratégia de fallback automático, retry com backoff exponencial e parsing de respostas. Esta tarefa substitui `Rgn.Leitor.IA.Http.pas`.

<critical>
- SEMPRE LEIA o PRD e o TechSpec antes de começar
- CONSULTE O TECHSPEC para detalhes de implementação — não duplique aqui
- FOQUE NO "O QUÊ" — descreva o que precisa ser feito, não como
- MINIMIZE CÓDIO — mostre código só para ilustrar estrutura atual ou áreas problemáticas
- TESTES OBRIGATÓRIOS — toda tarefa DEVE incluir testes nos entregáveis
</critical>

<requirements>
- `IAAnalyzer` DEVE suportar dois modos: cloud (via API configurada) e local (via API configurada)
- Fallback automático DEVE existir: tenta cloud primeiro, se falhar com RateLimitError ou ConnectionError, tenta local
- Retry com backoff exponencial DEVE existir: 3 tentativas para cloud (1s, 2s, 4s), 2 tentativas para local
- Timeout configurável: 60s para cloud, 120s para local
- `extrair_personagens(texto) -> list[CharacterProfile]` DEVE enviar prompt e parsear resposta
- `normalizar_nomes(personagens) -> list[CharacterProfile]` DEVE enviar nomes e receber normalização
- `definir_perfil(texto, personagem) -> CharacterProfile` DEVE retornar gênero e idade
- Parser DEVE lidar com respostas JSON e texto formatado (IA pode retornar qualquer coisa)
- Todas as chamadas DEVE usar `httpx.AsyncClient` para async

## Subtarefas
- [ ] Criar `backend/app/schemas/ia.py` com Pydantic schemas (CharacterProfile, etc.)
- [ ] Criar `backend/app/services/ia_analyzer.py` com classe `IAAnalyzer`
- [ ] Implementar `_chamar_llm_cloud(prompt)` — HTTP POST para API cloud configurada
- [ ] Implementar `_chamar_llm_local(prompt)` — HTTP POST para API local configurada
- [ ] Implementar estratégia de fallback cloud → local
- [ ] Implementar retry com backoff exponencial
- [ ] Implementar `_parse_resposta(texto)` — parser genérico para JSON ou texto
- [ ] Implementar `_extrair_personagens(texto)` — pipeline completo
- [ ] Implementar `_normalizar_nomes(personagens)` — pipeline completo
- [ ] Implementar `_definir_perfil(texto, personagem)` — pipeline completo

## Detalhes de Implementação

### Interface baseada no TechSpec
- Ver seção "Interfaces Principais — Interface de Análise com IA" do TechSpec
- `CharacterProfile` com `nome`, `genero` (masculino/feminino/neutro), `idade` (crianca/adulto/idoso)
- IAProvider enum: CLOUD ou LOCAL

### Prompt engineering
- Prompt para extração de personagens: enviar texto, receber `nome|fala` por linha
- Prompt para normalização: enviar lista de nomes, receber nomes padronizados com gênero
- Prompt para perfilamento: enviar falas do personagem, receber `Gênero|Idade`

### Arquivos Relevantes
- `src/pas/Book/Personagens/Rgn.Leitor.Book.Personagens.pas` — Prompts originais para extração de personagens
- `src/pas/Book/Narrador/Rgn.Leitor.Book.Narrador.pas` — Prompt para perfilamento de narrador
- `src/pas/Leitor.IA.Request.pas` — Estrutura original de requisição IA
- `src/pas/Leitor.IA.Response.pas` — Estrutura original de resposta IA

### Arquivos Dependentes
- `backend/app/models/api_config.py` (task_02) — Para ler configurações de LLM
- `backend/app/services/api_config_service.py` (task_04) — Para carregar URLs e tokens

### ADRs Relacionados
- [ADR-002: Stack Tecnológica](adrs/adr-002.md) — Define fallback cloud/local e httpx como client HTTP

## Entregáveis
- `ia_analyzer.py` com IAAnalyzer completo
- Fallback cloud/local funcional
- Retry com backoff exponencial
- Parsers para extração de personagens, normalização e perfilamento
- Testes unitários: parser de resposta, fallback, retry
- Testes de integração: chamada real a API LLM mockada

## Testes
- Testes unitários:
  - [ ] `_parse_resposta` extrai JSON válido de resposta de IA
  - [ ] `_parse_resposta` extrai texto formatado "nome|genero|idade" de resposta de IA
  - [ ] `_chamar_llm_cloud` com falha aciona fallback para `_chamar_llm_local`
  - [ ] `_chamar_llm_cloud` com RateLimitError aciona fallback
  - [ ] `_chamar_llm_cloud` com ConnectionError aciona fallback
  - [ ] `_chamar_llm_local` com falha retorna erro (sem fallback adicional)
  - [ ] Retry aciona 3 tentativas para cloud com backoff exponencial
  - [ ] Retry aciona 2 tentativas para local com backoff exponencial
- Testes de integração:
  - [ ] `IAAnalyzer` com API cloud mockada retorna personagens extraídos
  - [ ] `IAAnalyzer` com API cloud indisponível usa API local mockada
  - [ ] `IAAnalyzer` com ambas indisponíveis retorna erro descritivo

## Critérios de Sucesso
- Todos os testes passando
- Cobertura de testes >= 80%
- Fallback cloud → local funciona automaticamente
- Retry com backoff exponencial configurado corretamente
- Parsers extraem personagens, nomes e perfis corretamente
