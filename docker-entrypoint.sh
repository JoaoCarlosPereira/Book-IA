#!/bin/bash
# Entrypoint para o Docker - aplica migraes, cria admin padrao e inicia o servidor.
# Roda migrations como root, depois troca para usuario bookia.

set -e

cd /app/backend

# ── 1. Migrations ─────────────────────────────────────────────────────────────
echo ">>> Executando migraes Alembic..."
alembic upgrade head
echo ">>> Migrations aplicadas."

# ── 2. Primeiro admin ─────────────────────────────────────────────────────────
echo ">>> Verificando primeiro administrador..."
python3 -c "
import sys
sys.path.insert(0, '/app/backend')

from app.db import SessionLocal
from app.models.usuario import Usuario
from app.services.auth_service import hash_password
from sqlalchemy import func

db = SessionLocal()
try:
    count = db.query(func.count()).select_from(Usuario).scalar()
    if count == 0:
        login = 'admin'
        senha = 'admin123'
        print(f'  Criando admin padrao: {login} / {senha}')
        usuario = Usuario(login=login, senha_hash=hash_password(senha), perfil='admin')
        db.add(usuario)
        db.commit()
    else:
        print('  Administrador ja existe.')
finally:
    db.close()
"
echo ">>> Verificacao de admin concluida."

# ── 3. Iniciar uvicorn como bookia ────────────────────────────────────────────
echo ">>> Iniciando servidor Uvicorn como bookia..."
exec gosu bookia uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
