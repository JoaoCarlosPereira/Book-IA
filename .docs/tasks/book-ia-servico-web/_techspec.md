# TechSpec — Book-IA: Serviço Web de Conversão de PDF em Audiobook com IA

> **Versão:** 1.0
> **Data:** 2026-05-25
> **Status:** Rascunho para revisão

---

## Resumo Executivo

O Book-IA migra de um console Delphi monolítico para um **serviço web em Python** com backend FastAPI (API REST), frontend HTMX + Jinja2 (dashboard web), banco PostgreSQL com SQLAlchemy + Alembic, e filas assíncronas via Celery + Redis. A arquitetura segue o padrão de monorepo Python único: backend, templates, Celery workers e migrations no mesmo repositório, deploy via Docker Compose (4 containers: backend, celery worker, redis, postgres).

**Trade-off principal:** HTMX/Jinja2 vs React/SPA — escolhemos simplicidade e velocidade de desenvolvimento em troca de menor flexibilidade de frontend. A API REST completa (FastAPI + Swagger) garante que o frontend pode ser substituído por React/Next.js no futuro sem mudar o backend.

---

## Arquitetura do Sistema

### Visão dos Componentes

```
┌──────────────────────────────────────────────────────────────────┐
│                        Navegador do Usuário                       │
│  (HTMX calls via hx-get / hx-post, SSE para progresso)           │
└────────────┬─────────────────────────────────────────────────────┘
             │ HTTP (JSON + HTML partials)
             ▼
┌──────────────────────────────────────────────────────────────────┐
│  FastAPI (Port 8000)                                              │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────────┐ │
│  │ API Routers  │  │  Auth       │  │  Business Services       │ │
│  │ /livros      │  │  /auth      │  │  PDFProcessor            │ │
│  │ /config      │  │  (sessions) │  │  IAAnalyzer              │ │
│  │ /tasks       │  │             │  │  TTSEngine               │ │
│  └──────────────┘  └──────────────┘  │  MusicGen                │ │
│                                      └──────────┬────────────────┘ │
│                                                 │                  │
└─────────────────────────┬───────────────────────┼──────────────────┘
                          │                       │
             ┌────────────┘              ┌────────┘
             ▼                           ▼
┌─────────────────────┐       ┌──────────────────────┐
│  PostgreSQL         │       │  Celery Worker       │
│  (Port 5432)        │       │  (Redis broker)      │
│  • livro            │       │  • process_book()    │
│  • pagina           │       │  • call_llm()        │
│  • personagem       │       │  • call_tts()        │
│  • falas            │       │  • call_musicgen()   │
│  • arquivo          │       │  • merge_audio()     │
│  • api_config       │       │  • send_notification()│
│  • voz              │       └──────────────────────┘
│  • usuario          │
│  • book_task        │
│  • book_review      │
└─────────────────────┘
```

### Componentes e Responsabilidades

| Componente | Responsabilidade | Limites |
|---|---|---|
| **FastAPI (main.py)** | Entry point, mount routers, middleware (CORS, session, logging) | Não contém lógica de negócio |
| **API Routers** | Endpoints HTTP, validação de input, formatação de output | Não acessam DB diretamente — usam services |
| **Services** | Regras de negócio: PDF parsing, IA analysis, TTS, MusicGen | Não sabem sobre HTTP ou templates |
| **Models (SQLAlchemy)** | Definição de tabelas, relacionamentos, validações | Não sabem sobre FastAPI ou Celery |
| **Schemas (Pydantic)** | Validação de request/response bodies | Não sabem sobre models do DB |
| **Celery Worker** | Tasks assíncronas (processamento longo) | Não sabe sobre HTTP; acessa apenas DB e filesystem |
| **Templates (Jinja2 + HTMX)** | Renderização HTML com interatividade via HTMX | Não contém lógica de negócio |
| **Alembic** | Migrações de banco versionadas | Não roda em produção após schema consolidado |

### Fluxo de Dados — Upload de Livro

```
1. Usuário faz POST /api/v1/livros/upload (multipart/form-data)
2. FastAPI valida arquivo → salva PDF temporário
3. FastAPI salva registro em `livro` (status: "pendente")
4. FastAPI salva registro em `book_task` (status: "pendente")
5. FastAPI dispara Celery task: process_book.delay(livro_id)
6. FastAPI retorna 201 com link para acompanhamento (hx-target)
7. Celery worker executa pipeline completo (ver Fluxo abaixo)
8. Progresso atualizado em `book_task.progresso` (0–100%)
9. Frontend polla /api/v1/livros/{id}/progresso a cada 3s
10. Ao concluir, arquivo disponível em /api/v1/livros/{id}/download
```

