# PropChain — PPT Content
# AI for Bharat Hackathon | Powered by AWS

---

## SLIDE 1 — TITLE

**PropChain**
*Blockchain + AI-Powered Property Verification for Bharat*

Tagline: *"From forged deed to verified truth — in seconds."*

Team: OpsAI
Hackathon: AI for Bharat | Powered by AWS

---

## SLIDE 2 — THE PROBLEM

### Property Fraud is India's Most Costly Silent Crime

**Scale:**
- India registers ~1.2 crore property transactions annually
- Property fraud accounts for 30–40% of all civil court disputes in India
- Estimated ₹1 lakh crore+ in disputed property value across Indian courts

**Root causes (3 bullets):**
1. **Unstructured documents** — Title deeds, sale agreements, and encumbrance certificates are scanned paper documents. There is no machine-readable standard.
2. **Siloed land records** — State portals (Bhoomi, Kaveri, DILRMP) exist in isolation. A buyer in Delhi cannot easily check Karnataka records.
3. **No buyer-side verification** — A buyer has no way to know if a document is genuine, if the seller actually owns the property, or if it is mortgaged to a bank.

**Real fraud scenarios this project catches:**
- Seller presents a forged Title Deed with a future registration date
- Fraudster claims ownership of a property that belongs to someone else
- Property with an active ₹50 lakh bank mortgage is sold as "clear"
- Same property sold to multiple buyers using slightly altered documents

---

## SLIDE 3 — SOLUTION OVERVIEW

### PropChain: 3 Things in One Platform

**Visual: Three pillars**

```
   [AI Fraud Detection]   [Blockchain Audit Trail]   [National Registry Check]
         |                         |                          |
   Upload document          Every transaction          Cross-check owner,
   → AI reads it            → immutable block          survey number,
   → fraud score            → tamper-proof             encumbrances vs
   → flags raised           → permanent record         national database
```

**One sentence:**
> PropChain gives every property a tamper-proof digital identity, verifies documents with AI vision, and cross-checks claims against a national property registry — preventing fraud before it happens.

**Who benefits:**
- **Buyers** — Know the property is real, unencumbered, and the seller is the true owner
- **Sellers** — Establish authenticated ownership history, increase buyer confidence
- **Banks / Lenders** — AI-verified documents before releasing home loans
- **Government** — Digitize and audit property records on an immutable chain

---

## SLIDE 4 — HOW IT WORKS (USER JOURNEY)

### The PropChain Flow

**Step 1 — Register**
Owner registers a property → Genesis block minted on blockchain → Property gets a unique ID and permanent digital identity

**Step 2 — Verify Documents**
Upload Title Deed, Aadhaar, Encumbrance Certificate → AI reads the document (AWS Bedrock Nova) → 3-layer fraud analysis → Result logged on-chain

**Step 3 — List & Negotiate**
Verified properties appear on marketplace → Buyer makes a negotiated offer → Seller accepts → Deal terms recorded on-chain

**Step 4 — Pay & Transfer**
Buyer pays advance + monthly EMIs, each payment logged as a blockchain block → When fully paid, **ownership transfers automatically on-chain** — no manual process

**Step 5 — Invest (Fractional)**
Premium properties (hospitals, warehouses, commercial spaces) tokenized into shares → Small investors buy tokens → All holdings tracked on-chain

---

## SLIDE 5 — THE CORE: 3-LAYER FRAUD DETECTION

### Why One Layer Is Never Enough

| Layer | What It Checks | What It Catches | Powered By |
|-------|---------------|-----------------|------------|
| **Layer 1: AI Vision** | Reads every pixel of the document | Tampered images, inconsistent fields, suspicious formatting, digital editing artifacts | AWS Bedrock (Amazon Nova Lite) |
| **Layer 2: Rule Engine** | 7 deterministic rules on extracted fields | Future registration dates, invalid Aadhaar (not 12 digits), non-numeric amounts, missing mandatory fields, low-confidence extractions | PropChain Rules Engine |
| **Layer 3: Registry Cross-Check** | Compares extracted fields vs national database | **Wrong owner name, fabricated survey number, active mortgage hidden from buyer, government/disputed land** | National Property Registry (16 properties, 8 states) |

**The key insight:**
> A fraudster can forge a *perfectly formatted* document that passes Layer 1 and Layer 2. Only Layer 3 — comparing against ground truth — catches it. A fake Title Deed showing "Ravi Kumar" as owner fails immediately when the registry shows the property belongs to "Lakshmi Narayana".

