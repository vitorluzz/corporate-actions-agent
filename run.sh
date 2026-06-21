#!/usr/bin/env bash
#
# run.sh — roda TODO o projeto localmente (backend + API + console).
#
# Detecta automaticamente:
#   • Provider de LLM  -> Gemini se houver GOOGLE_API_KEY no .env, senão stub offline
#   • Banco de dados   -> Postgres (Docker) se disponível, senão SQLite local
#
# Uso:
#   ./run.sh              # = all  (setup + banco + lote + API + console)
#   ./run.sh setup        # instala dependências (uv + npm)
#   ./run.sh batch        # roda o lote -> outputs/ (JSONs + relatório)
#   ./run.sh api          # sobe só a API (FastAPI :8000)
#   ./run.sh web          # sobe só o console (Vite :5173)
#   ./run.sh test         # roda os testes do backend
#   ./run.sh stop         # derruba o Postgres (Docker)
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
SQLITE_DB="$ROOT/.local/asset_servicing.db"

API_PID=""
WEB_PID=""

# ── output helpers ──────────────────────────────────────────────────────────
log()  { printf "\033[1;36m▶ %s\033[0m\n" "$*"; }
ok()   { printf "\033[1;32m✓ %s\033[0m\n" "$*"; }
warn() { printf "\033[1;33m! %s\033[0m\n" "$*"; }
err()  { printf "\033[1;31m✗ %s\033[0m\n" "$*" >&2; }

# ── pre-flight ──────────────────────────────────────────────────────────────
require() { command -v "$1" >/dev/null 2>&1 || { err "'$1' não encontrado. Instale antes de continuar."; exit 1; }; }

ensure_env() {
  if [[ ! -f "$ROOT/.env" ]]; then
    cp "$ROOT/.env.example" "$ROOT/.env"
    warn "Criei .env a partir de .env.example. Edite GOOGLE_API_KEY para usar o Gemini."
  fi
}

show_provider() {
  if grep -qE '^[[:space:]]*GOOGLE_API_KEY[[:space:]]*=[[:space:]]*[^[:space:]]+' "$ROOT/.env" 2>/dev/null; then
    ok "GOOGLE_API_KEY detectada  →  provider = gemini (extração real + visão)"
  else
    warn "Sem GOOGLE_API_KEY       →  provider = stub (offline determinístico)"
  fi
}

# ── database ────────────────────────────────────────────────────────────────
docker_up() { command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; }

compose_cmd() {
  if docker compose version >/dev/null 2>&1; then echo "docker compose";
  elif command -v docker-compose >/dev/null 2>&1; then echo "docker-compose";
  else echo ""; fi
}

setup_db() {
  if docker_up; then
    local c; c="$(compose_cmd)"
    if [[ -n "$c" ]]; then
      log "Subindo Postgres ($c)..."
      $c -f "$ROOT/infra/docker-compose.yml" up -d postgres
      for _ in $(seq 1 30); do
        [[ "$(docker inspect --format '{{.State.Health.Status}}' asset_pg 2>/dev/null)" == "healthy" ]] && {
          ok "Postgres saudável (system of record)."; return 0;
        }
        sleep 1
      done
      warn "Postgres não respondeu a tempo; caindo para SQLite."
    fi
  else
    warn "Docker indisponível; usando SQLite local (Postgres é o default documentado)."
  fi
  mkdir -p "$(dirname "$SQLITE_DB")"
  export DATABASE_URL="sqlite:///$SQLITE_DB"
  ok "Banco: SQLite ($SQLITE_DB)"
}

# ── tasks ───────────────────────────────────────────────────────────────────
setup() {
  require uv; require npm
  log "Instalando backend (uv sync)..."
  ( cd "$BACKEND" && uv sync --extra dev )
  ok "Backend pronto."
  log "Instalando frontend (npm install)..."
  ( cd "$FRONTEND" && npm install --no-fund --no-audit )
  ok "Frontend pronto."
}

ensure_deps() {
  [[ -d "$BACKEND/.venv" ]] || { log "Backend sem .venv — instalando..."; ( cd "$BACKEND" && uv sync --extra dev ); }
  [[ -d "$FRONTEND/node_modules" ]] || { log "Frontend sem node_modules — instalando..."; ( cd "$FRONTEND" && npm install --no-fund --no-audit ); }
}

batch() {
  ensure_env; show_provider
  log "Rodando o lote sobre documents/ → outputs/"
  ( cd "$BACKEND" && uv run asset-agent run )
  ok "Outputs em outputs/ (JSONs + exceptions_report.md + run_summary.json)"
}

api() {
  ensure_env
  [[ -n "${DATABASE_URL:-}" ]] || setup_db
  log "API: http://localhost:8000  (Swagger em /docs)"
  ( cd "$BACKEND" && uv run uvicorn app.api.main:app --reload --port 8000 )
}

web() {
  log "Console: http://localhost:5173"
  ( cd "$FRONTEND" && npm run dev )
}

test_backend() {
  log "Rodando testes (hermético, sempre stub)..."
  ( cd "$BACKEND" && uv run pytest -q )
}

stop() {
  local c; c="$(compose_cmd)"
  if docker_up && [[ -n "$c" ]]; then
    log "Derrubando Postgres..."
    $c -f "$ROOT/infra/docker-compose.yml" down
  fi
  ok "Serviços Docker encerrados."
}

cleanup() {
  printf "\n"; warn "Encerrando serviços..."
  [[ -n "$API_PID" ]] && kill "$API_PID" 2>/dev/null || true
  [[ -n "$WEB_PID" ]] && kill "$WEB_PID" 2>/dev/null || true
  exit 0
}

all() {
  ensure_env; show_provider; ensure_deps; setup_db

  # Gera os deliverables (outputs/). Não aborta o resto se falhar (ex.: quota).
  log "Gerando outputs (lote)..."
  ( cd "$BACKEND" && uv run asset-agent run ) || warn "Lote falhou; o console ainda pode ingerir via API."

  log "Iniciando API (:8000) e Console (:5173)..."
  ( cd "$BACKEND" && exec uv run uvicorn app.api.main:app --port 8000 --log-level warning ) &
  API_PID=$!
  ( cd "$FRONTEND" && exec npm run dev ) &
  WEB_PID=$!
  trap cleanup INT TERM

  # Espera a API e popula o banco para o console.
  for _ in $(seq 1 30); do curl -sf localhost:8000/health >/dev/null 2>&1 && break; sleep 1; done
  log "Populando o banco (POST /ingest)..."
  if curl -sf -X POST localhost:8000/ingest >/dev/null 2>&1; then ok "Lote ingerido no banco."; else warn "Ingest falhou — verifique a API."; fi

  printf "\n"
  ok "API:     http://localhost:8000/docs"
  ok "Console: http://localhost:5173"
  ok "Pressione Ctrl+C para encerrar tudo."
  wait
}

case "${1:-all}" in
  all)   all ;;
  setup) setup ;;
  batch) batch ;;
  api)   api ;;
  web)   web ;;
  test)  test_backend ;;
  stop)  stop ;;
  *) err "Comando desconhecido: ${1}"; sed -n '3,22p' "$0"; exit 1 ;;
esac