### Fluxo de Dados — Celery Pipeline

```
Celery task: process_book(livro_id)
  │
  ├─→ 1. PDF_PROCESSING (0-10%)
  │     ├─ Extrair texto (PyMuPDF / ebooklib / TXT)
  │     ├─ Salvar páginas em `pagina`
  │     └─ Atualizar progresso
  │
  ├─→ 2. IA_ANALYSIS (10-40%)
  │     ├─ Analisar personagens (LLM call)
  │     ├─ Normalizar nomes (LLM call)
  │     ├─ Perfil de personagens (LLM calls)
  │     ├─ Perfil do narrador (LLM call)
  │     └─ Atualizar `personagem` e `falas`
  │
  ├─→ 3. VOICE_ASSIGNMENT (40-50%)
  │     ├─ Carregar vozes disponíveis de `voz`
  │     ├─ Matching por gênero/idade
  │     ├─ Atualizar `personagem.cdutoz_id`
  │     └─ Atualizar progresso
  │
  ├─→ 4. AUDIO_PRODUCTION (50-90%)
  │     ├─ Chunking de texto (TTSEngine)
  │     ├─ POST TTS API por chunk
  │     ├─ Download WAV → MP3
  │     ├─ Unificar por personagem
  │     ├─ Salvar caminhos em `arquivo`
  │     └─ Atualizar progresso
  │
  ├─→ 5. MUSICGEN (90-95%)  [se nível "avançado" ou "profissional"]
  │     ├─ Gerar prompt atmosférico (LLM)
  │     └─ POST MusicGen API → salvar trilha
  │
  └─→ 6. UNIFICAR (95-100%)
        ├─ Merge final (ffmpeg ou API merge)
        ├─ Atualizar `livro` status = "concluído"
        └─ Notificar usuário (SSE event ou polling)
```

---

## Design de Implementação

### Interfaces Principais

#### 1. Service de Processamento de PDF

```python
# app/services/pdf_processor.py

class DocumentType(str, Enum):
    PDF = "pdf"
    EPUB = "epub"
    TXT = "txt"

class PageExtractionResult(BaseModel):
    chapters: list[str]
    pages: list[Page]

class Page(BaseModel):
    numero: int
    texto: str
```

#### 2. Interface de Análise com IA

```python
# app/services/ia_analyzer.py

class IAProvider(str, Enum):
    CLOUD = "cloud"
    LOCAL = "local"

class CharacterProfile(BaseModel):
    nome: str
    genero: str  # "masculino" | "feminino" | "neutro"
    idade: str   # "crianca" | "adulto" | "idoso"

class IAAnalyzer:
    def __init__(self, provider: IAProvider, config: APIConfig): ...
    async def extrair_personagens(self, texto: str) -> list[CharacterProfile]: ...
    async def normalizar_nomes(self, personagens: list[CharacterProfile]) -> list[CharacterProfile]: ...
    async def definir_perfil(self, texto: str, personagem: str) -> CharacterProfile: ...
```

#### 3. Engine de TTS

```python
# app/services/tts_engine.py

class TTSEngine:
    def __init__(self, api_url: str, api_key: str | None): ...
    async def gerar_audio(self, texto: str, personagem: str) -> str:
        """Gera áudio e retorna caminho do arquivo."""
        chunks = self._chunkar_texto(texto, max_chars=180)
        arquivos = []
        for i, chunk in enumerate(chunks):
            wav_path = await self._post_to_api(chunk)
            mp3_path = await self._convert_to_mp3(wav_path)
            arquivos.append(mp3_path)
        return self._unificar_arquivos(arquivos)
    
    def _chunkar_texto(self, texto: str, max_chars: int = 180) -> list[str]: ...
```

### Modelos de Dados

#### Tabela `livro` (cabeçalho)

| Campo | Tipo | Restrições | Descrição |
|---|---|---|---|
| `id` | SERIAL | PK | Identificador |
| `titulo` | VARCHAR(500) | NOT NULL | Título do livro |
| `nome_arquivo` | VARCHAR(500) | NOT NULL | Nome original do arquivo |
| `tipo_documento` | VARCHAR(10) | NOT NULL | pdf / epub / txt |
| `nivel_producao` | VARCHAR(20) | NOT NULL | basico | avancado | profissional |
| `status` | VARCHAR(20) | NOT NULL | pendente | processando | concluido | falhou |
| `progresso` | INTEGER | DEFAULT 0 | 0-100 |
| `caminho_pdf` | VARCHAR(1000) | | Caminho no filesystem |
| `caminho_audio` | VARCHAR(1000) | | Audiobook final |
| `criado_em` | TIMESTAMP | DEFAULT NOW() | |
| `atualizado_em` | TIMESTAMP | DEFAULT NOW() | |
| `usuario_id` | INTEGER | FK → usuario.id | Quem enviou |