**Final Fraud Score formula:**
```
fraud_score = AI_score + (rule_flags × 0.08) + (registry_flags × 0.10)

AUTHENTIC  → score < 0.35
SUSPICIOUS → score 0.35–0.65
FLAGGED    → score > 0.65
```

---

## SLIDE 6 — AI PIPELINE DEEP DIVE

### How AWS Bedrock Powers the Verification

**The pipeline (single Bedrock call):**

```
PDF / Image Upload
       ↓
SHA-256 hash → DynamoDB cache check (7-day TTL)
       ↓ (cache miss)
PyMuPDF converts PDF → JPEG pages
       ↓
Pages stitched if > 20 images (Nova API limit)
       ↓
Amazon Bedrock Nova Lite
converse() API — vision + text in one call
       ↓
Structured JSON response:
{
  extracted_fields: [...],
  fraud_indicators: [...],
  fraud_score: 0.05,
  overall_assessment: "AUTHENTIC"
}
       ↓
Rule engine runs on extracted_fields
Registry cross-check runs on extracted_fields
       ↓
Combined verdict + blockchain logging
```

**Automatic fallback chain (resilience):**
```
Nova Lite → [throttled?] → Nova Pro → [throttled?] → OpenAI GPT-4o-mini → Mock
```

**Cross-Document Verification:**
Upload 2–5 documents simultaneously. Nova reads ALL of them in a single call and cross-checks:
- Owner name consistency across Title Deed + Aadhaar + Sale Agreement
- Survey/plot number matches
- Financial amounts (sale deed vs agreement must match)
- Date logic (registration before transfer)

**Why this is RAG:**
> The AI *generates* field extractions from unstructured documents (Generation), which are used to *retrieve* ground-truth records from the property registry (Retrieval), producing an *augmented* fraud verdict (Augmented Generation) that neither source alone could produce.

---

## SLIDE 7 — BLOCKCHAIN ARCHITECTURE

### Every Property Gets an Immutable Digital Identity

**Block structure:**
```json
{
  "block_index": 2,
  "property_id": "PROP-ABC12345",
  "transaction_type": "OWNERSHIP_TRANSFER",
  "data": { "from_owner": "Ravi Kumar", "to_owner": "Priya Sharma", "sale_price": 5500000 },
  "previous_hash": "b3f629ac19b7398...",
  "timestamp": "2024-01-15T10:30:00",
  "hash": "SHA256(block_index + property_id + data + previous_hash + timestamp)"
}
```

**10 Transaction Types tracked on-chain:**

| Type | Triggered By |
|------|-------------|
| GENESIS | First property registration |
| OWNERSHIP_TRANSFER | Buyer ↔ Seller transfer |
| DOCUMENT_VERIFICATION | AI fraud check result |
| STATUS_UPDATE | Legal status change (DISPUTED, ENCUMBERED) |
| DEAL_INITIATED | Buyer makes offer |
| DEAL_ACCEPTED | Seller confirms deal |
| INSTALLMENT_PAYMENT | Each EMI payment |
| FRACTIONAL_MINT | Property tokenized |
| FRACTIONAL_TRANSFER | Tokens sold to investor |
| FRACTIONAL_REDEEM | Investor exits position |

**Tamper detection:**
Every `GET /blockchain/verify/{property_id}` replays the entire chain — recomputes each SHA-256 hash and checks linkage. Direct database tampering is detected instantly.

**Key design choice:**
The document itself is never stored. Only its SHA-256 hash + AI verdict are written on-chain. Privacy preserved, audit trail intact.

---

## SLIDE 8 — NATIONAL PROPERTY REGISTRY

### India's Missing Layer — A Ground Truth Database

**The gap today:**
State portals (Bhoomi, Kaveri, DILRMP) contain the ground truth but are not queryable by common citizens in real-time. PropChain bridges this with a structured registry.

**What's in the registry (mock data, 16 properties across 8 states):**

| State | Properties | Includes |
|-------|-----------|---------|
| Karnataka | 5 | 1 disputed (court order), 1 fraud demo |
| Maharashtra | 2 | 1 with active SBI mortgage |
| Tamil Nadu | 2 | Clean records |
| Delhi | 1 | Clean record |
| Telangana | 1 | ICICI Bank mortgage |
| Gujarat | 1 | Clean record |
| Rajasthan | 1 | Clean record |
| West Bengal | 1 | Clean record |
| Uttar Pradesh | 1 | PNB mortgage |

**5 Registry checks per verification:**
1. **Property existence** — Does this survey/registration number exist?
2. **Owner verification** — Does the claimed owner match the registered owner? (fuzzy match handles "R. Kumar" vs "Ravi Kumar")
3. **Encumbrance check** — Active mortgage? Court order? Disputed status?
4. **Ownership history** — Full chain of title with all previous owners
5. **Owner search** — All properties under a name (detects undisclosed holdings)

