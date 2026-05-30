#!/usr/bin/env bash
# install.sh — Instalacao completa do Book-IA em Ubuntu (Docker Compose).
#
# Uso:
#   chmod +x install.sh
#   sudo ./install.sh
#
# Ou com credenciais customizadas:
#   sudo ./install.sh --login meuadmin --senha Minhasenha123

set -euo pipefail

# ── Cores ─────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log_ok()   { echo -e "${GREEN}[OK]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_info() { echo -e "${CYAN}[*]${NC}   $*"; }
log_err()  { echo -e "${RED}[ERR]${NC} $*" >&2; }

# ── Argumentos ────────────────────────────────────────────────────────────────
LOGIN="admin"
SENHA="admin123"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --login)  LOGIN="$2"; shift 2 ;;
    --senha)  SENHA="$2"; shift 2 ;;
    --help)
      echo "Uso: sudo $0 [OPCOES]"
      echo ""
      echo "OPCOES:"
      echo "  --login LOGIN   Login do primeiro admin (padrao: admin)"
      echo "  --senha SENHA   Senha do primeiro admin (minimo 6 caracteres, padrao: admin123)"
      echo "  --help          Mostra esta ajuda"
      echo ""
      echo "Exemplo:"
      echo "  sudo $0 --login editora --senha 'MinhaSenhaSegura!123'"
      exit 0
      ;;
    *) log_err "Argumento desconhecido: $1"; exit 1 ;;
  esac
done

if [[ ${#SENHA} -lt 6 ]]; then
  log_err "A senha deve ter pelo menos 6 caracteres."
  exit 1
fi

# ── Diretorio raiz ───────────────────────────────────────────────────────────
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo ""
echo "============================================"
echo "  Book-IA — Instalacao Completa"
echo "============================================"
echo ""

# ── 1. Verificar pre-requisitos ──────────────────────────────────────────────
log_info "Verificando pre-requisitos..."

for cmd in docker curl; do
  if ! command -v "$cmd" &>/dev/null; then
    log_err "$cmd nao encontrado. Instale antes de executar este script."
    exit 1
  fi
done

# Verificar docker compose v2
if docker compose version &>/dev/null; then
  log_ok "Docker Compose v2 encontrado"
elif docker-compose version &>/dev/null; then
  log_warn "Docker Compose v1 encontrado. Recomenda-se atualizar para v2."
else
  log_err "Docker Compose nao encontrado."
  exit 1
fi

# Verificar se usuario esta no grupo docker
if ! id -nG docker 2>/dev/null | grep -qw "$USER"; then
  log_warn "Usuario '$USER' nao esta no grupo 'docker'. O script usara sudo."
  NECESSITA_SUDO=true
else
  NECESSITA_SUDO=false
fi

# ── 2. Verificar se ja existe instalacao ─────────────────────────────────────
if docker compose ps --format name 2>/dev/null | grep -q bookia; then
  log_warn "Servicos Book-IA ja existem. Executando docker compose down -v para limpar..."
  sudo docker compose down -v 2>/dev/null || true
  sleep 3
fi

# ── 3. Construir e subir containeres ─────────────────────────────────────────
log_info "Construindo e iniciando servicos (isso pode demorar um pouco)..."
sudo docker compose up -d --build

# ── 4. Aguardar PostgreSQL saudavel ──────────────────────────────────────────
for i in $(seq 1 60); do
  if docker exec bookia-postgres pg_isready -U bookia -d bookia &>/dev/null; then
    log_ok "PostgreSQL pronto apos ${i}s"
    break
  fi
  if [[ $i -eq 60 ]]; then
    log_err "PostgreSQL nao ficou pronto em 60s. Verifique: sudo docker compose logs postgres"
    exit 1
  fi
  sleep 1
done

# Aguardar Redis
for i in $(seq 1 30); do
  if docker exec bookia-redis redis-cli ping 2>/dev/null | grep -q PONG; then
    log_ok "Redis pronto apos ${i}s"
    break
  fi
  if [[ $i -eq 30 ]]; then
    log_warn "Redis pode nao estar pronto. Continuando..."
  fi
  sleep 1
done

# ── 5. Aguardar backend estar pronto (entrypoint ja rodou migrations + admin) ─
log_info "Aguardando backend iniciar..."
for i in $(seq 1 60); do
  if curl -s http://localhost:8000/health &>/dev/null; then
    log_ok "Backend pronto apos ${i}s"
    break
  fi
  if [[ $i -eq 60 ]]; then
    log_err "Backend nao ficou pronto em 60s. Verifique: sudo docker compose logs backend"
    exit 1
  fi
  sleep 1
done

# ── 6. Tentar criar primeiro usuario admin via API ───────────────────────────
# O entrypoint do container ja cria um admin padrao.
# Se o usuario quiser outro login/senha, tenta criar aqui.
log_info "Verificando primeiro usuario administrador..."

RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:8000/api/v1/auth/setup \
  -F "login=${LOGIN}" \
  -F "senha=${SENHA}" 2>/dev/null) || true

if [[ "$RESPONSE" == "201" ]]; then
  log_ok "Administrador criado: ${LOGIN}"
elif [[ "$RESPONSE" == "403" ]]; then
  log_info "Administrador padrao 'admin' / 'admin123' ja criado pelo entrypoint."
else
  log_warn "Nao foi possivel criar administrador via API (HTTP ${RESPONSE})."
  log_warn "Use as credenciais padrao: admin / admin123"
fi

# ── 7. Verificar status dos servicos ─────────────────────────────────────────
echo ""
log_info "Status dos servicos:"
sudo docker compose ps 2>/dev/null || true

# ── 8. Verificar Celery worker ───────────────────────────────────────────────
sleep 3
WORKER_LOGS=$(sudo docker compose logs --tail=20 celery-worker 2>/dev/null || true)
if echo "$WORKER_LOGS" | grep -q "ready"; then
  log_ok "Celery worker esta rodando."
elif echo "$WORKER_LOGS" | grep -qi "error\|fail"; then
  log_warn "Celery worker pode ter problemas. Verifique:"
  echo "  sudo docker compose logs celery-worker"
else
  log_warn "Nao foi possivel confirmar se o Celery worker esta rodando."
  log_warn "Verifique: sudo docker compose logs celery-worker"
fi

# ── 9. Resumo final ─────────────────────────────────────────────────────────
echo ""
echo "============================================"
echo "  Instalacao Concluida!"
echo "============================================"
echo ""
echo "  URL:         http://localhost:8000"
echo "  Swagger:     http://localhost:8000/docs"
echo "  Admin login: ${LOGIN}"
echo "  Admin senha: ${SENHA}"
echo ""
echo "  Comandos uteis:"
echo "    docker compose logs -f backend"
echo "    docker compose logs -f celery-worker"
echo "    docker compose down          (para)"
echo "    docker compose down -v       (para + limpar dados)"
echo ""
echo "  Aviso: Se o login/senha acima falhar, use:"
echo "    admin / admin123 (padrao criado pelo entrypoint)"
echo ""
