---
status: pending
title: Modelos de dados e migrations com SQLAlchemy + Alembic
type: backend
complexity: medium
dependencies:
  - task_01
---

# Tarefa 02: Modelos de dados e migrations com SQLAlchemy + Alembic

## Visão Geral
Implementar todos os modelos SQLAlchemy (9 tabelas) e migrations Alembic para o banco PostgreSQL. Esta tarefa substitui o DAO Delphi (`DAO.Leitor.Book.pas`) e cria o esquema do zero conforme definido no ADR-003.

<critical>
- SEMPRE LEIA o PRD e o TechSpec antes de começar
- CONSULTE O TECHSPEC para detalhes de implementação — não duplique aqui
- FOQUE NO "O QUÊ" — descreva o que precisa ser feito, não como
- MINIMIZE CÓDIO — mostre código só para ilustrar estrutura atual ou áreas problemáticas
- TESTES OBRIGATÓRIOS — toda tarefa DEVE incluir testes nos entregáveis
</critical>

<requirements>
- 9 modelos SQLAlchemy DEVE ser criado: `livro`, `pagina`, `personagem`, `falas`, `arquivo`, `api_config`, `voz`, `usuario`, `book_task`, `book_review`
- Todas as colunas DEVE seguir a nomenclatura snake_case sem prefixo TB_
- Todas as tabelas DEVE ter `created_at` e `updated_at` com timestamps automáticos
- Foreign keys DEVE ser explícitas com SQLAlchemy `ForeignKey`
- Índices DEVE ser criados em todas as colunas usadas em JOINs frequentes
- Alembic DEVE gerar migration inicial com todas as tabelas
- O script `scripts/seed_data.sql` DEVE incluir vozes padrão e usuário admin inicial
</requirements>

## Subtarefas
- [ ] Criar `backend/app/db.py` com session factory e engine configuration
- [ ] Criar `backend/app/models/livro.py` — modelo livro (cabeçalho do projeto)
- [ ] Criar `backend/app/models/pagina.py` — modelo pagina (texto por página)
- [ ] Criar `backend/app/models/personagem.py` — modelo personagem (com FK para livro e voz)
- [ ] Criar `backend/app/models/falas.py` — modelo falas (com FK para livro, pagina, personagem, arquivo)
- [ ] Criar `backend/app/models/arquivo.py` — modelo arquivo (PDFs, WAVs, MP3s, trilhas)
- [ ] Criar `backend/app/models/api_config.py` — modelo api_config (LLM, TTS, MusicGen)
- [ ] Criar `backend/app/models/voz.py` — modelo voz (banco de vozes)
- [ ] Criar `backend/app/models/usuario.py` — modelo usuario (autenticação)
- [ ] Criar `backend/app/models/book_task.py` — modelo book_task (fila de processamento)
- [ ] Criar `backend/app/models/book_review.py` — modelo book_review (Fase 3)
- [ ] Criar `backend/app/models/__init__.py` com importação de todos os modelos
- [ ] Configurar Alembic (alembic.ini, alembic/env.py)
- [ ] Gerar migration inicial com `alembic revision --autogenerate`
- [ ] Executar migration com `alembic upgrade head`
- [ ] Criar `scripts/seed_data.sql` com vozes padrão e usuário admin

## Detalhes de Implementação

### Modelos baseados no TechSpec
- Ver seção "Modelos de Dados" do TechSpec para todas as colunas, tipos e restrições de cada tabela
- 11 modelos no total (livro, pagina, personagem, falas, arquivo, api_config, voz, usuario, book_task, book_review)
- `book_review` é planejado para Fase 3 mas o modelo deve existir desde o início

### Arquivos Relevantes
- `src/pas/Book/Leitor.Book.pas` — Modelo original Delphi; referencia estrutura de dados
- `src/pas/Book/DAO.Leitor.Book.pas` — DAO original; referencia tabelas e relacionamentos
- `src/dpr/Win32/Debug/dbxconnections.ini` — Configuração DB original; migrar para环境变量

### Arquivos Dependentes
- `backend/app/main.py` (task_01) — Precisa importar models para registrar na Base classe declarativa
- `backend/app/schemas/` (task_07+) — Schemas Pydantic referenciam models

### ADRs Relacionados
- [ADR-003: Modelos de Dados](adrs/adr-003.md) — Define recriação do esquema com nomeclatura Python-friendly e migrations versionadas

## Entregáveis
- 11 modelos SQLAlchemy completos em `backend/app/models/`
- Migration Alembic inicial gerada e testada (funcional em container PostgreSQL)
- `scripts/seed_data.sql` com vozes padrão (masculino/feminino × crianca/adulto/idoso) e admin
- Testes unitários: criar sessão, inserir modelo, fazer select retorna registro
- Testes de integração: migration roda limpa em banco PostgreSQL efêmero

## Testes
- Testes unitários:
  - [ ] Instancia modelo `Livro` com dados válidos e valida com Pydantic
  - [ ] Instancia modelo `Personagem` com FKs e valida relacionamentos
  - [ ] Instancia modelo `Usuario` com senha_hash e valida hash
  - [ ] Timestamps `created_at` e `updated_at` são preenchidos automaticamente
  - [ ] Validação: `tipo_documento` aceita apenas pdf/epub/txt
  - [ ] Validação: `nivel_producao` aceita apenas basico/avancado/profissional
- Testes de integração:
  - [ ] `alembic upgrade head` cria todas as 11 tabelas sem erro
  - [ ] `alembic downgrade base` remove todas as tabelas limpa
  - [ ] `seed_data.sql` insere vozes e admin com sucesso

## Critérios de Sucesso
- Todos os testes passando
- Cobertura de testes >= 80%
- `alembic upgrade head` cria todas as 11 tabelas em PostgreSQL
- Seed script insere 9 vozes + 1 admin
- Models podem ser instanciados e validados via Pydantic
