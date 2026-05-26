---
status: pending
title: Celery + Redis — worker, health check, estrutura de tasks
type: infra
complexity: medium
dependencies:
  - task_02
---

# Tarefa 06: Celery + Redis — worker, health check, estrutura de tasks

## Visão Geral
Configurar o Celery worker com Redis como broker, health checks e estrutura básica de tasks. Esta tarefa prepara o sistema de filas assíncronas sobre o qual o pipeline de processamento será construído.

<critical>
- SEMPRE LEIA o PRD e o TechSpec antes de começar
- CONSULTE O TECHSPEC para detalhes de implementação — não duplique aqui
- FOQUE NO "O QUÊ" — descreva o que precisa ser feito, não como
- MINIMIZE CÓDIO — mostre código só para ilustrar estrutura atual ou áreas problemáticas
- TESTES OBRIGATÓRIOS — toda tarefa DEVE incluir testes nos entregáveis
</critical>

<requirements>
- `celery_worker.py` DEVE criar app Celery com broker Redis e backend PostgreSQL
- Celery DEVE estar configurado com `broker_connection_retry_on_startup=True` para tolerância a falhas do Redis
- Task placeholder `process_book_task` DEVE existir (será substituída na task_11)
- Health check DEVE verificar conectividade com Redis e PostgreSQL
- `GET /health/redis` DEVE retornar `{redis: "ok"}` ou `{redis: "error", detail: "..."}`
- `GET /health/celery` DEVE retornar `{celery: "ok", worker_count: N}` ou erro
- Celery DEVE configurar `acks_late=True` para reprocessar tasks em caso de falha do worker
- Celery DEVE configurar `task_acks_late=True` e `task_reject_on_worker_lost=True`

## Subtarefas
- [ ] Criar `backend/celery_worker.py` com Celery app configurado (Redis broker + PostgreSQL backend)
- [ ] Criar `backend/app/api/v1/tasks.py` com endpoints de controle (pausar, retomar, cancelar, reordenar)
- [ ] Criar `backend/app/api/v1/tasks.py` com health checks (`/health/redis`, `/health/celery`)
- [ ] Criar task placeholder `process_book_task` (será implementada na task_11)
- [ ] Configurar Celery com retry automático (max_retries=3, backoff exponencial)
- [ ] Configurar `backend/celery_worker.py` com sinal SIGTERM para cleanup de temporários
- [ ] Criar `scripts/seed_data.sql` — inserir task de status inicial para novos livros

## Detalhes de Implementação

### Configuração baseada no TechSpec
- Ver seção "Monitoramento e Observabilidade" do TechSpec para health checks
- Ver seção "Tratamento de Erros" do TechSpec para retry e timeout
- Celery worker roda em container separado (mesmo código, processo diferente)

### Arquivos Relevantes
- `src/pas/Shared/Sistema/Rgn.Sistema.ThreadFactory.pas` — Referenciar padrão de threads OTL que será substituído
- `src/dpr/Leitor.dpr` — Referenciar loop `Monitorar()` que será substituído por Celery

### Arquivos Dependentes
- `backend/app/models/book_task.py` (task_02) — Modelo book_task para atualizar status
- `docker-compose.yml` (task_01) — Container celery precisa do Redis

### ADRs Relacionados
- [ADR-002: Stack Tecnológica](adrs/adr-002.md) — Define Celery + Redis como sistema de filas
- [ADR-004: Arquitetura do Sistema](adrs/adr-004.md) — Define Celery worker em container separado

## Entregáveis
- `celery_worker.py` configurado com Redis broker + PostgreSQL backend
- Endpoints de health check para Redis, Celery e PostgreSQL
- Endpoints de controle de fila (pausar, retomar, cancelar, reordenar)
- Task placeholder funcional
- Testes unitários: configuração do Celery, health checks
- Testes de integração: health check Redis/Celery retornam ok

## Testes
- Testes unitários:
  - [ ] Celery app é criado com broker Redis configurado
  - [ ] Celery app usa PostgreSQL como backend
  - [ ] `acks_late` está configurado como True
  - [ ] `broker_connection_retry_on_startup` está configurado como True
- Testes de integração:
  - [ ] `GET /health/redis` retorna `{redis: "ok"}` quando Redis está acessível
  - [ ] `GET /health/redis` retorna `{redis: "error"}` quando Redis está indisponível
  - [ ] `GET /health/celery` retorna `{celery: "ok", worker_count: 1}` quando worker está ativo
  - [ ] `GET /health/celery` retorna `{celery: "error"}` quando nenhum worker está ativo
  - [ ] Celery task é enviada e processada corretamente (task placeholder)

## Critérios de Sucesso
- Todos os testes passando
- Cobertura de testes >= 80%
- Celery worker conecta ao Redis e PostgreSQL sem erro
- Health checks retornam status correto
- Task placeholder é enviada e concluída via Celery
