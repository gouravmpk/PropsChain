# PropChain — Commands & Setup Guide
**Team OpsAI | AI for Bharat Hackathon | Powered by AWS**

---

## Prerequisites (First-Time Setup)

```bash
# Install Python 3.12
brew install python@3.12

# Install MongoDB
brew tap mongodb/brew
brew install mongodb-community

# Install dependencies
cd backend
./run.sh setup
```

---

## Daily Dev Workflow

```bash
cd backend

./run.sh start       # Start server (foreground, hot-reload on file save)
./run.sh start-bg    # Start server in background
./run.sh stop        # Stop background server
./run.sh status      # Show server + MongoDB health
./run.sh logs        # Tail background server logs
./run.sh open        # Open Swagger UI in Chrome
```

---

## MongoDB Commands

```bash
./run.sh mongo-start  # Start MongoDB
./run.sh mongo-stop   # Stop MongoDB

# Reset all blockchain data (dev only)
./run.sh reset-db
```

---

## URLs

| Page         | URL                                 |
|--------------|-------------------------------------|
| Swagger UI   | http://localhost:8000/swagger       |
| ReDoc        | http://localhost:8000/redoc         |
| OpenAPI JSON | http://localhost:8000/openapi.json  |
| Health       | http://localhost:8000/health        |

---

## API Endpoints

### AI Document Verification

| Method | Route              | Description                                   |
|--------|--------------------|-----------------------------------------------|
| POST   | /ai/verify-document | Upload PDF/image → AI fraud detection + on-chain log |
| GET    | /ai/mode           | Check if using real AWS or mock mode          |

#### `/ai/verify-document` form fields

| Field             | Type    | Required | Description                                          |
|-------------------|---------|----------|------------------------------------------------------|
| file              | File    | ✅       | PDF, JPEG, PNG, or TIFF (max 10 MB)                  |
| property_id       | string  | ✅       | Property ID already registered on chain              |
| document_type     | string  | ✅       | Title Deed / Sale Agreement / Aadhaar Card / etc.    |
| auto_log_on_chain | boolean | ❌       | Auto-log result as blockchain block (default: true)  |
| mock_scenario     | string  | ❌       | `auto` / `authentic` / `suspicious` / `flagged`      |

#### `mock_scenario` values *(ignored in real AWS mode)*

| Value       | Outcome                                          |
|-------------|--------------------------------------------------|
| `auto`      | Determined by file hash (default)                |
| `authentic` | Always returns clean, authentic result           |
| `suspicious`| Always returns medium-risk result                |
| `flagged`   | Always returns high-fraud flagged result         |

#### Verdict thresholds

| fraud_score  | Verdict      |
|--------------|--------------|
| 0.00 – 0.34  | `AUTHENTIC`  |
| 0.35 – 0.65  | `SUSPICIOUS` |
| 0.66 – 1.00  | `FLAGGED`    |

---

### Blockchain

| Method | Route                               | Description                        |
|--------|-------------------------------------|------------------------------------|
| POST   | /blockchain/mint                    | Register property (genesis block)  |
| POST   | /blockchain/transfer                | Record ownership transfer          |
| POST   | /blockchain/verify-document         | Log AI fraud check result on-chain |
| POST   | /blockchain/status                  | Update legal status                |
| POST   | /blockchain/fractional/mint         | Tokenize property into shares      |
| POST   | /blockchain/fractional/transfer     | Transfer fractional tokens         |
| GET    | /blockchain/passport/{property_id}  | Full Property Passport             |
| GET    | /blockchain/verify/{property_id}    | Verify chain integrity             |
| GET    | /blockchain/block/{block_hash}      | Block explorer by hash             |
| GET    | /blockchain/properties              | List all registered properties     |
| GET    | /health                             | Health check                       |

---

## Enabling Real AWS AI

1. Get AWS credentials with permissions for: `Textract`, `Bedrock`
2. Enable Bedrock model access in AWS Console → `us-east-1` → Bedrock → Model Access → enable `Claude Haiku`
3. Add to `backend/.env`:

```env
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
```

4. Restart the server → `GET /ai/mode` will return `"mode": "aws"`

---

## Project Structure

```
OpsAi/
├── Commands.md                          ← This file
├── PropChain.postman_collection.json    ← Import into Postman
├── PropChain.postman_environment.json   ← Import into Postman
└── backend/
    ├── run.sh                           ← All commands
    ├── main.py                          ← FastAPI app entry point
    ├── requirements.txt                 ← Python dependencies
    ├── .env                             ← Local config (MongoDB + AWS keys)
    ├── .env.example                     ← Template for all env vars
    ├── config/
    │   └── database.py                  ← MongoDB client + indexes
    ├── models/
    │   ├── blockchain.py                ← Blockchain Pydantic models
    │   └── ai_verify.py                 ← AI verification models
    ├── routes/
    │   ├── blockchain.py                ← Blockchain route handlers
    │   └── ai_verify.py                 ← AI verify route handlers
    ├── services/
    │   ├── blockchain_service.py        ← Core blockchain logic
    │   ├── ai_service.py               ← Textract + Bedrock + mock
    │   └── fraud_rules.py              ← Rule-based fraud checks
    └── utils/
        └── hashing.py                   ← SHA-256 hashing + timestamp
```

---

## Postman

1. Open Postman
2. `File → Import` → select `PropChain.postman_collection.json`
3. `File → Import` → select `PropChain.postman_environment.json`
4. Select environment: **PropChain — Local**
5. Run folders in order (00 → 09)
6. For AI upload requests: Body → form-data → set `file` type to **File**

> Variables `{{genesis_hash}}`, `{{block_hash}}`, `{{ai_mode}}` are auto-saved from responses.

---

## Environment Variables (`.env`)

```env
# MongoDB
MONGODB_URL=mongodb://localhost:27017
DB_NAME=propchain_db

# AWS (leave blank for mock mode)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1
BEDROCK_MODEL=anthropic.claude-haiku-4-5-20251001
```

---

## Tech Stack

| Layer      | Technology                                      |
|------------|-------------------------------------------------|
| Backend    | FastAPI (Python 3.12)                           |
| Blockchain | SHA-256 hash-chained mock (FastAPI + MongoDB)   |
| Database   | MongoDB (Motor async driver)                    |
| AI         | AWS Textract + AWS Bedrock (Claude Haiku)       |
| Fraud Rules| Rule-based (dates, formats, name consistency)   |
| Frontend   | React.js (planned)                              |
| Deployment | AWS EC2 / Railway (planned)                     |