#### Tabela `pagina`

| Campo | Tipo | Restrições | Descrição |
|---|---|---|---|
| `id` | SERIAL | PK | |
| `livro_id` | INTEGER | FK → livro.id, NOT NULL | |
| `numero` | INTEGER | NOT NULL | Número da página |
| `texto` | TEXT | NOT NULL | Conteúdo textual |
| `processado` | BOOLEAN | DEFAULT FALSE | |

#### Tabela `personagem`

| Campo | Tipo | Restrições | Descrição |
|---|---|---|---|
| `id` | SERIAL | PK | |
| `livro_id` | INTEGER | FK → livro.id, NOT NULL | |
| `nome` | VARCHAR(200) | NOT NULL | Nome normalizado |
| `nome_original` | VARCHAR(200) | | Como apareceu no texto |
| `genero` | VARCHAR(20) | | masculino | feminino | neutro |
| `idade` | VARCHAR(20) | | crianca | adulto | idoso |
| `is_narrador` | BOOLEAN | DEFAULT FALSE | |
| `voz_id` | INTEGER | FK → voz.id | Voz atribuída |
| `criado_em` | TIMESTAMP | DEFAULT NOW() | |

#### Tabela `falas`

| Campo | Tipo | Restrições | Descrição |
|---|---|---|---|
| `id` | SERIAL | PK | |
| `livro_id` | INTEGER | FK → livro.id, NOT NULL | |
| `pagina_id` | INTEGER | FK → pagina.id | |
| `personagem_id` | INTEGER | FK → personagem.id | |
| `texto` | TEXT | NOT NULL | Texto da fala |
| `processado` | BOOLEAN | DEFAULT FALSE | TTS feito? |
| `arquivo_id` | INTEGER | FK → arquivo.id | Áudio gerado |

#### Tabela `arquivo`

| Campo | Tipo | Restrições | Descrição |
|---|---|---|---|
| `id` | SERIAL | PK | |
| `livro_id` | INTEGER | FK → livro.id, NOT NULL | |
| `tipo` | VARCHAR(20) | NOT NULL | pdf | wav | mp3 | trilha |
| `caminho` | VARCHAR(1000) | NOT NULL | Caminho no filesystem |
| `tamanho_bytes` | BIGINT | | |
| `criado_em` | TIMESTAMP | DEFAULT NOW() | |

#### Tabela `api_config`

| Campo | Tipo | Restrições | Descrição |
|---|---|---|---|
| `id` | SERIAL | PK | |
| `tipo` | VARCHAR(20) | NOT NULL | llm | tts | musicgen |
| `modo` | VARCHAR(10) | NOT NULL | cloud | local |
| `url` | VARCHAR(500) | NOT NULL | Endpoint da API |
| `token` | VARCHAR(500) | | Token de autenticação (criptografado) |
| `modelo` | VARCHAR(200) | | Nome do modelo (LLM) |
| `ativo` | BOOLEAN | DEFAULT TRUE | |
| `criado_em` | TIMESTAMP | DEFAULT NOW() | |

#### Tabela `voz`

| Campo | Tipo | Restrições | Descrição |
|---|---|---|---|
| `id` | SERIAL | PK | |
| `nome` | VARCHAR(200) | NOT NULL | Nome da voz |
| `genero` | VARCHAR(20) | NOT NULL | masculino | feminino | neutro |
| `idade` | VARCHAR(20) | NOT NULL | crianca | adulto | idoso |

#### Tabela `usuario`

| Campo | Tipo | Restrições | Descrição |
|---|---|---|---|
| `id` | SERIAL | PK | |
| `login` | VARCHAR(100) | UNIQUE, NOT NULL | Login |
| `senha_hash` | VARCHAR(255) | NOT NULL | bcrypt hash |
| `perfil` | VARCHAR(20) | DEFAULT "usuario" | admin | usuario | revisor | espectador |
| `criado_em` | TIMESTAMP | DEFAULT NOW() | |

#### Tabela `book_task` (fila de processamento)

| Campo | Tipo | Restrições | Descrição |
|---|---|---|---|
| `id` | SERIAL | PK | |
| `livro_id` | INTEGER | FK → livro.id, NOT NULL | |
| `status` | VARCHAR(20) | NOT NULL | pendente | em_analise | em_producao | pausado | concluido | falhou | cancelado |
| `prioridade` | INTEGER | DEFAULT 5 | 1=mais alta, 10=menor |
| `progresso` | INTEGER | DEFAULT 0 | 0-100 |
| `etapa_atual` | VARCHAR(100) | | Descrição da etapa atual |
| `erro` | TEXT | | Mensagem de erro (se falhou) |
| `criado_em` | TIMESTAMP | DEFAULT NOW() | |
| `atualizado_em` | TIMESTAMP | DEFAULT NOW() | |

