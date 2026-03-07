# PropChain — Hackathon Submission PPT
# AI for Bharat | Powered by AWS

---

## SLIDE 1 — Brief about the Idea

**PropChain** is an AI + Blockchain powered property verification and transaction platform built to eliminate property fraud in India.

India processes over 1.2 crore property transactions annually. A significant portion are fraudulent — forged title deeds, properties sold under disputed ownership, mortgaged assets misrepresented as clear. Buyers have no reliable, fast way to verify a document's authenticity or check if a seller is the true owner.

**PropChain solves this with three pillars:**

**1. AI Document Verification**
A buyer or bank uploads any property document — Title Deed, Encumbrance Certificate, Aadhaar, Sale Agreement. AWS Bedrock (Amazon Nova) reads the document like a human expert, extracts all fields, and runs a fraud analysis in under 3 seconds. The result: a fraud score (0–1), specific red flags, and a verdict — AUTHENTIC, SUSPICIOUS, or FLAGGED.

**2. National Registry Cross-Check**
Extracted fields (owner name, survey number, registration number) are verified against a national property registry covering 8 states. This catches fraud that even a perfect-looking document can hide — a wrong owner, a fabricated survey number, an active bank mortgage the seller is concealing.

**3. Blockchain Audit Trail**
Every event — registration, AI verification, ownership transfer, payment installment — is written as an append-only SHA-256 hash-chained block in MongoDB. No event can be erased. Tamper detection runs on every read. Each property gets a permanent, verifiable digital identity called a **Property Passport**.

**The result:** A first-time home buyer gets the confidence of a 3-day legal due diligence in 2 seconds.

---

## SLIDE 2 — AI in the Solution

### Why AI is Required

Property documents are unstructured scanned images — PDFs and JPEGs of paper records with no fixed schema, no standard field positions, and no machine-readable format. A traditional rule-based system cannot:
- Read handwritten or printed text from a scanned image
- Understand that "R. Kumar" and "Ravi Kumar" might be the same person or a fraud attempt
- Detect that an amount written as "50 Lakhs approx" is suspicious because it is non-numeric
- Identify digital editing artifacts or inconsistent fonts within a document

**Only a vision-capable large language model can do all of this simultaneously in one pass.**

---

### How AWS Services are Used

| AWS Service | Role in Architecture |
|-------------|---------------------|
| **Amazon Bedrock — Nova Lite** | Primary AI model. Receives document pages as images via `converse()` API. Extracts all key fields AND performs fraud analysis in a single call. No separate OCR step needed. |
| **Amazon Bedrock — Nova Pro** | Automatic fallback when Nova Lite is throttled. Activated transparently — the user sees no disruption. |
| **Amazon ECS / Fargate** | Runs the FastAPI backend as a Docker container. Serverless compute — no EC2 instances to manage. |
| **Amazon S3** | Hosts the React frontend build. Private bucket accessed only through CloudFront OAC. |
| **Amazon CloudFront** | Single entry point for the entire platform. Serves frontend from S3 and proxies all `/api/*` traffic to Fargate over HTTP. HTTPS termination at edge. |
| **Amazon DynamoDB** | Bedrock response cache. File SHA-256 hash → cached AI result, 7-day TTL. Zero Bedrock cost on repeated uploads of the same document. |
| **AWS Secrets Manager** | Stores MongoDB URL, JWT secret, and AWS credentials. Injected into the container at startup — no secrets in code. |
| **Amazon ECR** | Docker image registry. CI/CD-ready with lifecycle rules (keep last 5 images). |

---

### What Value the AI Layer Adds to the User Experience

**Before PropChain (without AI):**
- Hire a property lawyer: ₹5,000–₹20,000 and 3–7 days
- Manually visit Sub-Registrar Office to check records
- No guarantee the advocate catches every fraud pattern
- Result is a paper opinion, not a verifiable audit trail

