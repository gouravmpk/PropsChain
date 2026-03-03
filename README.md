# PropsChain

**Live Demo:** https://d3fv0lpke5d3uv.cloudfront.net/

Blockchain & AI-powered property registration platform for India — built for the **AI for Bharat Hackathon** powered by AWS.

---

## Problem

Property registration in India is slow, manual, and prone to fraud. Real estate investments remain inaccessible due to high capital requirements and lack of transparency.

## Solution

- **Property Passport** — Every property gets an immutable, SHA-256 hash-chained digital identity. Each block stores `(block_index, property_id, data, previous_hash, timestamp, hash)`. Tamper detection runs on every chain read.
- **AI Fraud Detection** — Documents (Title Deed, Aadhaar, Encumbrance Certificate, etc.) are analyzed by Amazon Nova Lite (primary) or Nova Pro (fallback) via AWS Bedrock. The fraud score, flags, and extracted fields are written on-chain as a `DOCUMENT_VERIFICATION` block — a permanent, tamper-proof audit trail.
- **Fractional Ownership** — Tokenize premium assets (hospitals, warehouses) into investable shares accessible to small investors.

---

## Architecture

```
User → CloudFront (d3fv0lpke5d3uv.cloudfront.net)
         ├── /         → S3 (React SPA, static hosting)
         └── /api/*    → ECS Fargate (FastAPI, port 8000)
                             ├── AWS Bedrock Nova Lite — AI fraud detection (Nova Pro as tier-2 fallback)
                             ├── DynamoDB              — Bedrock response cache
                             ├── MongoDB (Atlas)        — Blockchain ledger + user/property data
                             └── Secrets Manager        — MongoDB URL, JWT secret, AWS keys
```

### Resilience layers on every Bedrock call
```
Request → DynamoDB cache check     (hash match → instant response, $0 model cost)
       → Bedrock Nova Lite         (primary — 4× retry, exponential backoff 2–30 s)
       → Bedrock Nova Pro          (tier-2 — if Lite is throttled / unavailable)
       → OpenAI GPT-4o-mini        (tier-3 — if both Nova models fail on demo day)
       → Mock simulation           (last resort, never breaks the demo)
```

---

## Architecture Decisions

| Decision | Why |
|---|---|
| MongoDB over RDS | Flexible document schema for blockchain blocks; `(property_id, block_index)` unique index enforces append-only at the DB level — no block can be overwritten |
| ECS Fargate over Lambda | FastAPI with heavy image processing (PyMuPDF, Pillow) exceeds Lambda's 250 MB limit; Fargate avoids cold starts on demo day |
| CloudFront in front of S3 | HTTPS, global CDN, SPA routing (403/404 → index.html), and `/api/*` proxy to Fargate — single domain, no CORS complexity |
| Bedrock region `us-east-1` | Higher TPM/RPM quota vs `ap-south-1` for Nova models; AWS team explicitly recommended this in their demo session |
| DynamoDB cache for Bedrock | SHA-256 hash of file bytes → DynamoDB lookup before every Bedrock call; repeated uploads cost $0 in model credits with sub-10ms response |
| OpenAI GPT-4o-mini fallback | If Bedrock throttles during the demo, the same prompt/schema is served by OpenAI transparently — the UI never shows an error |
| Exponential backoff (tenacity) | Retries throttled Bedrock calls 4× with 2–30 s exponential wait before falling back; a single throttle doesn't kill the demo |
| Nova Lite primary, Pro fallback | Lite handles most single-page docs at lower cost; Pro auto-activates if Lite is throttled — no manual switching needed |

---

## AWS Services Used

| Service | Role | Free Tier |
|---|---|---|
| CloudFront | CDN + HTTPS + API proxy | 1 TB/month |
| S3 | React SPA static hosting | 5 GB |
| ECS Fargate | FastAPI backend container (512 CPU, 1 GB) | — |
| ECR | Docker image registry | 500 MB |
| AWS Bedrock (Nova Lite / Pro) | AI document fraud detection (Lite primary, Pro fallback) | Per token |
| DynamoDB | Bedrock response cache (25 GB always free) | 25 GB always |
| Secrets Manager | MongoDB URL, JWT, AWS keys | — |

---

## Why the AI is Load-Bearing

Removing the AI layer makes property registration **insecure by design** — any document would pass. The AI's role:

1. Fraud score is written to the **immutable blockchain ledger** as a `DOCUMENT_VERIFICATION` block
2. Combined with deterministic rule checks (future dates, registration number format, stamp duty cross-check)
3. Gates ownership transfers — a `FLAGGED` document cannot proceed to transfer on-chain
4. Cross-document consistency check detects name/survey number mismatches across a document set

---

## Submission Details

| Item | Value |
|---|---|
| Live URL | https://d3fv0lpke5d3uv.cloudfront.net/ |
| GitHub | https://github.com/gouravmpk/PropsChain |
| Team | OpsAI |
| Team Lead | Muruganandham Selvamani |
| Problem Statement | Slow and Manual Property Registration |

---

## Local Development

```bash
# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env   # fill MONGODB_URL, JWT_SECRET, AWS keys
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

API docs available at `http://localhost:8000/docs`

---

## Deploy to AWS

```bash
cd infra
pip install -r requirements.txt
cdk deploy
./deploy.sh   # builds Docker image, pushes to ECR, syncs React build to S3
```

After deploy, set secrets in AWS Secrets Manager under `propchain/config`:
```json
{
  "MONGODB_URL": "...",
  "JWT_SECRET": "...",
  "AWS_ACCESS_KEY_ID": "...",
  "AWS_SECRET_ACCESS_KEY": "..."
}
```