**MCP Server:**
The registry is also exposed as a Model Context Protocol (MCP) server with 6 tools — enabling AI assistants (Claude Desktop, Claude Code) to query property records via natural language. This is the production integration path with real government APIs.

---

## SLIDE 9 — DEAL FLOW & FRACTIONAL OWNERSHIP

### Complete Property Transaction Lifecycle

**Deal Flow (Negotiated Purchase):**
```
Buyer sees Verified property
    → Makes offer (negotiated_price, advance_amount, installments)
    → DEAL_INITIATED block minted
    → Seller accepts → DEAL_ACCEPTED block
    → Buyer pays advance → INSTALLMENT_PAYMENT block
    → Monthly EMIs → each logged on-chain
    → Final payment → OWNERSHIP_TRANSFER auto-triggered
    → Property ownership updated in DB + blockchain simultaneously
```

Smart rules enforced:
- Buyers cannot make offers on their own properties
- Only one active deal per property at a time (no double-dealing)
- Advance must be less than total negotiated price
- Pay-full option: buyer can clear remaining balance in one shot

**Fractional Ownership (Investment):**
```
Owner tokenizes property → 1000 tokens at ₹X each
Investors buy tokens (% of property)
Each purchase → FRACTIONAL_TRANSFER block
Investors can sell tokens back (FRACTIONAL_REDEEM)
All holdings tracked in real-time
```

Use case: A ₹5 crore commercial warehouse becomes accessible to 50 small investors at ₹1 lakh each. Each investor holds on-chain proof of their stake.

---

## SLIDE 10 — AWS ARCHITECTURE

### Built Entirely on AWS

```
                            ┌─────────────────────────────┐
                            │       Amazon CloudFront      │
                            │   CDN + API Proxy (HTTPS)    │
                            └────────┬────────────┬────────┘
                                     │            │
                          /* (SPA)   │            │ /api/*
                                     ▼            ▼
                            ┌──────────┐  ┌───────────────────┐
                            │ Amazon   │  │   AWS Fargate      │
                            │   S3     │  │   (ECS Cluster)    │
                            │  React   │  │   FastAPI :8000    │
                            │  Build   │  │   Docker Container │
                            └──────────┘  └────────┬──────────┘
                                                   │
                    ┌──────────────────────────────┼──────────────────────────────┐
                    │                              │                              │
                    ▼                              ▼                              ▼
         ┌──────────────────┐         ┌────────────────────┐         ┌───────────────────┐
         │  Amazon Bedrock  │         │   Amazon DynamoDB  │         │  AWS Secrets Mgr  │
         │  Nova Lite (AI)  │         │  Bedrock Cache     │         │  MongoDB URL      │
         │  Nova Pro (fallback)│      │  7-day TTL         │         │  JWT Secret       │
         └──────────────────┘         └────────────────────┘         │  AWS Keys         │
                                                                      └───────────────────┘
                                      ┌────────────────────┐
                                      │    Amazon ECR      │
                                      │  Docker Image Repo │
                                      └────────────────────┘

                            MongoDB Atlas (external)
                            Properties, Blockchain, Deals, Users
```

**Security:**
- CloudFront terminates all HTTPS — backend never exposed to internet directly
- Secrets Manager injects credentials as environment variables — no hardcoded secrets
- ECS Task Role with least-privilege Bedrock + DynamoDB permissions only
- JWT authentication on all protected routes

---

## SLIDE 11 — AWS SERVICES USED

### Answering the Criteria: How AWS Powers PropChain

| AWS Service | How Used | Why It Matters |
|-------------|----------|---------------|
| **Amazon Bedrock** (Nova Lite + Nova Pro) | Vision-based document fraud analysis via `converse()` API. Nova reads PDF/image pages directly. | Core AI — no other service can read and reason about scanned property documents this way |
| **Amazon ECS / Fargate** | Runs the entire FastAPI backend as a Docker container — serverless compute, no EC2 to manage | Auto-scaling, zero server management for hackathon team |
| **Amazon S3** | Hosts the React frontend build. Private bucket, CloudFront OAC for access | Static hosting at scale, zero cost for traffic spike |
| **Amazon CloudFront** | Serves frontend from S3 AND proxies `/api/*` to Fargate over HTTP | Single domain for frontend + API, HTTPS termination, global CDN |
| **Amazon DynamoDB** | Bedrock response cache: `hash(document) → AI result`, 7-day TTL | Zero model cost on repeated document uploads. Saves Bedrock credits |
| **AWS Secrets Manager** | Stores MongoDB URL, JWT secret, AWS credentials — injected at container startup | No secrets in code or environment files |
| **Amazon ECR** | Docker image registry for the backend container | CI/CD-ready image storage with lifecycle rules (keep last 5 images) |