**With PropChain (AI layer):**
- Upload document → result in < 3 seconds
- Specific flags: *"REGISTRY: Owner mismatch — Registry shows 'Lakshmi Narayana', document claims 'Ravi Kumar'"*
- Fraud score with explainable reasoning, not just a yes/no
- Result permanently logged on blockchain — becomes legal evidence
- Zero cost on recheck (DynamoDB cache)
- Works 24/7, no office visit required

The AI layer transforms property verification from a professional service only the wealthy can afford into a free, instant, always-available utility for every Indian buyer.

---

## SLIDE 3 — Features

### Complete Feature List

**AI & Fraud Detection**
- Single-document AI verification (PDF / JPEG / PNG / TIFF, up to 10 MB)
- Multi-document cross-verification (2–5 documents in one AI call — checks consistency across Title Deed, Aadhaar, Sale Agreement simultaneously)
- 3-layer fraud scoring: AI vision + 7 rule-based checks + national registry cross-check
- Explainable results: specific flags per fraud indicator, not just a score
- Automatic AI fallback chain: Nova Lite → Nova Pro → OpenAI GPT-4o-mini → Mock simulation

**National Property Registry**
- 16 properties across 8 Indian states (Karnataka, Maharashtra, Tamil Nadu, Delhi, Telangana, Gujarat, Rajasthan, West Bengal, Uttar Pradesh)
- Owner verification with fuzzy name matching ("R. Kumar" vs "Ravi Kumar")
- Encumbrance check: active mortgages, court orders, disputed land
- Full chain of title / ownership history per property
- Owner-based search (detect undisclosed holdings)
- MCP (Model Context Protocol) server — registry queryable by AI assistants

**Blockchain**
- SHA-256 hash-chained blocks stored in MongoDB (append-only)
- 10 transaction types covering full property lifecycle
- Property Passport: full blockchain history per property
- Chain integrity verification — detects any direct DB tampering
- Block explorer: look up any block by its SHA-256 hash

**Property Lifecycle**
- Property registration with Genesis block
- Negotiated deal flow: offer → accept → advance → monthly EMIs
- Auto-ownership transfer on-chain when buyer pays in full
- Ownership transfer with stamp duty and registration fee tracking
- Legal status updates (DISPUTED, ENCUMBERED, CLEARED, UNDER_LITIGATION)

**Fractional Ownership & Investment**
- Tokenize premium properties into investable shares (e.g., 1000 tokens at ₹5,500 each for a ₹55 lakh property)
- Investors buy % ownership — all holdings tracked on-chain
- Structured exit: sell tokens back, refund calculated at current token price
- Marketplace browsing: all fractional investment listings with available tokens

**Platform**
- JWT-based user authentication with Aadhaar-linked identity
- Real-time dashboard: properties, blocks, verifications, fraud prevented, investors, market value
- Full transaction history per property and platform-wide
- Portfolio view per investor

---

## SLIDE 4 — Process Flow Diagram

