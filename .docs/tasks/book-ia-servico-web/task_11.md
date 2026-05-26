---
status: pending
title: Celery task process_book — orquestração completa do pipeline
type: backend
complexity: high
dependencies:
  - task_07, task_08, task_09, task_10
---

# Tarefa 11: Celery task process_book — orquestração completa do pipeline

## Visão Geral
Implementar a task Celery `process_book` que orquestra o pipeline completo de processamento: PDF processing → IA analysis → voice assignment → audio production → MusicGen → unification. Esta tarefa substitui o fluxo sequencial do Delphi (`Rgn.Leitor.Book.ProcessarBook`).

<critical>
- SEMPRE LEIA o PRD e o TechSpec antes de começar
- CONSULTE O TECHSPEC para detalhes de implementação — não duplique aqui
- FOQUE NO "O QUÊ" — descreva o que precisa ser feito, não como
- MINIMIZE CÓDIO — mostre código só para ilustrar estrutura atual ou áreas problemáticas
- TESTES OBRIGATÓRIOS — toda tarefa DEVE incluir testes nos entregáveis
</critical>

<requirements>
- `process_book(livro_id)` DEVE executar as 6 etapas do pipeline em sequência
- Etapa 1 (PDF_PROCESSING, 0-10%): extrair texto, salvar páginas em `pagina`
- Etapa 2 (IA_ANALYSIS, 10-40%): personagens, normalização, perfilamento, narrador
- Etapa 3 (VOICE_ASSIGNMENT, 40-50%): carregar vozes, matching por gênero/idade
- Etapa 4 (AUDIO_PRODUCTION, 50-90%): chunking, TTS, WAV→MP3, unificar
- Etapa 5 (MUSICGEN, 90-95%): gerar prompt, chamar API, salvar trilha (se nível avancado/profissional)
- Etapa 6 (UNIFICAR, 95-100%): merge final, atualizar status = "concluído"
- Progresso DEVE ser atualizado em `book_task.progresso` após cada etapa
- Etapa atual DEVE ser salva em `book_task.etapa_atual`
- Erros DEVE ser capturados e salvos em `book_task.erro` (não lançar exceção não tratada)
- Task DEVE atualizar `livro.status` para "concluído" ou "falhou"
- Task DEVE respeitar status "pausado" (parar entre etapas se pausado)

## Subtarefas
- [ ] Criar `backend/app/celery_tasks/process_book.py` com task `process_book`
- [ ] Implementar etapa 1: PDF_PROCESSING (extrair, salvar páginas)
- [ ] Implementar etapa 2: IA_ANALYSIS (personagens, normalização, perfil)
- [ ] Implementar etapa 3: VOICE_ASSIGNMENT (matching de vozes)
- [ ] Implementar etapa 4: AUDIO_PRODUCTION (TTS por personagem)
- [ ] Implementar etapa 5: MUSICGEN (trilha sonora, condicional)
- [ ] Implementar etapa 6: UNIFICAR (merge final, atualizar status)
- [ ] Implementar verificação de status "pausado" entre etapas
- [ ] Implementar captura e salvamento de erros em book_task.erro
- [ ] Implementar atualização de progresso (0-100%)

## Detalhes de Implementação

### Pipeline baseado no TechSpec
- Ver seção "Fluxo de Dados — Celery Pipeline" do TechSpec (6 etapas detalhadas)
- Ver seção "Sequenciamento de Desenvolvimento — Ordem de Construção" do TechSpec (passo 11)

### Fluxo de progresso
- Cada etapa atualiza `book_task.progresso` e `book_task.etapa_atual`
- Progresso é lido pelo frontend via `GET /api/v1/livros/{id}/progresso` (task_10)

### Arquivos Relevantes
- `src/pas/Book/Rgn.Leitor.Book.pas` — Fluxo original `ProcessarBook`
- `src/pas/Book/Personagens/Rgn.Leitor.Book.Personagens.pas` — Pipeline original de personagens
- `src/pas/Book/Narrador/Rgn.Leitor.Book.Narrador.pas` — Pipeline original de narrador
- `src/pas/Book/Vozes/Rgn.Leitor.Book.Vozes.pas` — Pipeline original de vozes

### Arquivos Dependentes
- `backend/app/services/pdf_processor.py` (task_05) — Extrair texto
- `backend/app/services/ia_analyzer.py` (task_07) — Análise de personagens
- `backend/app/services/tts_engine.py` (task_08) — Produção de áudio
- `backend/app/services/musicgen.py` (task_09) — Trilha sonora
- `backend/app/models/book_task.py` (task_02) — Atualizar progresso
- `backend/app/models/livro.py` (task_02) — Atualizar status

### ADRs Relacionados
- [ADR-002: Stack Tecnológica](adrs/adr-002.md) — Define Celery como sistema de filas

## Entregáveis
- `process_book.py` com task Celery completa (6 etapas)
- Atualização de progresso em tempo real
- Tratamento de erros por etapa
- Respeito ao status "pausado" entre etapas
- Testes unitários: cada etapa do pipeline
- Testes de integração: pipeline completo com mocks

## Testes
- Testes unitários:
  - [ ] Etapa 1 extrai texto e salva páginas corretamente
  - [ ] Etapa 2 processa personagens, normaliza nomes e define perfis
  - [ ] Etapa 3 faz matching de vozes por gênero/idade
  - [ ] Etapa 4 gera áudio para todos os personagens
  - [ ] Etapa 5 gera trilha sonora apenas se nível == "avancado" ou "profissional"
  - [ ] Etapa 6 unifica áudio e atualiza status para "concluído"
  - [ ] Se etapa 4 falha, status é atualizado para "falhou" com mensagem de erro
  - [ ] Se livro está "pausado" entre etapas, task para e retoma ao receber "retomar"
  - [ ] Progresso é atualizado corretamente (0→100%)
- Testes de integração:
  - [ ] Pipeline completo com PDF de teste (todos os serviços mockados)
  - [ ] Pipeline completo com IA mockada e TTS mockada

## Critérios de Sucesso
- Todos os testes passando
- Cobertura de testes >= 80%
- Pipeline de 6 etapas executado corretamente
- Progresso atualizado em tempo real
- Erros capturados e salvos em book_task
- Status "pausado" respeitado entre etapas
