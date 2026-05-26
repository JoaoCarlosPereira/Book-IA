# Book-IA — Serviço Web de Conversão de PDF em Audiobook com IA

Serviço web em Python para processamento de livros em PDF (ou EPUB/TXT) com geração de audiobooks enriquecidos com Inteligência Artificial, incluindo múltiplas vozes e trilha sonora contextual.

## Tecnologias

- **Backend:** FastAPI (Python 3.13)
- **Frontend:** HTMX + Jinja2 templates
- **Banco de dados:** PostgreSQL 16 + SQLAlchemy 2.0 + Alembic
- **Filas:** Celery + Redis
- **Deploy:** Docker Compose

## Requisitos

- Docker e Docker Compose instalados
- Python 3.13+ (para execução local)

## Execução com Docker Compose

```bash
# Iniciar todos os serviços
docker-compose up -d

# Verificar status
docker-compose ps

# Acessar o dashboard
# http://localhost:8000

# Acessar a documentação Swagger
# http://localhost:8000/docs

# Ver logs
docker-compose logs -f backend
docker-compose logs -f celery-worker
```

### Parar e limpar

```bash
# Parar todos os serviços
docker-compose down

# Parar e remover volumes (perde dados do banco)
docker-compose down -v
```

## Execução Local

```bash
# Criar ambiente virtual
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux/macOS

# Instalar dependências
pip install -r backend/requirements.txt

# Configurar variáveis de ambiente (copiar .env.example)
copy .env.example .env        # Windows
cp .env.example .env          # Linux/macOS

# Iniciar serviços externos
docker-compose up postgres redis -d

# Executar migrations
cd backend
alembic upgrade head

# Iniciar o backend
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

# Iniciar o worker Celery (em outro terminal)
celery -A celery_worker worker --loglevel=info
```

## Estrutura do Projeto

```
Book-IA/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app entry point
│   │   ├── config.py          # Settings (env vars)
│   │   ├── db.py              # SQLAlchemy engine
│   │   ├── deps.py            # Dependency injection
│   │   ├── api/v1/            # API routers
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/          # Business logic
│   │   └── templates/         # Jinja2 templates
│   ├── celery_worker.py       # Celery app
│   ├── requirements.txt       # Python dependencies
│   ├── alembic.ini            # Alembic config
│   └── alembic/               # Database migrations
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

## Endpoints

| Endpoint | Descrição |
|---|---|
| `GET /health` | Health check |
| `GET /docs` | Documentação Swagger (UI) |
| `GET /redoc` | Documentação ReDoc |

## Testes

```bash
# Executar todos os testes
pytest tests/

# Testes com cobertura
pytest tests/ --cov=backend.app --cov-report=term-missing
```

## Licença

Privado — Book-IA Project