### Primary User Flow: Document Verification

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PROPCHAIN VERIFICATION PIPELINE                   │
└─────────────────────────────────────────────────────────────────────┘

  USER                    PROPCHAIN BACKEND                    AWS SERVICES
   │                            │                                    │
   │── Upload Document ─────────▶│                                    │
   │   (PDF / Image)             │── SHA-256 hash ──────────────────▶ │
   │                             │                              DynamoDB│
   │                             │◀─ Cache HIT? Return result ────────│
   │                             │                                    │
   │                             │ (Cache MISS)                       │
   │                             │                                    │
   │                             │── Convert PDF → JPEG pages ───────▶│
   │                             │   (PyMuPDF + Pillow)         Bedrock│
   │                             │── converse() API call ────────────▶│
   │                             │   (Nova Lite: vision + text)  Nova │
   │                             │◀─ Extracted fields + fraud score ──│
   │                             │                                    │
   │                             │── Cache result ──────────────────▶ │
   │                             │                              DynamoDB│
   │                             │                                    │
   │                             │── Layer 2: Run 7 Rule Checks       │
   │                             │   • Future date check              │
   │                             │   • Registration number format     │
   │                             │   • Name consistency               │
   │                             │   • Aadhaar format (12 digits)     │
   │                             │   • Amount format (numeric)        │
   │                             │   • Mandatory fields present       │
   │                             │   • Extraction confidence > 70%    │
   │                             │                                    │
   │                             │── Layer 3: Registry Cross-Check    │
   │                             │   • Look up survey/reg number      │
   │                             │   • Verify owner name              │
   │                             │   • Check encumbrances             │
   │                             │                                    │
   │                             │── Combine scores:                  │
   │                             │   final = AI + rules×0.08          │
   │                             │          + registry×0.10           │
   │                             │                                    │
   │                             │── Log result on blockchain         │
   │                             │   (DOCUMENT_VERIFICATION block)    │
   │                             │                                    │
   │◀── Verdict + Flags ─────────│                                    │
   │    AUTHENTIC / SUSPICIOUS   │                                    │
   │    / FLAGGED                │                                    │
```

---

### Deal Flow: Buyer → Seller → Auto Transfer

```
  BUYER           PROPCHAIN            SELLER        BLOCKCHAIN
    │                 │                   │               │
    │─ Make Offer ───▶│                   │               │
    │  (price, EMIs)  │── Notify seller ─▶│               │
    │                 │                   │               │
    │                 │◀── Accept ────────│               │
    │                 │                              DEAL_ACCEPTED block
    │─ Pay Advance ──▶│                                    │
    │                 │                         INSTALLMENT_PAYMENT block
    │─ Pay EMI 1 ────▶│                                    │
    │─ Pay EMI 2 ────▶│                                    │
    │       ...       │                                    │
    │─ Pay Final ────▶│                                    │
    │                 │── total_paid >= negotiated_price?  │
    │                 │   YES                              │
    │                 │── Update property owner in DB      │
    │                 │                         OWNERSHIP_TRANSFER block
    │◀─ "Ownership    │                                    │
    │    Transferred" │                                    │