#### Tabela `book_review` (Fase 3)

| Campo | Tipo | Restrições | Descrição |
|---|---|---|---|
| `id` | SERIAL | PK | |
| `livro_id` | INTEGER | FK → livro.id, NOT NULL | |
| `usuario_id` | INTEGER | FK → usuario.id | Revisor |
| `personagem_id` | INTEGER | FK → personagem.id | |
| `acao` | VARCHAR(20) | NOT NULL | aprovado | reprovado | modificado |
| `observacao` | TEXT | | |
| `criado_em` | TIMESTAMP | DEFAULT NOW() | |

### Endpoints de API

#### Autenticação

| Método | Caminho | Descrição | Request | Response |
|---|---|---|---|---|
| GET | `/api/v1/auth/login` | Exibe tela de login | — | HTML template |
| POST | `/api/v1/auth/login` | Realiza login | `{login, senha}` | 302 redirect (sucesso) ou 401 (falha) |
| POST | `/api/v1/auth/logout` | Encerra sessão | — | 302 para /login |
| POST | `/api/v1/auth/setup` | Configuração inicial (primeiro acesso) | `{login, senha}` | 302 para /dashboard |

#### Livros (Pipeline)

| Método | Caminho | Descrição | Request | Response |
|---|---|---|---|---|
| POST | `/api/v1/livros/upload` | Upload de PDF/EPUB/TXT | multipart/form-data | 201 `{id, status: "pendente"}` |
| GET | `/api/v1/livros` | Lista livros na fila | Query: `status, pagina, por_pagina` | JSON array |
| GET | `/api/v1/livros/{id}` | Detalhes do livro | — | JSON com status, progresso, personagens |
| GET | `/api/v1/livros/{id}/progresso` | Progresso atual | — | `{progresso, etapa, status}` |
| POST | `/api/v1/livros/{id}/pausar` | Pausa processamento | — | 200 `{status: "pausado"}` |
| POST | `/api/v1/livros/{id}/retomar` | Retoma processamento | — | 200 `{status: "processando"}` |
| POST | `/api/v1/livros/{id}/cancelar` | Cancela livro | — | 200 `{status: "cancelado"}` |
| POST | `/api/v1/livros/{id}/reordenar` | Muda prioridade | `{prioridade: 1}` | 200 `{prioridade: 1}` |
| GET | `/api/v1/livros/{id}/download` | Download do audiobook | — | Arquivo MP3 |
| DELETE | `/api/v1/livros/{id}` | Remove livro e arquivos | — | 204 |

#### Configurações de API

| Método | Caminho | Descrição | Request | Response |
|---|---|---|---|---|
| GET | `/api/v1/configuracoes/apis` | Lista APIs configuradas | — | JSON array |
| POST | `/api/v1/configuracoes/apis` | Cria/Atualiza API | `{tipo, modo, url, token, modelo}` | 201 JSON |
| DELETE | `/api/v1/configuracoes/apis/{id}` | Remove configuração | — | 204 |
| POST | `/api/v1/configuracoes/apis/{id}/testar` | Testa conexão | — | `{conectado: true, latencia_ms: 120}` |

#### Revisão de Personagens (Fase 2)

| Método | Caminho | Descrição | Request | Response |
|---|---|---|---|---|
| GET | `/api/v1/livros/{id}/personagens` | Lista personagens | — | JSON array com falas |
| PUT | `/api/v1/livros/{id}/personagens/{pid}` | Atualiza personagem | `{nome, genero, idade, voz_id}` | 200 JSON |
| DELETE | `/api/v1/livros/{id}/personagens/{pid}` | Remove personagem | — | 204 |
| POST | `/api/v1/livros/{id}/aprovar` | Aprova e inicia produção | — | 202 `{status: "em_producao"}` |

### Modelos Pydantic (Exemplos)

```python
# app/schemas/livro.py

class LivroCreate(BaseModel):
    nome_arquivo: str
    tipo_documento: DocumentType
    nivel_producao: Literal["basico", "avancado", "profissional"]

class LivroResponse(BaseModel):
    id: int
    titulo: str
    status: str
    progresso: int
    nivel_producao: str
    criado_em: datetime
    
    class Config:
        from_attributes = True

class LivroProgresso(BaseModel):
    progresso: int
    etapa: str
    status: str
```

---

## Pontos de Integração

### Integração com Serviços de IA

