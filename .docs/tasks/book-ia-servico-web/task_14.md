---
status: pending
title: Testes de integração — pipeline completo, auth, fila, HTMX
type: test
complexity: high
dependencies:
  - task_10, task_11, task_12
---

# Tarefa 14: Testes de integração — pipeline completo, auth, fila, HTMX

## Visão Geral
Implementar testes de integração que validam fluxos completos do sistema: upload → processamento → download, autenticação, fila com múltiplos livros, e interações HTMX. Usar `TestClient` do FastAPI, containers PostgreSQL e Redis efêmeros via Docker Compose.

<critical>
- SEMPRE LEIA o PRD e o TechSpec antes de começar
- CONSULTE O TECHSPEC para detalhes de implementação — não duplique aqui
- FOQUE NO "O QUÊ" — descreva o que precisa ser feito, não como
- MINIMIZE CÓDIO — mostre código só para ilustrar estrutura atual ou áreas problemáticas
- TESTES OBRIGATÓRIOS — toda tarefa DEVE incluir testes nos entregáveis
</critical>

<requirements>
- Todos os testes DEVE usar `FastAPI TestClient` para chamadas HTTP
- Containers PostgreSQL e Redis DEVE ser iniciados via Docker Compose ou pytest-postgresql para testes
- Fluxo de upload → Celery → progresso → download DEVE ser testado ponta a ponta
- Autenticação DEVE ser testada: setup → login → acesso protegido → logout
- Fila com múltiplos livros DEVE testar concorrência (múltiplas tasks Celery)
- HTMX calls DEVE ser testadas com `TestClient` (hx headers simulados)
- Testes DEVE usar banco de dados isolado (drop/create para cada teste)
- Celery worker DEVE ser mockado para testes determinísticos (ou testado com worker real em container)

## Subtarefas
- [ ] Criar `tests/conftest.py` com fixtures de integração (app, client, db, celery)
- [ ] Configurar banco de teste isolado (drop/create antes de cada teste)
- [ ] Criar `tests/test_integration/test_auth.py` — testes de autenticação
- [ ] Criar `tests/test_integration/test_upload_pipeline.py` — upload → processamento → download
- [ ] Criar `tests/test_integration/test_fila.py` — múltiplos livros na fila
- [ ] Criar `tests/test_integration/test_htmx.py` — fluxos HTMX
- [ ] Criar `tests/test_integration/test_configuracoes.py` — CRUD + teste de conexão
- [ ] Criar `tests/test_integration/test_celery_pipeline.py` — pipeline Celery completo
- [ ] Configurar `docker-compose.test.yml` para serviços de teste (postgres, redis)
- [ ] Criar script `scripts/run_tests.sh` para rodar todos os testes

## Detalhes de Implementação

### Testes baseados no TechSpec
- Ver seção "Testes de Integração" do TechSpec para cenários e dependências
- Framework: `pytest` + `TestClient` (FastAPI) + `pytest-postgresql`
- Setup: Docker Compose com PostgreSQL e Redis em containers efêmeros

### Cenários do TechSpec
- Upload → processamento → download
- Login → sessão → acesso protegido
- Configuração API → teste de conexão
- Fila com múltiplos livros
- Pausar/retomar/cancelar task
- Upload de EPUB e TXT

### Arquivos Relevantes
- `src/dpr/Win32/Debug/extrair_pdf.py` — Scripts de fixture (PDFs, EPUBs)
- `unittest/pas/TestRgn.Leitor.IA.Http.pas` — Referenciar estrutura de testes existentes

### Arquivos Dependentes
- `backend/app/main.py` (task_01) — App FastAPI para TestClient
- `backend/app/api/v1/livros.py` (task_10) — Endpoints de livros
- `backend/app/api/v1/auth.py` (task_03) — Endpoints de auth
- `backend/app/api/v1/configuracoes.py` (task_04) — Endpoints de config
- `backend/celery_worker.py` (task_06) — Celery worker para testes

### ADRs Relacionados
- [ADR-002: Stack Tecnológica](adrs/adr-002.md) — Define stack incluindo pytest para testes
- [ADR-004: Arquitetura do Sistema](adrs/adr-004.md) — Define estrutura do projeto

## Entregáveis
- `tests/test_integration/` com 6 arquivos de teste de integração
- `conftest.py` com fixtures de integração (app, client, db)
- `docker-compose.test.yml` para serviços de teste
- `scripts/run_tests.sh` para execução de testes
- Todos os testes passando em ambiente isolado (Docker)
- Cobertura de integração >= 80% nos módulos testados

## Testes
- Testes de integração Auth:
  - [ ] POST /api/v1/auth/setup cria admin e redireciona
  - [ ] POST /api/v1/auth/login com credenciais válidas define cookie
  - [ ] POST /api/v1/auth/login com credenciais inválidas retorna 401
  - [ ] Acesso a rota protegida sem sessão retorna 302 para /login
  - [ ] POST /api/v1/auth/logout destrói sessão
- Testes de integração Upload Pipeline:
  - [ ] POST /api/v1/livros/upload com PDF cria livro e dispara task Celery
  - [ ] GET /api/v1/livros/{id}/progresso retorna progresso atualizado
  - [ ] GET /api/v1/livros/{id}/download retorna arquivo MP3 após conclusão
  - [ ] POST /api/v1/livros/upload com EPUB cria livro corretamente
  - [ ] POST /api/v1/livros/upload com TXT cria livro corretamente
- Testes de integração Fila:
  - [ ] 3 livros na fila → todos processados corretamente
  - [ ] POST /api/v1/livros/{id}/pausar atualiza status
  - [ ] POST /api/v1/livros/{id}/retomar retoma processamento
  - [ ] POST /api/v1/livros/{id}/cancelar cancela processamento
  - [ ] POST /api/v1/livros/{id}/reordenar muda prioridade
- Testes de integração HTMX:
  - [ ] HTMX polling (`hx-trigger="every 3s"`) retorna HTML parcial com progresso
  - [ ] HTMX upload (`hx-post`) faz upload de arquivo via partial render
  - [ ] HTMX teste de conexão retorna badge verde/vermelho
- Testes de integração Configurações:
  - [ ] CRUD completo de api_config
  - [ ] Teste de conexão com URL válida retorna {conectado: true}
  - [ ] Teste de conexão com URL inválida retorna {conectado: false}

## Critérios de Sucesso
- Todos os testes passando
- Cobertura de testes >= 80%
- Pipeline completo upload → download funciona em ambiente isolado
- Múltiplos livros processados corretamente em fila
- HTMX calls funcionam com TestClient
- Testes determinísticos (mocks ou containers efêmeros)
- `pytest --cov` mostra cobertura >= 80%