```

---

## SLIDE 5 — Wireframes / Mock Diagrams

### Screen 1: Dashboard
```
┌────────────────────────────────────────────────────────────────┐
│  PropChain                           [Ravi Kumar ▼]  [Logout]  │
├──────────┬─────────────────────────────────────────────────────┤
│          │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│ Dashboard│  │ 24 Props │ │ 18 Verf  │ │ ₹12.4 Cr │ │ 89 Blk│ │
│ Propertis│  │Registered│ │ Verified │ │ Mkt Value│ │ On Chain│ │
│ AI Verify│  └──────────┘ └──────────┘ └──────────┘ └────────┘ │
│ Blockchain    ┌──────────────────────┐  ┌────────────────────┐ │
│ Deals    │    │  Fraud Prevented: 7  │  │ Active Investors: 3│ │
│ Marketplace   │  Verifications: 31   │  │ Fractional Props: 2│ │
│ Portfolio│    └──────────────────────┘  └────────────────────┘ │
│ Profile  │                                                      │
└──────────┴─────────────────────────────────────────────────────┘
```

### Screen 2: AI Document Verification
```
┌────────────────────────────────────────────────────────────────┐
│  AI Document Verification                                       │
├────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────┐  ┌────────────────────────────┐   │
│  │   Drop file here        │  │  Document Type             │   │
│  │   PDF / JPG / PNG       │  │  [Title Deed          ▼]   │   │
│  │   Max 10 MB             │  │                            │   │
│  └─────────────────────────┘  └────────────────────────────┘   │
│                    [Verify Document]                            │
├────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  VERDICT: ● FLAGGED          Fraud Score: 87/100         │  │
│  │  ─────────────────────────────────────────────────────── │  │
│  │  Extracted Fields:                                        │  │
│  │  Owner Name: Ravi Kumar (97%)  Survey No: 123/4A (95%)   │  │
│  │  Registration Date: 15/01/2027 (69%) ← SUSPICIOUS        │  │
│  │  ─────────────────────────────────────────────────────── │  │
│  │  Registry Checks:                                         │  │
│  │  ✗ Owner Mismatch — Registry shows 'Lakshmi Narayana'    │  │
│  │  ✗ Registration date is in the future (2027)             │  │
│  │  ✗ Registration number format invalid                     │  │
│  │  ─────────────────────────────────────────────────────── │  │
│  │  Verified by: Amazon Nova Lite · AWS Bedrock · us-east-1  │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
```

### Screen 3: Blockchain Explorer
```
┌────────────────────────────────────────────────────────────────┐
│  Blockchain Explorer               Chain Status: ● INTACT      │
├────────────────────────────────────────────────────────────────┤
│  Block #4   [OWNERSHIP_TRANSFER]   2024-01-15 10:32 AM         │
│  Hash: 57dd6473...fc9bc0e   Prev: b3f629...280af               │
│  From: Ravi Kumar → To: Priya Sharma   ₹55,00,000              │
├────────────────────────────────────────────────────────────────┤
│  Block #3   [DOCUMENT_VERIFICATION]  2024-01-15 10:28 AM       │
│  Hash: a168dd20...e1c97    Verdict: AUTHENTIC   Score: 0.04    │
├────────────────────────────────────────────────────────────────┤
│  Block #2   [DEAL_ACCEPTED]          2024-01-10 09:15 AM       │
│  Deal: DEAL-A3F2B1C4   Negotiated: ₹55,00,000                  │
├────────────────────────────────────────────────────────────────┤
│  Block #1   [DEAL_INITIATED]         2024-01-08 03:45 PM       │
│  Buyer: Priya Sharma   Advance: ₹5,00,000   EMIs: 12           │
├────────────────────────────────────────────────────────────────┤
│  Block #0   [GENESIS]                2024-01-05 11:00 AM       │
│  Hash: 7d711a27...b34590a   Owner: Ravi Kumar   1200 sq ft     │
└────────────────────────────────────────────────────────────────┘
```

---

## SLIDE 6 — Architecture Diagram

```
                    ┌─────────────────────────────────────────┐
                    │          USERS (Browser / Mobile)        │
                    └──────────────────┬──────────────────────┘
                                       │ HTTPS
                    ┌──────────────────▼──────────────────────┐
                    │          Amazon CloudFront               │
                    │   Global CDN · HTTPS Termination         │
                    │   SPA Error Handling (React Router)      │
                    └──────┬───────────────────┬──────────────┘
                           │ /* (frontend)      │ /api/* (backend)
              ┌────────────▼──────────┐  ┌──────▼────────────────────┐
              │      Amazon S3        │  │    AWS Fargate (ECS)       │
              │  React Build (Static) │  │    FastAPI · Python 3.12   │
              │  Private Bucket + OAC │  │    Docker · Port 8000      │
              └───────────────────────┘  └──┬──────┬────────┬────────┘
                                            │      │        │
                   ┌────────────────────────┘      │        └───────────────────┐
                   │                               │                            │
        ┌──────────▼───────────┐    ┌──────────────▼────────┐    ┌─────────────▼────────┐
        │   Amazon Bedrock     │    │    Amazon DynamoDB     │    │   AWS Secrets Manager │
        │                      │    │                        │    │                       │
        │  Nova Lite (primary) │    │  propchain-ai-cache    │    │  MONGODB_URL          │
        │  Nova Pro (fallback) │    │  SHA-256 → AI result   │    │  JWT_SECRET           │
        │  converse() API      │    │  7-day TTL             │    │  AWS_ACCESS_KEY_ID    │
        │  Vision + Text       │    │  On-demand billing     │    │  AWS_SECRET_ACCESS_KEY│
        └──────────────────────┘    └────────────────────────┘    └───────────────────────┘

        ┌──────────────────────┐    ┌──────────────────────────────────────────────────────┐
        │    Amazon ECR        │    │          MongoDB Atlas (External)                     │
        │  propchain-backend   │    │  Collections:                                        │
        │  Docker Image        │    │  • properties    • blockchain   • deals              │
        │  Lifecycle: keep 5   │    │  • transactions  • users        • fractional         │
        └──────────────────────┘    └──────────────────────────────────────────────────────┘

        ┌─────────────────────────────────────────────────────────────────────────────────┐
        │  MCP Server (Local / Future: SSE on Fargate)                                    │
        │  Indian Property Registry · 6 Tools · Queryable by AI assistants               │
        └─────────────────────────────────────────────────────────────────────────────────┘
```

**Data flow for document verification:**
`Upload → CloudFront → Fargate → DynamoDB (cache check) → Bedrock Nova (vision) → Rules Engine → Registry Check → MongoDB (blockchain write) → Response`

---

## SLIDE 7 — Technologies Used

### Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.12 | Core language |
| FastAPI | Latest | REST API framework, async |
| PyMuPDF (fitz) | Latest | PDF → JPEG page conversion |
| Pillow | Latest | Image processing, page stitching |
| Motor (AsyncIO MongoDB) | Latest | Async MongoDB driver |
| Pydantic v2 | Latest | Data validation |
| python-jose | Latest | JWT authentication |
| tenacity | Latest | Exponential backoff retry for Bedrock |
| boto3 | Latest | AWS SDK (Bedrock, DynamoDB, Secrets Manager) |
| python-dotenv | Latest | Environment config |
| MCP SDK | 1.0+ | Model Context Protocol server |

### Frontend
| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18 | UI framework |
| Vite | Latest | Build tool |
| Tailwind CSS | 3 | Styling |
| React Router | 6 | SPA routing |
| Axios | Latest | HTTP client |
| Recharts | Latest | Dashboard charts |
| React Hot Toast | Latest | Notifications |

### AWS Services
| Service | Tier / Config |
|---------|--------------|
| Amazon Bedrock — Nova Lite | `us.amazon.nova-lite-v1:0` · us-east-1 |
| Amazon Bedrock — Nova Pro | `us.amazon.nova-pro-v1:0` · us-east-1 (fallback) |
| AWS Fargate | 0.5 vCPU · 1 GB RAM |
| Amazon S3 | Standard · private · OAC |
| Amazon CloudFront | Price Class All |
| Amazon DynamoDB | On-demand · TTL enabled |
| AWS Secrets Manager | `propchain/config` |
| Amazon ECR | `propchain-backend` · lifecycle: 5 images |

### Infrastructure
| Tool | Purpose |
|------|---------|
| AWS CDK (Python) | Infrastructure as Code |
| Docker | Container packaging |
| MongoDB Atlas | Managed cloud database (free tier) |

---

## SLIDE 8 — Estimated Implementation Cost

### AWS Monthly Cost Estimate (Production — Medium Scale)

| Service | Configuration | Estimated Monthly Cost |
|---------|--------------|----------------------|
| **AWS Fargate** | 0.5 vCPU · 1 GB · 730 hrs/month | ~$15–20 |
| **Amazon Bedrock — Nova Lite** | ~1,000 verifications/month · avg 2,000 tokens/call | ~$2–5 |
| **Amazon Bedrock — Nova Pro** | ~50 fallback calls/month | ~$1–2 |
| **Amazon DynamoDB** | On-demand · ~1 GB cache storage | < $1 |
| **Amazon S3** | React build ~5 MB · static hosting | < $0.50 |
| **Amazon CloudFront** | 10 GB transfer/month | ~$1 |
| **AWS Secrets Manager** | 1 secret | $0.40 |
| **Amazon ECR** | < 1 GB storage | < $0.10 |
| **MongoDB Atlas** | Free tier (512 MB) | $0 |
| **Total** | | **~$20–30 / month** |

**Cost optimizations already built in:**
- **DynamoDB Bedrock cache** — same document never re-processed. 7-day TTL. Saves ~60–80% of Bedrock costs in real-world usage where documents are repeatedly uploaded.
- **Fargate desired_count=0** at idle — zero compute cost when no traffic.
- **CloudFront caching** for frontend — S3 bandwidth minimized.

**Hackathon (current) cost:** ~$0–5 total (free tier + minimal Bedrock calls during demo).

---

## SLIDE 9 — Snapshots of the Prototype

### Key screens to capture for the submission:

**1. Landing Page** — Hero section with PropChain branding and CTA

**2. Dashboard** — Real-time stats cards: properties, verified, blockchain blocks, fraud prevented, total market value, active investors

**3. AI Document Verification — FLAGGED result**
Upload a suspicious document → Show:
- Red FLAGGED badge with 87% fraud score
- Extracted fields with low-confidence highlights
- Registry flags: "REGISTRY: Owner mismatch — Registry shows 'Lakshmi Narayana'"
- Rule flags: "Future date detected: Registration Date: 15/01/2027"
- "Verified by: Amazon Nova Lite · AWS Bedrock · us-east-1"

**4. AI Document Verification — AUTHENTIC result**
Same screen with green AUTHENTIC badge, 96% trust score, all checks passed

**5. Cross-Document Verification**
Two documents uploaded → Nova cross-checks → Inconsistency shown: "Owner Name: 'R. Kumar' vs 'Ravi Kumar' — MEDIUM severity"

**6. Blockchain Explorer**
Property chain with 5 blocks visible — GENESIS → DOCUMENT_VERIFICATION → DEAL_INITIATED → DEAL_ACCEPTED → OWNERSHIP_TRANSFER

**7. Deal Flow**
Active deal card showing: negotiated price, advance paid, 3/12 EMIs paid, progress bar, "Pay Next EMI" button

**8. Marketplace**
Fractional investment listings — property cards with token price, available tokens, % remaining

**9. Property Passport**
Full property detail: owner, survey number, status (Verified), blockchain hash, complete transaction history

---

## SLIDE 10 — Prototype Performance Report / Benchmarking

### Verification Speed

| Mode | Average Time | Notes |
|------|-------------|-------|
| AWS Bedrock (Nova Lite) — cache miss | 2,800–4,500 ms | PDF → JPEG conversion + Nova call |
| AWS Bedrock (Nova Lite) — cache HIT | 80–120 ms | DynamoDB read only |
| AWS Bedrock (Nova Pro) — fallback | 5,000–8,000 ms | Larger model, slower |
| Mock mode | 10–50 ms | No external call |
| Processing time tracked | Yes | `processing_time_ms` in every response |

### Fraud Detection Accuracy (on mock test set)

| Scenario | Detected | Method |
|----------|---------|--------|
| Future registration date (2027) | ✓ | Rule: Future Date Check |
| Invalid Aadhaar (8 digits instead of 12) | ✓ | Rule: Aadhaar Format |
| Non-numeric consideration amount | ✓ | Rule: Amount Format |
| Owner name mismatch vs registry | ✓ | Registry: Owner Verification |
| Fabricated survey number (not in registry) | ✓ | Registry: Property Existence |
| Active mortgage not disclosed | ✓ | Registry: Encumbrance Check |
| Disputed / government land sold illegally | ✓ | Registry: Property Status |
| Tampered blockchain block (direct DB edit) | ✓ | Chain integrity re-hash |

### Resilience

| Failure Scenario | Response |
|-----------------|---------|
| Nova Lite throttled | Auto-retry (4×, exponential backoff 2–30s), then Nova Pro |
| Nova Pro throttled | OpenAI GPT-4o-mini fallback |
| All AI unavailable | Mock simulation — service never returns error to user |
| MongoDB down | FastAPI returns 503 |
| Bedrock cache unavailable | Silent skip — proceeds to live Bedrock call |

### Scale (current prototype limits)

| Parameter | Limit |
|-----------|-------|
| Max file size | 10 MB |
| Supported formats | PDF, JPEG, PNG, TIFF |
| Max pages per PDF (Nova) | 20 images (stitch if more) |
| Max docs per cross-verify | 5 |
| Blockchain blocks per property | Unlimited (append-only) |
| Registry properties (mock) | 16 across 8 states |

---

## SLIDE 11 — Additional Details / Future Development

### Phase 1 — Real Government API Integration (3–6 months)
- Connect to **DILRMP** (Digital India Land Records Modernisation Programme) API for live national records
- Integrate **state portals**: Bhoomi (Karnataka), Kaveri Online Services, MahaRERA, AP/TS IGRS
- Replace mock registry with live property data — same code, different data source

### Phase 2 — AI Agent Architecture (3–6 months)
The MCP (Model Context Protocol) server we built is the foundation. Instead of a single Bedrock call, an AI agent will:
1. Receive a document
2. Call `registry_lookup` tool to fetch ground truth before analyzing
3. Call `encumbrance_check` tool to verify property status
4. Use retrieved context to make a more informed, accurate assessment
This upgrades PropChain from "AI reads a document" to "AI agent investigates a property"

### Phase 3 — DigiLocker Integration (6–9 months)
Pull documents directly from the government's DigiLocker — Aadhaar, PAN, registered sale deeds. Government-issued documents cannot be forged. Eliminates the forgery risk entirely for supported document types.

### Phase 4 — True Distributed Ledger (9–12 months)
Replace the MongoDB mock blockchain with **Hyperledger Fabric** or an Indian government-approved DLT. Multiple parties (banks, SRO offices, registrars) become nodes — no single entity controls the chain.

### Phase 5 — Regulatory & Financial Integration
- RERA registration verification
- Auto stamp duty calculation by state
- e-Registration with SRO office APIs
- Home loan disbursement trigger: bank releases funds only after on-chain ownership transfer confirmed

### Already Built (Bonus Features)
- **MCP Server** — 6 tools exposing the property registry to AI assistants (Claude Desktop, Claude Code). Queryable via natural language. Production path: deploy with SSE transport on a separate Fargate service.
- **OpenAI fallback** — If all Bedrock capacity exhausted, GPT-4o-mini handles verification seamlessly
- **Fractional Ownership Marketplace** — Premium properties tokenized for small investor access
- **Full Deal Flow** — Complete negotiated purchase lifecycle with EMI tracking on-chain

---

## SLIDE 12 — Prototype Assets

### GitHub Public Repository
`[INSERT GITHUB URL]`

Repository contains:
- `backend/` — FastAPI backend (Python 3.12)
- `frontend/` — React + Vite + Tailwind UI
- `infra/` — AWS CDK stack (Python) — complete IaC for one-command deploy
- `mcp_server/` — MCP server for AI assistant registry access

### Demo Video
`[INSERT YOUTUBE / DRIVE LINK]` (Max 3 minutes)

Suggested demo flow for video:
1. (0:00–0:30) Dashboard overview — live stats
2. (0:30–1:15) Upload a flagged document → show 3-layer fraud detection in action
3. (1:15–1:45) Cross-document verification — two docs, name inconsistency caught
4. (1:45–2:15) Blockchain explorer — full property passport, chain integrity verified
5. (2:15–2:45) Deal flow — offer, accept, pay, auto-transfer
6. (2:45–3:00) Architecture callout — AWS services used

### Live Prototype URL
`[INSERT CLOUDFRONT URL]`

### Team
OpsAI Team
Contact: team@propchain.ai
