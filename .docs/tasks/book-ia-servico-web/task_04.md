---
status: pending
title: API de configurações (CRUD de APIs + teste de conexão)
type: backend
complexity: medium
dependencies:
  - task_02
---

# Tarefa 04: API de configurações (CRUD de APIs + teste de conexão)

## Visão Geral
Implementar o CRUD completo de configurações de serviços de IA (LLM, TTS, MusicGen) com endpoint de teste de conexão. As credenciais (tokens) devem ser armazenadas de forma criptografada no banco.

<critical>
- SEMPRE LEIA o PRD e o TechSpec antes de começar
- CONSULTE O TECHSPEC para detalhes de implementação — não duplique aqui
- FOQUE NO "O QUÊ" — descreva o que precisa ser feito, não como
- MINIMIZE CÓDIO — mostre código só para ilustrar estrutura atual ou áreas problemáticas
- TESTES OBRIGATÓRIOS — toda tarefa DEVE incluir testes nos entregáveis
</critical>

<requirements>
- CRUD completo DEVE existir para `api_config`: criar, listar, atualizar, deletar
- O campo `token` DEVE ser criptografado antes de salvar no banco (Fernet ou similar)
- Endpoint de teste DEVE fazer requisição real ao endpoint configurado e retornar status de conexão + latência
- Validação: `tipo` DEVE ser llm, tts ou musicgen
- Validação: `modo` DEVE ser cloud ou local
- Endpoint DELETE DEVE marcar como inativo ao invés de remover fisicamente (soft delete)

## Subtarefas
- [ ] Criar `backend/app/schemas/api_config.py` com Pydantic schemas (create, update, response)
- [ ] Criar `backend/app/services/api_config_service.py` com CRUD e criptografia de token
- [ ] Criar `backend/app/api/v1/configuracoes.py` com routers de CRUD
- [ ] Implementar `POST /api/v1/configuracoes/apis/{id}/testar` — faz ping real ao endpoint
- [ ] Implementar `POST /api/v1/configuracoes/apis` — cria nova configuração
- [ ] Implementar `GET /api/v1/configuracoes/apis` — lista todas configurações
- [ ] Implementar `PUT /api/v1/configuracoes/apis/{id}` — atualiza configuração
- [ ] Implementar `DELETE /api/v1/configuracoes/apis/{id}` — soft delete (marca inativo)

## Detalhes de Implementação

### Schemas baseados no TechSpec
- Ver seção "Endpoints de API — Configurações de API" do TechSpec
- Campos: tipo (enum), modo (enum), url (varchar), token (varchar criptografado), modelo (varchar), ativo (boolean)

### Arquivos Relevantes
- `src/pas/Book/DAO.Leitor.Book.pas` — `LocalizarAPIS` e `SalvarAPIs` como referência
- `src/pas/Leitor.IA.Request.pas` — Referenciar estrutura de requisição IA

### Arquivos Dependentes
- `backend/app/models/api_config.py` (task_02) — Modelo SQLAlchemy
- `backend/app/deps.py` (task_03) — require_auth protege rotas

### ADRs Relacionados
- [ADR-002: Stack Tecnológica](adrs/adr-002.md) — Define configurações como cloud ou local

## Entregáveis
- CRUD completo de api_config com criptografia de token
- Endpoint de teste de conexão funcional
- Testes unitários: criptografia/descriptografia, validação de schemas
- Testes de integração: fluxo completo CRUD + teste de conexão

## Testes
- Testes unitários:
  - [ ] `Fernet.encrypt(b"token123")` gera token criptografado
  - [ ] `Fernet.decrypt(token)` retorna valor original
  - [ ] `api_config.tipo` aceita apenas llm/tts/musicgen
  - [ ] `api_config.modo` aceita apenas cloud/local
- Testes de integração:
  - [ ] POST /api/v1/configuracoes/apis cria configuração com token criptografado
  - [ ] GET /api/v1/configuracoes/apis retorna lista sem revelar token descriptografado
  - [ ] POST /api/v1/configuracoes/apis/{id}/testar com URL válida retorna `{conectado: true, latencia_ms: N}`
  - [ ] POST /api/v1/configuracoes/apis/{id}/testar com URL inválida retorna `{conectado: false, erro: "..."}`
  - [ ] DELETE /api/v1/configuracoes/apis/{id} marca como inativo

## Critérios de Sucesso
- Todos os testes passando
- Cobertura de testes >= 80%
- CRUD funcional com criptografia de tokens
- Teste de conexão valida URL e retorna latência
- Tokens nunca são expostos em responses (sempre mascarados)
