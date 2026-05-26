---
status: pending
title: API de livros — upload, fila, progresso, pausa/retomar/cancelar, download
type: backend
complexity: high
dependencies:
  - task_02, task_05, task_06, task_07, task_08, task_09
---

# Tarefa 10: API de livros — upload, fila, progresso, pausa/retomar/cancelar, download

## Visão Geral
Implementar a API REST completa para gerenciamento de livros: upload de arquivo, lista de livros na fila, detalhes do livro, progresso, controle (pausar/retomar/cancelar), reordenação por prioridade e download do audiobook. Esta é a principal tarefa de integração que une todos os serviços.

<critical>
- SEMPRE LEIA o PRD e o TechSpec antes de começar
- CONSULTE O TECHSPEC para detalhes de implementação — não duplique aqui
- FOQUE NO "O QUÊ" — descreva o que precisa ser feito, não como
- MINIMIZE CÓDIO — mostre código só para ilustrar estrutura atual ou áreas problemáticas
- TESTES OBRIGATÓRIOS — toda tarefa DEVE incluir testes nos entregáveis
</critical>

<requirements>
- POST `/api/v1/livros/upload` DEVE aceitar multipart/form-data (PDF/EPUB/TXT)
- Upload DEVE validar tipo de arquivo, tamanho máximo e salvar no filesystem
- Upload DEVE criar registro em `livro` (status: "pendente") e `book_task` (status: "pendente")
- Upload DEVE disparar Celery task `process_book_task.delay(livro_id)`
- GET `/api/v1/livros` DEVE listar livros com filtros (status, paginação)
- GET `/api/v1/livros/{id}` DEVE retornar detalhes (status, progresso, personagens, falas)
- GET `/api/v1/livros/{id}/progresso` DEVE retornar progresso atual (0-100%, etapa, status)
- POST `/api/v1/livros/{id}/pausar` DEVE pausar task Celery (se em andamento)
- POST `/api/v1/livros/{id}/retomar` DEVE retomar task Celery (se pausada)
- POST `/api/v1/livros/{id}/cancelar` DEVE cancelar task Celery (se pendente ou em andamento)
- POST `/api/v1/livros/{id}/reordenar` DEVE atualizar prioridade no `book_task`
- GET `/api/v1/livros/{id}/download` DEVE retornar arquivo MP3 como stream
- DELETE `/api/v1/livros/{id}` DEVE remover livro e arquivos relacionados (soft delete)
- Todos os endpoints DEVE ser protegidos por `require_auth`

## Subtarefas
- [ ] Criar `backend/app/schemas/livro.py` com Pydantic schemas
- [ ] Criar `backend/app/services/livro_service.py` com lógica de gerenciamento de livros
- [ ] Implementar `POST /api/v1/livros/upload` — upload + validação + disparo de task
- [ ] Implementar `GET /api/v1/livros` — listagem com filtros e paginação
- [ ] Implementar `GET /api/v1/livros/{id}` — detalhes do livro
- [ ] Implementar `GET /api/v1/livros/{id}/progresso` — progresso atual
- [ ] Implementar `POST /api/v1/livros/{id}/pausar` — pausa task Celery
- [ ] Implementar `POST /api/v1/livros/{id}/retomar` — retoma task Celery
- [ ] Implementar `POST /api/v1/livros/{id}/cancelar` — cancela task Celery
- [ ] Implementar `POST /api/v1/livros/{id}/reordenar` — atualiza prioridade
- [ ] Implementar `GET /api/v1/livros/{id}/download` — stream de arquivo MP3
- [ ] Implementar `DELETE /api/v1/livros/{id}` — soft delete + limpeza de arquivos
- [ ] Montar routers em `backend/app/api/v1/livros.py`
- [ ] Registrar routers em `backend/app/main.py`

## Detalhes de Implementação

### Endpoints baseados no TechSpec
- Ver seção "Endpoints de API — Livros (Pipeline)" do TechSpec para todas as rotas, métodos, request/response e códigos de status

### Fluxo de upload baseado no TechSpec
- Ver seção "Fluxo de Dados — Upload de Livro" do TechSpec (10 passos)

### Arquivos Relevantes
- `src/pas/Book/DAO.Leitor.Book.pas` — `LocalizarCabecalho`, `SalvarPaginas` como referência para operações DB
- `src/pas/Book/Rgn.Leitor.Book.pas` — Fluxo original de `ProcessarBook`

### Arquivos Dependentes
- `backend/app/models/livro.py` (task_02) — Modelo Livro
- `backend/app/models/book_task.py` (task_02) — Modelo book_task
- `backend/app/services/pdf_processor.py` (task_05) — Para extrair texto do arquivo
- `backend/app/services/ia_analyzer.py` (task_07) — Para análise de personagens
- `backend/app/services/tts_engine.py` (task_08) — Para produção de áudio
- `backend/app/services/musicgen.py` (task_09) — Para trilha sonora
- `backend/app/middlewares/session.py` (task_03) — require_auth protege rotas

### ADRs Relacionados
- [ADR-004: Arquitetura do Sistema](adrs/adr-004.md) — Define API routers montados em FastAPI

## Entregáveis
- API completa de livros com 11 endpoints
- Upload funcional com disparo de Celery task
- Controle de fila: pausar, retomar, cancelar, reordenar
- Download de audiobook como stream
- Testes unitários: validação de schemas, lógica de serviço
- Testes de integração: fluxo completo de upload → fila → download

## Testes
- Testes unitários:
  - [ ] `POST /api/v1/livros/upload` com PDF válido cria livro e book_task
  - [ ] `POST /api/v1/livros/upload` com EPUB válido cria livro e book_task
  - [ ] `POST /api/v1/livros/upload` com TXT válido cria livro e book_task
  - [ ] `POST /api/v1/livros/upload` com arquivo inválido (ex: .exe) retorna 400
  - [ ] `POST /api/v1/livros/upload` com arquivo > 50MB retorna 400
  - [ ] `GET /api/v1/livros` retorna lista com filtros por status
  - [ ] `GET /api/v1/livros/{id}` retorna detalhes completos
  - [ ] `GET /api/v1/livros/{id}/progresso` retorna `{progresso: N, etapa: "...", status: "..."}`
  - [ ] `POST /api/v1/livros/{id}/pausar` atualiza book_task.status para "pausado"
  - [ ] `POST /api/v1/livros/{id}/retomar` atualiza book_task.status para "processando"
  - [ ] `POST /api/v1/livros/{id}/cancelar` atualiza book_task.status para "cancelado"
  - [ ] `GET /api/v1/livros/{id}/download` retorna arquivo MP3 como stream
  - [ ] `DELETE /api/v1/livros/{id}` remove registros e arquivos relacionados
- Testes de integração:
  - [ ] Upload de PDF → Celery task é disparada → progresso atualiza → download funciona
  - [ ] Upload de 2 PDFs simultâneos → ambos processados corretamente
  - [ ] Cancelar livro em andamento → book_task.status atualizado, Celery task parada

## Critérios de Sucesso
- Todos os testes passando
- Cobertura de testes >= 80%
- 11 endpoints funcionando corretamente
- Upload dispara Celery task e progresso atualiza
- Controle de fila funcional (pausar/retomar/cancelar/reordenar)
- Download retorna arquivo correto
