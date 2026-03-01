# .github/copilot-instructions.md

# Advanced Copilot Instructions — PropChain (OpsAI)

## Role & Expectations

You are assisting as a **senior full-stack engineer** working on a **production-grade MVP** for a hackathon.
Code must be clean, modular, readable, and demo-ready while remaining scalable to real-world usage.

Do not generate toy examples.

---

## Project Context

**Project:** PropChain
**Domain:** Real Estate | Blockchain | AI | India
**Core Objective:**
Digitize property registration, prevent fraud using AI, and enable fractional real-estate ownership via blockchain.

---

## Tech Stack (Non-Negotiable)

### Frontend

- React (Vite)
- JavaScript (ES6+)
- Tailwind CSS
- Axios
- Functional components + hooks only

### Backend

- Python 3.10+
- FastAPI
- REST APIs
- Pydantic models
- JWT-ready (mock allowed)

### Cloud / Infra

- AWS DynamoDB (NoSQL)
- AWS S3 (documents)
- Amazon Bedrock (AI verification)
- Ethereum / Web3 (mocked interactions)

---

## Architecture Rules

1. **Frontend → FastAPI only**
2. **FastAPI → AWS / AI / Blockchain services**
3. **No direct AWS calls from frontend**
4. **No business logic in route handlers**
5. **Services handle all integrations**
6. **Blockchain is append-only (immutable)**
7. **DynamoDB is metadata source of truth**

---

## Folder Responsibilities

### `/routes`

- Define API endpoints only
- Validate input
- Call service layer
- Return JSON responses
- No AWS or Web3 logic

### `/services`

- AWS SDK usage (boto3)
- Bedrock AI invocation
- Blockchain/Web3 abstraction
- External system integration
- Reusable logic only

### `/models.py`

- Pydantic request/response schemas
- No DB logic

### `/frontend/pages`

- Route-level UI
- Page state management
- API orchestration

### `/frontend/components`

- Stateless UI components
- Reusable visuals only

---

## Backend Coding Rules (FastAPI)

- Always use `APIRouter`
- Explicit HTTP verbs
- Clear route naming:
  - `/property/register`
  - `/property/{id}`
  - `/ai/verify`
  - `/fractional/tokenize`
- Prefer UUIDs for IDs
- Return explicit status fields

Example pattern:

```python
@router.post("/register")
def register_property(request: PropertyCreate):
    ...
```
