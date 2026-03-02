#!/bin/bash
# =============================================================================
# PropChain — Project Runner
# AI for Bharat Hackathon | Team OpsAI
# =============================================================================

set -e

VENV_DIR="venv"
PYTHON="venv/bin/python3"
PORT=8000

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m' # No Color

banner() {
  echo ""
  echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
  echo -e "${CYAN}║         PropChain API — OpsAI Team           ║${NC}"
  echo -e "${CYAN}║     AI for Bharat Hackathon | AWS            ║${NC}"
  echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
  echo ""
}

# ── Setup: create venv + install deps ────────────────────────────────────────
setup() {
  banner
  echo -e "${YELLOW}[1/3] Checking Python...${NC}"
  if command -v python3.12 &>/dev/null; then
    PY=python3.12
  elif command -v /opt/homebrew/bin/python3.12 &>/dev/null; then
    PY=/opt/homebrew/bin/python3.12
  else
    echo -e "${RED}Python 3.12 not found. Install via: brew install python@3.12${NC}"
    exit 1
  fi
  echo -e "  Using: $($PY --version)"

  echo -e "${YELLOW}[2/3] Creating virtual environment...${NC}"
  $PY -m venv $VENV_DIR
  echo -e "  venv created at ./$VENV_DIR"

  echo -e "${YELLOW}[3/3] Installing dependencies...${NC}"
  $VENV_DIR/bin/pip install -r requirements.txt -q
  echo -e "${GREEN}  ✅ Dependencies installed${NC}"


                                                                                                                                                                                                                                                  
  echo ""
  if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${YELLOW}  ⚠️  .env created from .env.example — add your AWS credentials before starting.${NC}"
  else
    echo -e "${GREEN}  ✅ .env already exists${NC}"
  fi

  echo ""
  echo -e "${GREEN}Setup complete. Run './run.sh start' to launch the server.${NC}"
}

# ── MongoDB: start ────────────────────────────────────────────────────────────
mongo_start() {
  echo -e "${YELLOW}Starting MongoDB...${NC}"
  if brew services list | grep -q "mongodb-community.*started"; then
    echo -e "${GREEN}  ✅ MongoDB already running${NC}"
  else
    brew services start mongodb/brew/mongodb-community
    sleep 2
    echo -e "${GREEN}  ✅ MongoDB started${NC}"
  fi
}

# ── MongoDB: stop ─────────────────────────────────────────────────────────────
mongo_stop() {
  echo -e "${YELLOW}Stopping MongoDB...${NC}"
  brew services stop mongodb/brew/mongodb-community
  echo -e "${GREEN}  ✅ MongoDB stopped${NC}"
}

# ── Start the FastAPI server ──────────────────────────────────────────────────
start() {
  banner
  mongo_start

  if [ ! -d "$VENV_DIR" ]; then
    echo -e "${RED}Virtual environment not found. Run './run.sh setup' first.${NC}"
    exit 1
  fi

  echo ""
  echo -e "${GREEN}Starting PropChain API on port $PORT...${NC}"
  echo ""
  echo -e "  ${CYAN}Swagger UI  →  http://localhost:$PORT/swagger${NC}"
  echo -e "  ${CYAN}ReDoc       →  http://localhost:$PORT/redoc${NC}"
  echo -e "  ${CYAN}OpenAPI     →  http://localhost:$PORT/openapi.json${NC}"
  echo -e "  ${CYAN}Health      →  http://localhost:$PORT/health${NC}"
  echo ""
  echo -e "${YELLOW}Press Ctrl+C to stop.${NC}"
  echo ""

  $VENV_DIR/bin/uvicorn main:app --reload --host 0.0.0.0 --port $PORT
}