| Serviço | Endpoint | Autenticação | Retry | Timeout |
|---|---|---|---|---|
| **LLM (cloud)** | URL configurável (padrão: Gemini API) | Bearer token | 3 tentativas, backoff exponencial | 60s |
| **LLM (local)** | URL configurável (padrão: Ollama) | Nenhum | 2 tentativas | 120s |
| **TTS** | URL configurável (padrão: localhost:8001) | Bearer token (opcional) | 3 tentativas, backoff exponencial | 120s |
| **MusicGen** | URL configurável (padrão: localhost:8002) | Bearer token (opcional) | 3 tentativas, backoff exponencial | 180s |

### Estratégia de Fallback (LLM)

```python
async def _chamar_llm(self, prompt: str) -> str:
    """Tenta provider cloud primeiro, fallback para local."""
    try:
        return await self._provider_cloud(prompt)
    except (RateLimitError, ConnectionError) as e:
        logger.warning(f"Cloud falhou ({e}), tentando local...")
        return await self._provider_local(prompt)
```

### Tratamento de Erros

- **API externa indisponível:** retry 3x com backoff (1s, 2s, 4s). Após falha, marca tarefa como `falhou` com mensagem de erro em `book_task.erro`.
- **Timeout:** cada chamada tem timeout configurável. Timeout aciona retry + fallback.
- **Memória insuficiente:** Celery task com `max_retries=0` e sinal `SIGTERM` para cleanup de arquivos temporários.

---

## Análise de Impacto

| Componente | Tipo de Impacto | Descrição e Risco | Ação Necessária |
|---|---|---|---|
| `extrair_pdf.py` (Python) | **Modificado** | Script atual é chamado por Delphi via subprocess. No novo sistema, será integrado como módulo Python direto. | Migrar para `app/services/pdf_processor.py` |
| `Rgn.Leitor.IA.Http.pas` | **Depreciado** | HTTP client para LLM será reimplementado em Python (asyncio/httpx). | Novo código em `app/services/ia_analyzer.py` |
| `Rgn.Leitor.Book.Personagens.pas` | **Depreciado** | Lógica de extração de personagens. Será reimplementada. | Novo código em `app/services/ia_analyzer.py` |
| `Rgn.Leitor.Book.Vozes.pas` | **Depreciado** | Lógica de TTS e chunking. Será reimplementada. | Novo código em `app/services/tts_engine.py` |
| `Rgn.Leitor.Book.VozesHttp.pas` | **Depreciado** | HTTP client para TTS/MusicGen. Será reimplementada. | Novo código em `app/services/tts_engine.py` e `app/services/musicgen.py` |
| `DAO.Leitor.Book.pas` | **Depreciado** | DAO Delphi. Substituído por SQLAlchemy models + Alembic. | Novo código em `app/models/` |
| `Rgn.Sistema.ThreadFactory.pas` | **Substituído** | OTL threads do Delphi. Substituído por Celery. | Celery tasks em `celery_worker.py` |
| Banco PostgreSQL | **Novo** | Esquema recriado com SQLAlchemy + Alembic. | Criar migrations em `alembic/versions/` |
| Sistema de arquivos | **Novo** | Pastas configuráveis para PDFs e áudios. | Configurar paths via环境变量 |

---

## Abordagem de Testes

### Testes Unitários

**Framework:** `pytest` + `pytest-asyncio` + `factory_boy`

**Componentes a testar:**

| Componente | O Testar | Mocks Necessários |
|---|---|---|
| `pdf_processor` | Extração de texto PDF/EPUB/TXT | Nenhum (testar com PDFs de fixture) |
| `ia_analyzer` | Chamada LLM, parsing de resposta, retry | `httpx.AsyncClient` mockado |
| `tts_engine` | Chunking de texto, fallback de separação | `httpx.AsyncClient` mockado |
| `musicgen` | Geração de prompt, chamada API | `httpx.AsyncClient` mockado |
| `auth` | Hash de senha, validação, sessão | `bcrypt` mockado |
| `pdf_processor._chunkar_texto` | Separação em chunks de 180 chars | Nenhum |
| `ia_analyzer._parse_personagens` | Parsing de resposta IA (JSON/texto) | Nenhum |

**Casos de borda:**
- PDF com 0 páginas (arquivo vazio)
- PDF com > 1000 páginas (memory management)
- Texto sem personagens identificáveis
- API LLM retornando JSON inválido
- TTS retornando erro 500
- Arquivo corrompido ou formato inválido

### Testes de Integração

**Framework:** `pytest` + `TestClient` (FastAPI) + `pytest-postgresql`

**Cenários:**

