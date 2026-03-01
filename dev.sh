#!/bin/bash
# =============================================================================
# PropChain — Full Stack Dev Runner
# Starts: MongoDB + FastAPI backend (port 8000) + React frontend (port 5173)
# =============================================================================

set -e

BACKEND_DIR="backend"
FRONTEND_DIR="frontend"
BACKEND_PORT=8000
FRONTEND_PORT=5173

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

banner() {
  echo ""
  echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
  echo -e "${CYAN}║       PropChain — Full Stack Dev             ║${NC}"
  echo -e "${CYAN}║     AI for Bharat Hackathon | OpsAI         ║${NC}"
  echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
  echo ""
}

# ── Cleanup on Ctrl+C ─────────────────────────────────────────────────────────
cleanup() {
  echo ""
  echo -e "${YELLOW}Shutting down...${NC}"
  [ -n "$BACKEND_PID" ]  && kill "$BACKEND_PID"  2>/dev/null && echo -e "  ${GREEN}✅ Backend stopped${NC}"
  [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null && echo -e "  ${GREEN}✅ Frontend stopped${NC}"
  exit 0
}
trap cleanup INT TERM

# ── Check frontend deps ───────────────────────────────────────────────────────
check_frontend() {
  if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo -e "${YELLOW}Installing frontend dependencies...${NC}"
    cd "$FRONTEND_DIR"
    npm install
    cd ..
    echo -e "${GREEN}  ✅ Frontend deps installed${NC}"
  fi
}

# ── Check backend venv ────────────────────────────────────────────────────────
check_backend() {
  if [ ! -d "$BACKEND_DIR/venv" ]; then
    echo -e "${YELLOW}Backend venv not found. Running setup...${NC}"
    cd "$BACKEND_DIR"
    ./run.sh setup
    cd ..
  fi
}

# ── Start MongoDB ─────────────────────────────────────────────────────────────
start_mongo() {
  echo -e "${YELLOW}Starting MongoDB...${NC}"
  if brew services list | grep -q "mongodb-community.*started"; then
    echo -e "${GREEN}  ✅ MongoDB already running${NC}"
  else
    brew services start mongodb/brew/mongodb-community
    sleep 2
    echo -e "${GREEN}  ✅ MongoDB started${NC}"
  fi
}

# ── Main ──────────────────────────────────────────────────────────────────────
banner
check_backend
check_frontend
start_mongo

echo ""
echo -e "${BOLD}Starting services...${NC}"
echo ""

# Start backend in background
cd "$BACKEND_DIR"
venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port $BACKEND_PORT > /tmp/propchain-backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# Start frontend in background
cd "$FRONTEND_DIR"
npm run dev -- --port $FRONTEND_PORT > /tmp/propchain-frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

# Wait for both to be ready
echo -ne "${YELLOW}Waiting for backend...${NC}"
for i in $(seq 1 15); do
  if curl -s "http://localhost:$BACKEND_PORT/health" > /dev/null 2>&1; then
    echo -e " ${GREEN}ready${NC}"
    break
  fi
  echo -n "."
  sleep 1
done

echo -ne "${YELLOW}Waiting for frontend...${NC}"
for i in $(seq 1 15); do
  if curl -s "http://localhost:$FRONTEND_PORT" > /dev/null 2>&1; then
    echo -e " ${GREEN}ready${NC}"
    break
  fi
  echo -n "."
  sleep 1
done

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           PropChain is running!              ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${CYAN}Frontend     →  http://localhost:$FRONTEND_PORT${NC}"
echo -e "  ${CYAN}Backend API  →  http://localhost:$BACKEND_PORT${NC}"
echo -e "  ${CYAN}Swagger UI   →  http://localhost:$BACKEND_PORT/swagger${NC}"
echo -e "  ${CYAN}Health       →  http://localhost:$BACKEND_PORT/health${NC}"
echo ""
echo -e "  Backend logs  →  tail -f /tmp/propchain-backend.log"
echo -e "  Frontend logs →  tail -f /tmp/propchain-frontend.log"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop both services.${NC}"
echo ""

# Keep script alive — forward logs to terminal
tail -f /tmp/propchain-backend.log &
TAIL_PID=$!

wait $BACKEND_PID $FRONTEND_PID