# ── Start in background ───────────────────────────────────────────────────────
start_bg() {
  banner
  mongo_start

  if [ ! -d "$VENV_DIR" ]; then
    echo -e "${RED}Virtual environment not found. Run './run.sh setup' first.${NC}"
    exit 1
  fi

  echo -e "${GREEN}Starting PropChain API in background on port $PORT...${NC}"
  nohup $VENV_DIR/bin/uvicorn main:app --host 0.0.0.0 --port $PORT > /tmp/propchain.log 2>&1 &
  echo $! > /tmp/propchain.pid
  sleep 2

  if curl -s http://localhost:$PORT/health > /dev/null; then
    echo -e "${GREEN}  ✅ Server running (PID $(cat /tmp/propchain.pid))${NC}"
    echo -e "  ${CYAN}Swagger UI  →  http://localhost:$PORT/swagger${NC}"
    echo -e "  ${CYAN}Logs        →  tail -f /tmp/propchain.log${NC}"
    echo -e "  ${CYAN}Stop        →  ./run.sh stop${NC}"
  else
    echo -e "${RED}  ❌ Server failed to start. Check logs: tail /tmp/propchain.log${NC}"
  fi
}

# ── Stop background server ────────────────────────────────────────────────────
stop() {
  if [ -f /tmp/propchain.pid ]; then
    PID=$(cat /tmp/propchain.pid)
    kill "$PID" 2>/dev/null && echo -e "${GREEN}  ✅ Server stopped (PID $PID)${NC}" || echo -e "${YELLOW}  Server was not running${NC}"
    rm -f /tmp/propchain.pid
  else
    echo -e "${YELLOW}No PID file found. Server may not be running.${NC}"
  fi
}

# ── Logs ──────────────────────────────────────────────────────────────────────
logs() {
  tail -f /tmp/propchain.log
}

# ── Status ────────────────────────────────────────────────────────────────────
status() {
  echo -e "${CYAN}=== PropChain Status ===${NC}"
  if [ -f /tmp/propchain.pid ] && kill -0 "$(cat /tmp/propchain.pid)" 2>/dev/null; then
    echo -e "  Server   : ${GREEN}RUNNING${NC} (PID $(cat /tmp/propchain.pid))"
  else
    echo -e "  Server   : ${RED}STOPPED${NC}"
  fi

  if brew services list | grep -q "mongodb-community.*started"; then
    echo -e "  MongoDB  : ${GREEN}RUNNING${NC}"
  else
    echo -e "  MongoDB  : ${RED}STOPPED${NC}"
  fi

  if curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
    echo -e "  API      : ${GREEN}REACHABLE${NC} → http://localhost:$PORT"
  else
    echo -e "  API      : ${RED}UNREACHABLE${NC}"
  fi
}

# ── Open browser ──────────────────────────────────────────────────────────────
open_docs() {
  open -a "Google Chrome" "http://localhost:$PORT/swagger"
}

# ── Wipe DB (dev only) ────────────────────────────────────────────────────────
reset_db() {
  echo -e "${RED}WARNING: This will delete all PropChain data from MongoDB.${NC}"
  read -p "Type 'yes' to confirm: " confirm
  if [ "$confirm" = "yes" ]; then
    $VENV_DIR/bin/python3 -c "
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def drop():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    await client['propchain_db']['blockchain_ledger'].drop()
    await client['propchain_db']['properties'].drop()
    print('✅ Collections dropped')
    client.close()

asyncio.run(drop())
"
  else
    echo "Cancelled."
  fi
}

# ── Help ──────────────────────────────────────────────────────────────────────
help() {
  banner
  echo "Usage: ./run.sh <command>"
  echo ""
  echo "Commands:"
  echo "  setup       Install Python venv + dependencies"
  echo "  start       Start server (foreground, with auto-reload)"
  echo "  start-bg    Start server in background"
  echo "  stop        Stop background server"
  echo "  logs        Tail background server logs"
  echo "  status      Show server + MongoDB status"
  echo "  open        Open Swagger UI in Chrome"
  echo "  mongo-start Start MongoDB"
  echo "  mongo-stop  Stop MongoDB"
  echo "  reset-db    ⚠️  Drop all blockchain data (dev only)"
  echo "  help        Show this message"
  echo ""
}

# ── Entrypoint ────────────────────────────────────────────────────────────────
case "${1:-help}" in
  setup)       setup ;;
  start)       start ;;
  start-bg)    start_bg ;;
  stop)        stop ;;
  logs)        logs ;;
  status)      status ;;
  open)        open_docs ;;
  mongo-start) mongo_start ;;
  mongo-stop)  mongo_stop ;;
  reset-db)    reset_db ;;
  help|*)      help ;;
esac
