#!/bin/bash
# Entrypoint para o Docker — aplica migrações e inicia o servidor

set -e

echo "Executando migrações Alembic..."
alembic upgrade head

echo "Iniciando servidor Uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
