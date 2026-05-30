# Book-IA — Serviço Web de Conversão de PDF em Audiobook com IA

Serviço web em Python para processamento de livros em PDF (ou EPUB/TXT) com geração de audiobooks enriquecidos com Inteligência Artificial, incluindo múltiplas vozes e trilha sonora contextual.

## Tecnologias

- **Backend:** FastAPI (Python 3.13)
- **Frontend:** HTMX + Jinja2 templates
- **Banco de dados:** PostgreSQL 16 + SQLAlchemy 2.0 + Alembic
- **Filas:** Celery + Redis
- **Deploy:** Docker Compose

## Requisitos

- Docker e Docker Compose instalados (Ubuntu 20.04+)
- Pelo menos 2 GB de RAM disponível
- Python 3.13+ (para execução local)

---

## Instalação Rápida (Ubuntu)

### 1. Instalar Docker e Docker Compose

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin
sudo usermod -aG docker $USER
newgrp docker   # ou faça logout/login para ativar
```

### 2. Instalar e rodar

```bash
chmod +x install.sh
sudo ./install.sh
```

O script automatiza:

- Construção e subida dos containers
- Aguardo automático do PostgreSQL e Redis
- Aplicação de migrations (Alembic)
- Criação do primeiro usuário administrador
- Verificação de status de todos os serviços

### 3. Com credenciais customizadas

```bash
sudo ./install.sh --login editora --senha 'MinhaSenhaSegura123'
```

### 4. Acessar

| Recurso | URL |
|---------|-----|
| Dashboard | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |

Credenciais padrão: `admin` / `admin123`

---

## Execução Manual (Docker Compose)

Se preferir controlar cada passo:

```bash
# 1. Construir e subir
docker compose up -d --build

# 2. Aplicar migrations
docker compose exec backend alembic upgrade head

# 3. Criar primeiro admin (executar apenas na primeira vez)
curl -X POST http://localhost:8000/api/v1/auth/setup \
  -F "login=admin" -F "senha=admin123"

# 4. Acessar http://localhost:8000
```

### Parar e limpar

```bash
# Parar serviços (dados preservados)
docker compose down

# Parar e remover volumes (perde dados do banco)
docker compose down -v
```

---

## Execução Local

```bash
# 1. Banco e fila
docker compose up postgres redis -d

# 2. Ambiente virtual
python3 -m venv venv
source venv/bin/activate

# 3. Dependências
pip install -r backend/requirements.txt

# 4. Migrations
cd backend
alembic upgrade head

# 5. Backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 6. Celery worker (outro terminal)
celery -A celery_worker worker --loglevel=info
```

---

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
├── install.sh                 # Script de instalação Ubuntu
├── Dockerfile
├── docker-compose.yml
├── docker-entrypoint.sh       # Entrypoint com migrations automáticas
├── .gitignore
└── README.md
```

---

## Endpoints

| Endpoint | Descrição |
|---|---|
| `GET /health` | Health check |
| `GET /docs` | Documentação Swagger (UI) |
| `GET /redoc` | Documentação ReDoc |
| `GET /health/redis` | Status do Redis |
| `GET /health/celery` | Status do Celery |

---

## Testes

```bash
# Todos os testes
pytest tests/

# Com cobertura
pytest tests/ --cov=backend.app --cov-report=term-missing

# Apenas unitários
pytest tests/ --ignore=tests/test_integration

# Apenas integração
pytest tests/test_integration/
```

---

## Dependências Externas para Audiobook Completo

Para gerar áudio (TTS) e trilha sonora (MusicGen), configure os serviços na UI em **Configurações**:

- **TTS API:** `http://<seu-host>:8001`
- **MusicGen API:** `http://<seu-host>:8002`
- **LLM:** Gemini, Ollama ou qualquer API compatível

Sem esses serviços, o sistema processa textos e lista livros, mas não gera áudio.

---

## Licença

Privado — Book-IA Project