| Teste | Componentes | Dependências |
|---|---|---|
| Upload → processamento → download | FastAPI + Celery + PostgreSQL | Container PostgreSQL temporário |
| Login → sessão → acesso protegido | Auth + Session | Nenhum |
| Configuração API → teste de conexão | API config + HTTP | Nenhum |
| Fila com múltiplos livros | Celery + PostgreSQL | Container Redis temporário |
| Pausar/retomar/cancelar task | Celery + book_task | Container PostgreSQL |
| Upload de EPUB e TXT | PDF processor | Nenhum |

**Setup:** Docker Compose com PostgreSQL e Redis em containers efêmeros para testes.

---

## Sequenciamento de Desenvolvimento

### Ordem de Construção

1. **Scaffolding do projeto** — Estrutura de pastas, `requirements.txt`, `Dockerfile`, `docker-compose.yml`, `.gitignore`. **Sem dependências.**
2. **Configuração do banco** — SQLAlchemy models + Alembic migrations. Criar schema completo. **Depende de: 1.**
3. **Autenticação** — Model `usuario`, endpoints de login/logout/setup, session middleware, decorators de proteção. **Depende de: 2.**
4. **API de configurações** — CRUD de `api_config`, endpoint de teste de conexão. **Depende de: 2.**
5. **PDF Processor** — `pdf_processor.py` com suporte a PDF/EPUB/TXT. **Depende de: 1.**
6. **Celery + Redis** — Configuração do worker, health check, estrutura de tasks. **Depende de: 1, 2.**
7. **IA Analyzer** — LLM client com fallback cloud/local, retry, parsing de respostas. **Depende de: 1, 4.**
8. **TTSEngine** — Chunking de texto, chamada TTS API, conversão WAV→MP3. **Depende de: 1, 4, 6.**
9. **MusicGen** — Geração de prompt, chamada API, salvamento de trilha. **Depende de: 1, 4, 6.**
10. **API de livros (endpoints)** — Upload, fila, progresso, pausa/retomar/cancelar, download. **Depende de: 2, 5, 6, 7, 8, 9.**
11. **Celery task `process_book`** — Orquestração do pipeline completo. **Depende de: 7, 8, 9, 10.**
12. **Frontend (HTMX templates)** — Dashboard, upload, lista de livros, detalhes, configurações. **Depende de: 3, 4, 10.**
13. **Testes unitários** — Cobertura de services e utilitários. **Depende de: 5, 7, 8, 9.**
14. **Testes de integração** — Pipeline completo, auth, fila. **Depende de: 10, 11, 12.**

### Dependências Técnicas

| Dependência | Status | Bloqueante para |
|---|---|---|
| **PostgreSQL instalado e acessível** | Deve ser provisionado | Passos 2, 3, 6 |
| **Redis instalado e acessível** | Deve ser provisionado | Passo 6 |
| **APIs de IA configuradas (LLM, TTS, MusicGen)** | Configuração do usuário | Passos 4, 7, 8, 9 |
| **ffmpeg instalado** | Dependência de sistema | Passo 8 (conversão WAV→MP3) |
| **Python 3.13+** | Deve estar disponível | Todos os passos |

---

## Design da Interface (Jinja2 Templates + HTMX + Pac-Man Tech Theme)

### Estrutura de Templates

```
templates/
├── base.html              # Layout principal: navbar, canvas pacman, footer
├── login.html             # Tela de autenticação
├── setup.html             # Configuração inicial de admin (primeiro acesso)
├── dashboard.html         # Página inicial: visão geral da fila
├── partials/
│   ├── livro_list.html    # Lista de livros (renderizado via HTMX para dashboard)
│   ├── livro_card.html    # Card individual de livro na fila
│   ├── progresso.html     # Barra de progresso (atualizada via polling)
│   └── status_badge.html  # Badge de status (pendente, processando, etc.)
└── livro/
    ├── upload.html        # Formulário de upload de PDF/EPUB/TXT
    ├── detail.html        # Detalhes do livro com tabs (páginas, personagens, áudio)
    ├── review.html        # Revisão de personagens (Fase 2)
    └── configuracoes.html # Painel de configuração de APIs
```

### Integração com Design System Pac-Man Tech

Os templates reutilizam os assets da pasta `design/`:

| Asset | Uso |
|---|---|
| `design/css/styles.css` | Estilos base Bootstrap + customizações do tema |
| `design/css/responsive-fixes.css` | Correções responsivas |
| `design/js/scripts.js` | Canvas animado Pac-Man (fundo) |
| `design/css/styles.css :root` | Cores: `--bs-primary: #34d3ff`, `--bs-secondary: #ffd166`, `--bs-body-bg: #08101c` |

**Adaptação necessária:** Os templates do Book-IA usam os componentes do design system (cards, navbar, badges, gradientes) como base, adaptando-os para a interface de dashboard (listas, formulários, progresso) ao invés de páginas de portfolio.

