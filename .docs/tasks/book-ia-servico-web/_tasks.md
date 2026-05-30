# Book-IA — Lista de Tarefas

## Tarefas

|| # | Título | Status | Complexidade | Dependências |
||---|--------|--------|--------------|--------------|
|| 01 | Scaffolding do projeto Python | completed | low | — |
|| 02 | Modelos de dados e migrations com SQLAlchemy + Alembic | completed | medium | task_01 |
|| 03 | Autenticação e sessão com cookies HTTP-only | completed | medium | task_02 |
|| 04 | API de configurações (CRUD de APIs + teste de conexão) | completed | medium | task_02 |
|| 05 | PDF Processor com suporte multi-formato (PDF/EPUB/TXT) | completed | medium | task_01 |
|| 06 | Celery + Redis — worker, health check, estrutura de tasks | completed | medium | task_02 |
|| 07 | IA Analyzer — LLM client com fallback cloud/local, retry e parsing | completed | high | task_02, task_04 |
|| 08 | TTSEngine — chunking de texto, chamada TTS API, conversão WAV→MP3 | completed | high | task_02, task_04, task_06 |
|| 09 | MusicGen — geração de prompt, chamada API, salvamento de trilha | completed | high | task_02, task_04, task_06 |
|| 10 | API de livros — upload, fila, progresso, pausa/retomar/cancelar, download | completed | high | task_02, task_05, task_06, task_07, task_08, task_09 |
|| 11 | Celery task process_book — orquestração completa do pipeline | completed | high | task_07, task_08, task_09, task_10 |
|| 12 | Frontend HTMX — dashboard, login, upload, detalhes, configurações | completed | medium | task_03, task_04, task_10 |
|| 13 | Testes unitários — cobertura de services e utilitários | completed | high | task_05, task_07, task_08, task_09 |
|| 14 | Testes de integração — pipeline completo, auth, fila, HTMX | completed | high | task_10, task_11, task_12 |
|| — | **Fase 2 — Áudio Completo** | — | — | — |
|| 15 | Revisão guiada de personagens — modelo, endpoints, template HTMX | completed | high | task_06, task_07 |
|| 16 | Exportação por capítulos — modelo, pipeline, frontend | new | high | task_05, task_09 |
