---
status: pending
title: Testes unitários — cobertura de services e utilitários
type: test
complexity: high
dependencies:
  - task_05, task_07, task_08, task_09
---

# Tarefa 13: Testes unitários — cobertura de services e utilitários

## Visão Geral
Implementar testes unitários para todos os services (PDF Processor, IA Analyzer, TTSEngine, MusicGen) e utilitários (auth, parsing) com cobertura mínima de 80%. Usar `pytest` + `pytest-asyncio` + `factory_boy` com mocks para chamadas HTTP externas.

<critical>
- SEMPRE LEIA o PRD e o TechSpec antes de começar
- CONSULTE O TECHSPEC para detalhes de implementação — não duplique aqui
- FOQUE NO "O QUÊ" — descreva o que precisa ser feito, não como
- MINIMIZE CÓDIO — mostre código só para ilustrar estrutura atual ou áreas problemáticas
- TESTES OBRIGATÓRIOS — toda tarefa DEVE incluir testes nos entregáveis
</critical>

<requirements>
- Cobertura mínima de 80% em todos os módulos testados
- Todos os testes DEVE usar mocks para chamadas HTTP externas (httpx.AsyncClient)
- PDF Processor DEVE ser testado com PDFs de fixture (arquivos reais)
- IA Analyzer DEVE mockar httpx para todas as chamadas LLM
- TTSEngine DEVE mockar httpx para chamada TTS API
- MusicGen DEVE mockar httpx para chamada MusicGen API
- Auth DEVE mockar bcrypt para todos os testes de hash
- pytest.ini DEVE configurar `asyncio_mode = auto` para testes async
- factory_boy DEVE criar factories para todos os models

## Subtarefas
- [ ] Configurar `tests/` com `conftest.py` (fixtures globais, factories)
- [ ] Criar `pytest.ini` com configuração de pytest e pytest-asyncio
- [ ] Criar `tests/test_services/test_pdf_processor.py` — testes de extração
- [ ] Criar `tests/test_services/test_ia_analyzer.py` — testes de LLM client
- [ ] Criar `tests/test_services/test_tts_engine.py` — testes de chunking e TTS
- [ ] Criar `tests/test_services/test_musicgen.py` — testes de geração de trilha
- [ ] Criar `tests/test_services/test_auth_service.py` — testes de hash e validação
- [ ] Criar `tests/test_schemas/` — testes de validação de Pydantic schemas
- [ ] Criar fixtures de PDFs, EPUBs e TXTs para testes
- [ ] Configurar coverage (pytest-cov) com mínimo de 80%
- [ ] Verificar cobertura e adicionar testes faltantes

## Detalhes de Implementação

### Framework baseado no TechSpec
- Ver seção "Abordagem de Testes" do TechSpec para componentes a testar e mocks necessários
- `pytest` + `pytest-asyncio` + `factory_boy` para unit tests
- `pytest-postgresql` para integration tests (task_14)

### Casos de borda do TechSpec
- Ver seção "Casos de borda" do TechSpec: PDF vazio, PDF > 1000 páginas, resposta JSON inválida, TTS erro 500, etc.

### Arquivos Relevantes
- `unittest/pas/TestRgn.Leitor.IA.Http.pas` — Referenciar testes existentes (DUnit) como contexto
- `src/dpr/Win32/Debug/extrair_pdf.py` — Script original de extração; criar fixtures baseadas nele

### Arquivos Dependentes
- `backend/app/services/pdf_processor.py` (task_05)
- `backend/app/services/ia_analyzer.py` (task_07)
- `backend/app/services/tts_engine.py` (task_08)
- `backend/app/services/musicgen.py` (task_09)

### ADRs Relacionados
- [ADR-002: Stack Tecnológica](adrs/adr-002.md) — Define stack tecnológica incluindo pytest para testes

## Entregáveis
- `pytest.ini` configurado com pytest-asyncio
- `conftest.py` com fixtures globais e factories (factory_boy)
- Testes para PDF Processor (mínimo 15 casos)
- Testes para IA Analyzer (mínimo 15 casos)
- Testes para TTSEngine (mínimo 10 casos)
- Testes para MusicGen (mínimo 6 casos)
- Testes para Auth Service (mínimo 5 casos)
- Testes de validação de schemas (mínimo 5 casos)
- Cobertura geral >= 80%
- `pytest` passa em 0 erros

## Testes
- Testes unitários PDF Processor:
  - [ ] PDF de 10 páginas extrai 10 páginas com texto
  - [ ] PDF vazio retorna lista vazia
  - [ ] PDF com > 1000 páginas não estoura memória
  - [ ] EPUB com 5 capítulos extrai 5 capítulos
  - [ ] TXT UTF-8 com acentos extrai corretamente
  - [ ] TXT vazio retorna lista vazia
  - [ ] Arquivo corrompido retorna erro descritivo
  - [ ] Formato inválido (.zip) retorna erro "formato não suportado"
  - [ ] Arquivo > 50MB retorna erro "tamanho excedido"
- Testes unitários IA Analyzer:
  - [ ] Parser extrai JSON de resposta de IA
  - [ ] Parser extrai texto "nome|genero|idade" de IA
  - [ ] Fallback cloud → local aciona em RateLimitError
  - [ ] Fallback cloud → local aciona em ConnectionError
  - [ ] Retry 3x com backoff exponencial (1s, 2s, 4s)
  - [ ] Retry 2x para local com backoff (1s, 2s)
  - [ ] Timeout 60s para cloud
  - [ ] Timeout 120s para local
- Testes unitários TTSEngine:
  - [ ] Chunking de texto por sentença (ponto final)
  - [ ] Chunking de texto longo gera múltiplos chunks
  - [ ] Chunking sem "." divide em limites de palavra
  - [ ] "." isolado não é enviado para TTS (substituído por ",")
  - [ ] TTS API mockada retorna caminho de arquivo
  - [ ] TTS API indisponível retry 3x
- Testes unitários MusicGen:
  - [ ] Prompt atmosférico é gerado em inglês
  - [ ] MusicGen API mockada retorna caminho de arquivo
  - [ ] Duração > 300s gera trilha por página
  - [ ] Duração <= 300s gera trilha única
- Testes unitários Auth:
  - [ ] bcrypt.hashpw gera hash válido
  - [ ] bcrypt.checkpw valida senha correta
  - [ ] bcrypt.checkpw rejeita senha errada
  - [ ] Primeiro acesso cria admin
  - [ ] Segundo acesso retorna 403

## Critérios de Sucesso
- Todos os testes passando
- Cobertura de testes >= 80% em todos os módulos
- Nenhum teste com chamadas HTTP reais (todos mockados)
- Todos os casos de borda do TechSpec cobertos
- `pytest --cov` mostra cobertura >= 80%