### Páginas do Dashboard

#### Login (`login.html`)
- Card central com glassmorphism (`rgba(7, 15, 28, 0.78)` + `backdrop-filter: blur(14px)`).
- Campos: login (texto), senha (password).
- Botão: `.btn-primary` (gradiente ciano).
- Fundo: canvas Pac-Man animado.

#### Dashboard (`dashboard.html`)
- Hero section com `.text-gradient` para título "Book-IA".
- Grid de cards `.card.shadow.border-0.rounded-4` para cada livro na fila.
- Cada card usa `.feature.bg-primary.bg-gradient-primary-to-secondary` para ícone de status.
- Badge `.bg-gradient-primary-to-secondary` para prioridade.
- HTMX: `hx-get="/api/v1/livros"` com `hx-trigger="every 3s"` para polling de progresso.
- Upload: botão `.btn-primary.btn-lg` que abre modal com `hx-post="/api/v1/livros/upload"`.

#### Detalle do Livro (`livro/detail.html`)
- Tabs Bootstrap com `.bg-gradient-primary-to-secondary` para ativo.
- Aba 1: informações gerais (título, status, progresso, nível de produção).
- Aba 2: personagens identificados (lista com cards inline).
- Aba 3: falas e áudio (tabela com status de cada fala).
- Botões de ação: pausar, retomar, cancelar, download — todos `.btn-outline-dark`.
- Progresso: barra Bootstrap com gradiente ciano→amarelo, atualizada via HTMX.

#### Configurações (`livro/configuracoes.html`)
- Formulário para cada API (LLM, TTS, MusicGen) com campos: tipo, modo (cloud/local), URL, token.
- Botão "Testar conexão" → chama endpoint `POST /api/v1/configuracoes/apis/{id}/testar` via HTMX.
- Resultado: badge verde (conectado) ou vermelho (falhou) injetado inline.

### Fluxos HTMX

| Interação | HTMX Attribute | Endpoint | Target |
|---|---|---|---|
| Atualizar lista de livros | `hx-get="/api/v1/livros"` `hx-trigger="every 3s"` | `GET /api/v1/livros` | `#livro-list` |
| Upload de arquivo | `hx-post="/api/v1/livros/upload"` `hx-encoding="multipart/form-data"` | `POST /api/v1/livros/upload` | `#livro-list` |
| Pausar livro | `hx-post="/api/v1/livros/{id}/pausar"` | `POST .../pausar` | `#livro-card-{id}` |
| Cancelar livro | `hx-post="/api/v1/livros/{id}/cancelar"` | `POST .../cancelar` | `#livro-card-{id}` |
| Testar conexão API | `hx-post="/api/v1/configuracoes/apis/{id}/testar"` | `POST .../testar` | `#test-result-{id}` |
| Reordenar prioridade | `hx-post="/api/v1/livros/{id}/reordenar"` `hx-include="#prioridade-select"` | `POST .../reordenar` | `#livro-card-{id}` |

### Componentes Customizados

```html
<!-- Status badge com gradiente -->
<div class="badge bg-gradient-primary-to-secondary text-white">
  <div class="text-uppercase">{{ status }}</div>
</div>

<!-- Feature icon para etapas do pipeline -->
<div class="feature bg-primary bg-gradient-primary-to-secondary text-white rounded-3 me-3">
  <i class="bi bi-file-earmark-pdf"></i>
</div>

<!-- Progress bar com gradiente Pac-Man -->
<div class="progress" style="height: 1rem; background: rgba(13, 24, 44, 0.92);">
  <div class="progress-bar bg-gradient-primary-to-secondary" 
       role="progressbar" 
       style="width: {{ progresso }}%" 
       aria-valuenow="{{ progresso }}">
  </div>
</div>
```

### Cores Semânticas para Status

| Status | Cor | Hex |
|---|---|---|
| Pendente | Cinza | `rgba(216, 231, 255, 0.4)` |
| Processando | Ciano | `#34d3ff` |
| Concluído | Verde | `#198754` |
| Falhou | Vermelho | `#dc3545` |
| Pausado | Amarelo | `#ffd166` |
| Cancelado | Cinza escuro | `#6c757d` |

## Monitoramento e Observabilidade

### Métricas (via Prometheus/Starlette middleware)

| Métrica | Tipo | Descrição |
|---|---|---|
| `bookia_books_total` | Counter | Total de livros processados por status |
| `bookia_processing_duration_seconds` | Histogram | Tempo do upload ao áudio concluído |
| `bookia_llm_requests_total` | Counter | Requests por LLM provider |
| `bookia_tts_duration_seconds` | Histogram | Tempo de geração de áudio |
| `bookia_queue_depth` | Gauge | Livros na fila (pendentes) |
| `bookia_celery_active_tasks` | Gauge | Tasks rodando no worker |