**Using Generative AI on AWS — evaluation answer:**
- **Why AI is required:** Property documents are unstructured scanned images — rule-based systems cannot read them. Only a vision-capable LLM can extract fields and reason about fraud from raw pixels.
- **How AWS services are used:** Amazon Bedrock `converse()` API with Nova Lite for vision + text understanding in a single call. DynamoDB caches results for cost efficiency.
- **What value AI adds:** Turns a 3-day manual verification process into a 2-second automated fraud score with specific, actionable flags — and a permanent on-chain audit trail.

---

## SLIDE 12 — LIVE DEMO WALKTHROUGH

### What Evaluators Will See

**Screen 1 — Dashboard**
Real-time stats: properties registered, blockchain blocks, verifications performed, fraud prevented count, total market value on platform

**Screen 2 — Register Property**
Fill in property details (survey number, address, area, Aadhaar) → Genesis block minted → Property ID generated → Transaction hash displayed

**Screen 3 — AI Verify (the star feature)**
Upload any PDF/image document → Select document type → Watch the 3-layer analysis run:
- AI extracts: Owner Name, Survey Number, Registration Date, Consideration Amount
- Rule checks: all 7 rules evaluated with pass/fail
- Registry check: "REGISTRY: Owner mismatch — Registry shows 'Lakshmi Narayana', document claims 'Ravi Kumar'"
- Final verdict: FLAGGED | Fraud Score: 0.87

**Screen 4 — Cross-Verify**
Upload Title Deed + Aadhaar Card simultaneously → Nova reads both in one call → "Name inconsistency detected: 'R. Kumar' vs 'Ravi Kumar' — MEDIUM severity"

**Screen 5 — Blockchain Explorer**
Live block list, each with transaction type badge, hash, timestamp → Verify chain integrity → Every document verification permanently recorded

**Screen 6 — Deal Flow**
Make an offer on a verified property → Accept → Pay advance → EMI progression → Ownership auto-transfer on full payment

**Screen 7 — Marketplace / Portfolio**
Fractional investment listings, token purchase, portfolio view

---

## SLIDE 13 — IMPACT & SCALE

### Why This Matters for Bharat

**Immediate impact:**
- A first-time home buyer gets a 2-second AI verdict instead of a 3-day advocate review
- A bank gets AI-verified documents before releasing a home loan
- A seller proves clean ownership history, increasing buyer confidence and property value

**Numbers (platform demo):**
- 8 states covered in property registry
- 16 property records with realistic fraud scenarios
- 10 blockchain transaction types covering full property lifecycle
- 3-layer fraud detection (AI + rules + registry)
- < 3 seconds average verification time
- 0 Bedrock cost on repeat uploads (DynamoDB cache)

**Production path:**
| Component | Demo (Today) | Production |
|-----------|-------------|------------|
| Registry | 16 mock properties | DILRMP API integration |
| AI Model | Nova Lite (us-east-1) | Nova Pro with higher quota |
| Blockchain | MongoDB-backed mock | Hyperledger / actual DLT |
| Auth | JWT | Aadhaar-based DigiLocker eSign |
| MCP Server | Local stdio | SSE transport on Fargate |

---

## SLIDE 14 — FUTURE ROADMAP

### From Hackathon to Production

**Phase 1 — Registry Integration**
Connect to real DILRMP API, Kaveri Online Services (Karnataka), MahaRERA (Maharashtra), and state-specific portals via standardized adapter layer

**Phase 2 — Agent-Based Verification**
Replace single Bedrock call with an AI agent that:
- Calls `registry_lookup` tool to fetch ground truth
- Calls `encumbrance_check` tool before analyzing the document
- Uses retrieved context to make a more accurate fraud assessment
*(The MCP server we built is the foundation for this)*

**Phase 3 — DigiLocker Integration**
Pull documents directly from DigiLocker (government-verified) — eliminates document forgery risk entirely for Aadhaar, PAN, and registered deeds

**Phase 4 — Regulatory Compliance**
RERA integration, stamp duty calculation, e-registration with SRO office APIs

---

## SLIDE 15 — TEAM

**OpsAI Team**

[Team member names, roles, contact]

Built for: AI for Bharat Hackathon | Powered by AWS
GitHub: [repository link]
Live Demo: [CloudFront URL]
