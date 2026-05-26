---
status: pending
title: Scaffolding do projeto Python
type: infra
complexity: low
dependencies: []
---

# Tarefa 01: Scaffolding do projeto Python

## Visão Geral
Configurar a estrutura base do projeto Book-IA em Python: diretórios, arquivos de configuração, dependências e Docker Compose. Esta tarefa cria a fundação sobre a qual todas as demais tarefas serão construídas.

<critical>
- SEMPRE LEIA o PRD e o TechSpec antes de começar
- CONSULTE O TECHSPEC para detalhes de implementação — não duplique aqui
- FOQUE NO "O QUÊ" — descreva o que precisa ser feito, não como
- MINIMIZE CÓDIO — mostre código só para ilustrar estrutura atual ou áreas problemáticas
- TESTES OBRIGATÓRIOS — toda tarefa DEVE incluir testes nos entregáveis
</critical>

<requirements>
- O projeto DEVE ter a estrutura de diretórios definida no ADR-004
- O `requirements.txt` DEVE listar todas dependências com versões pinadas
- O `Dockerfile` DEVE ser multi-stage (build + runtime)
- O `docker-compose.yml` DEVE orquestrar 4 serviços: backend, celery worker, redis, postgres
- O `.gitignore` DEVE excluir artefatos de build, caches, .env local, e arquivos do Delphi não relevantes
</requirements>

## Subtarefas
- [ ] Criar estrutura de diretórios: `backend/app/`, `backend/templates/`, `backend/static/`, `tests/`, `scripts/`
- [ ] Criar `backend/app/main.py` com instância FastAPI básica
- [ ] Criar `backend/app/config.py` com settings baseados em环境变量
- [ ] Criar `requirements.txt` com todas dependências (FastAPI, uvicorn, SQLAlchemy, alembic, celery, redis, httpx, etc.)
- [ ] Criar `Dockerfile` multi-stage para o backend
- [ ] Criar `docker-compose.yml` com 4 serviços (backend, celery, redis, postgres)
- [ ] Criar `.gitignore` adequado para projeto Python + Delphi
- [ ] Criar `README.md` com instruções de setup e execução

## Detalhes de Implementação

### Estrutura de diretórios esperada
```
Book-IA/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── deps.py
│   │   ├── api/v1/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── templates/
│   ├── celery_worker.py
│   ├── requirements.txt
│   ├── alembic.ini
│   └── alembic/
├── tests/
│   ├── test_api/
│   ├── test_services/
│   └── test_celery/
├── scripts/
├── Dockerfile
├── docker-compose.yml
├── .gitignore
└── README.md
```

### Arquivos Relevantes
- `src/dpr/Leitor.dpr` — Referenciar para entender o fluxo atual (entrada: S:\dsv\NLP\pdfs\processar, saída: S:\dsv\TTS\out\)
- `src/dpr/Win32/Debug/extrair_pdf.py` — Script Python existente; será migrado para `app/services/pdf_processor.py`
- `design/` — Assets do design system Pac-Man Tech Theme; serão referenciados pelos templates

### Arquivos Dependentes
- `src/dpr/Leitor.dproj` — Referenciar para entender dependências Delphi que serão substituídas
- `src/pas/` — Código Delphi existente que será reimplementado em Python

### ADRs Relacionados
- [ADR-002: Stack Tecnológica](adrs/adr-002.md) — Define FastAPI, HTMX, PostgreSQL, Celery/Redis
- [ADR-004: Arquitetura do Sistema](adrs/adr-004.md) — Define estrutura de diretórios e deploy via Docker Compose

## Entregáveis
- Estrutura de diretórios completa conforme ADR-004
- `requirements.txt` com dependências pinadas (versões estáveis)
- `Dockerfile` multi-stage funcional
- `docker-compose.yml` com 4 serviços (backend, celery, redis, postgres)
- `.gitignore` adequado
- `README.md` com instruções de setup e primeiros passos
- Testes unitários: configuração do ambiente de teste (pytest.ini, conftest.py)

## Testes
- Testes de configuração:
  - [ ] `docker-compose up` inicia todos os 4 containers sem erro
  - [ ] `docker-compose exec backend python -c "import fastapi"` importa com sucesso
  - [ ] `docker-compose exec backend python -c "import sqlalchemy"` importa com sucesso
  - [ ] `docker-compose exec backend python -c "import celery"` importa com sucesso
  - [ ] `docker-compose exec backend python -c "import alembic"` importa com sucesso
- Testes de integração:
  - [ ] `curl http://localhost:8000/health` retorna 200 com JSON de health check
  - [ ] `docker-compose down` para todos os containers limpamente

## Critérios de Sucesso
- Todos os testes passando
- `docker-compose up -d` inicia todos os serviços sem erro
- `docker-compose exec backend python app/main.py` (via uvicorn) inicia o servidor
- `curl localhost:8000/health` retorna `{"status": "ok"}`
- Cobertura de testes >= 80% (configuração do ambiente)