### Logs Estruturados

```python
import logging
import structlog

logger = structlog.get_logger()

# Exemplo de log estruturado
logger.info("livro_processando", 
    livro_id=livro.id,
    titulo=livro.titulo,
    etapa="ia_analise",
    pagina_atual=42,
    total_paginas=350
)
```

**Campos obrigatórios em todos os logs:** `timestamp`, `level`, `event`, `livro_id` (se aplicável).

### Health Checks

| Endpoint | Verifica |
|---|---|
| `GET /health` | FastAPI running + PostgreSQL conectada |
| `GET /health/redis` | Redis broker acessível |
| `GET /health/celery` | Celery worker responde |

### Alertas

| Alerta | Condição | Nível |
|---|---|---|
| Task falhou | `book_task.status = "falhou"` | Warning |
| Queue backlog | > 10 livros pendentes > 1 hora | Warning |
| API indisponível | 3 tentativas consecutivas falhando | Error |
| Espaço em disco | < 5 GB livre no volume de áudio | Critical |
| Worker parado | Celery heartbeat sem resposta > 5 min | Critical |

---

## Considerações Técnicas

### Decisões-Chave

**Decisão:** Celery + Redis para filas assíncronas.
**Justificativa:** O pipeline de processamento (IA + TTS + MusicGen) é intensivo em I/O e demorado (minutos a horas). Celery oferece retry automático, monitoramento (Flower), scale horizontal e persistência de tasks.
**Trade-offs:** Adiciona Redis como dependência de infraestrutura. Overhead de deployment maior que threading simples.
**Alternativas rejeitadas:** 
- `asyncio` nativo do Python: não oferece persistência de tasks nem retry automático.
- RQ (Redis Queue): mais simples mas menos maduro e sem monitoramento visual integrado.

**Decisão:** HTMX + Jinja2 para frontend.
**Justificativa:** O dashboard é CRUD-centric (lista, detalhes, upload, configurações). HTMX resolve todas as interações necessárias com partial renders, eliminando a complexidade de um SPA.
**Trade-offs:** Frontend acoplado ao backend. Se precisar de app mobile no futuro, será necessário um frontend JS separado.
**Alternativas rejeitadas:** React/Vite (mais complexo), Vue.js (ecossistema menor), Streamlit (limitado em customização).

**Decisão:** PostgreSQL com SQLAlchemy ORM + Alembic.
**Justificativo:** PostgreSQL é robusto para concorrência e textos longos. SQLAlchemy 2.0 com estilo declarativo é o padrão da indústria Python. Alembic traz versionamento (inexistente no Delphi).
**Trade-offs:** Curva de aprendizado para equipe vinda do Delphi. SQLAlchemy é mais verboso que o Delphi DAO.
**Alternativas rejeitadas:** Django ORM (menos flexível), raw SQL (sem versionamento), SQLite (não suporta Celery bem).

### Riscos Conhecidos

| Risco | Probabilidade | Mitigação |
|---|---|---|
| PyMuPDF/ebooklib conflitarem em dependências (C libs) | Média | Ambiente Python isolado (venv), pin de versões |
| Redis falhar durante processamento | Baixa | Health check; Celery com `broker_connection_retry_on_startup=True` |
| Espaço em disco cheio (PDFs + áudios) | Média | Monitoramento de disk space; limpeza automática de temporários; configuração de retenção |
| API de IA fora do ar durante processamento | Alta | Retry + fallback cloud/local + marcação de tarefa como "falhou" para retry manual |
| Livro muito grande (> 1000 páginas) excedendo memória | Baixa | Processamento pagina a pagina; limites de memória no Celery worker |

---

## Registros de Decisão de Arquitetura

- [ADR-001: Estratégia de Entrega Faseada com MVP Vertical](adrs/adr-001.md) — Entregar o sistema em 3 fases, cada uma com valor próprio, começando pelo pipeline essencial.
- [ADR-002: Stack Tecnológica — FastAPI + HTMX + PostgreSQL + Celery/Redis](adrs/adr-002.md) — FastAPI para API, HTMX para frontend, Celery/Redis para filas, PostgreSQL para banco.
- [ADR-003: Modelos de Dados — Recriação do Esquema PostgreSQL com SQLAlchemy](adrs/adr-003.md) — Recriar esquema do zero com nomeclatura Python-friendly e migrations versionadas.
- [ADR-004: Arquitetura do Sistema — Monorepo Python com FastAPI + HTMX + Celery](adrs/adr-004.md) — Backend, templates, Celery e migrations no mesmo repositório, deploy via Docker Compose.
