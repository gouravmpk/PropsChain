# PropChain — Full System Workflow

## 1. Infrastructure Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                          AWS (ap-south-1)                            │
│                                                                      │
│  User Browser                                                        │
│      │                                                               │
│      ▼                                                               │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                   CloudFront CDN                             │    │
│  │            d35swpqfjmv67g.cloudfront.net                    │    │
│  │                                                              │    │
│  │   /* (default)  ──────────►  S3 Bucket                      │    │
│  │                              propchain-frontend-264982087490 │    │
│  │                              (React build artifacts)         │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  React App (browser) ──VITE_API_URL──► Fargate Public IP:8000       │
│                                             │                        │
│                                    ┌────────▼────────┐              │
│                                    │  ECS Fargate     │              │
│                                    │  FastAPI :8000   │              │
│                                    │  propchain       │              │
│                                    │  cluster         │              │
│                                    └────────┬────────┘              │
│                                             │                        │
│                          ┌──────────────────┼──────────────┐        │
│                          ▼                  ▼              ▼        │
│                    ┌──────────┐    ┌──────────────┐  ┌──────────┐  │
│                    │ MongoDB  │    │ AWS Bedrock  │  │ Secrets  │  │
│                    │ Atlas    │    │ Nova Pro     │  │ Manager  │  │
│                    │ (remote) │    │(ap-south-1)  │  │propchain │  │
│                    └──────────┘    └──────────────┘  │/config   │  │
│                                                       └──────────┘  │
│                                                                      │
│  ECR: propchain-backend (Docker image storage)                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 2. MongoDB Collections

```
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│    users         │   │   properties     │   │ transactions     │
│─────────────────│   │─────────────────│   │─────────────────│
│ id              │   │ id (PROP-xxxx)  │   │ type            │
│ name            │   │ title           │   │ property_id     │
│ email (unique)  │   │ owner_name      │   │ from / to       │
│ password (hash) │   │ status          │   │ amount          │
│ phone           │   │ market_value    │   │ timestamp       │
│ aadhaar         │   │ fraud_score     │   │ block_hash      │
│ kyc_verified    │   │ fractional_     │   └─────────────────┘
│ wallet_balance  │   │  enabled        │
└─────────────────┘   │ total_tokens    │   ┌─────────────────┐
                      │ available_tokens│   │fractional_      │
                      │ token_price     │   │holdings         │
                      └─────────────────┘   │─────────────────│
                                            │ property_id     │
┌─────────────────────────────────────────┐ │ email           │
│         blockchain_ledger                │ │ tokens          │
│─────────────────────────────────────────│ │ invested        │
│ property_id                             │ │ date            │
│ block_index  (unique per property)      │ └─────────────────┘
│ transaction_type (GENESIS|TRANSFER|...) │
│ data         (JSON payload)             │
│ previous_hash                           │
│ hash         (SHA-256, unique globally) │
│ timestamp                               │
└─────────────────────────────────────────┘
```

---

## 3. Property Lifecycle (Core Flow)

```
                        REGISTER
                           │
                    POST /properties/register
                           │
              ┌────────────▼────────────────┐
              │  Generate PROP-xxxx ID       │
              │  Compute fraud_score (1-20)  │
              │  status = Verified / Review  │
              │  Insert → properties         │
              │  Insert → transactions       │
              └────────────┬────────────────┘
                           │ mint_genesis()
                    ┌──────▼──────────────────────────────────┐
                    │  BLOCKCHAIN BLOCK 0 (GENESIS)            │
                    │  block_index = 0                         │
                    │  previous_hash = 000...0 (64 zeros)      │
                    │  data: owner, address, area, value       │
                    │  hash = SHA256(0 + prop_id + data + ts)  │
                    └─────────────────────────────────────────┘
                           │
                    ┌──────▼───────────────────────────────────┐
                    │         VERIFY DOCUMENT (optional)        │
                    │  POST /ai/verify                          │
                    │    │  Upload PDF/Image                    │
                    │    ▼                                      │
                    │  AWS Bedrock Nova Pro (ap-south-1)        │
                    │    │  Extract fields, detect fraud        │
                    │    ▼                                      │
                    │  Rule-based checks overlay               │
                    │    │                                      │
                    │    ▼                                      │
                    │  fraud_score (0.0-1.0)                   │
                    │  verdict: AUTHENTIC / SUSPICIOUS / FLAGGED│
                    │    │                                      │
                    │    └─► BLOCKCHAIN BLOCK N                 │
                    │         type: DOCUMENT_VERIFICATION       │
                    │         data: doc_hash, score, verdict    │
                    └──────────────────────────────────────────┘
                           │
              ┌────────────▼────────────┐
              │      TRANSFER (Sale)    │ ◄── OR ──► TOKENIZE
              │  POST /properties/      │            (next section)
              │    {id}/transfer        │
              └────────────┬────────────┘
                           │ add_transaction()
                    ┌──────▼──────────────────────────────────┐
                    │  BLOCKCHAIN BLOCK N+1 (OWNERSHIP_TRANSFER)│
                    │  data: from_owner, to_owner, sale_price  │
                    │  previous_hash = hash of block N         │
                    └─────────────────────────────────────────┘
```

---

## 4. Fractional Ownership Flow

```
                    TOKENIZE (Owner only)
                           │
              POST /properties/{id}/enable-fractional
                    ?total_tokens=2000
                           │
              ┌────────────▼────────────────┐
              │  token_price = market_value  │
              │               / total_tokens │
              │  available_tokens = 2000     │
              │  fractional_enabled = true   │
              │  Update → properties         │
              └────────────┬────────────────┘
                           │ add_transaction()
                    ┌──────▼──────────────────────────────────┐
                    │  BLOCKCHAIN BLOCK N (FRACTIONAL_MINT)    │
                    │  data: total_tokens, token_price, symbol │
                    └─────────────────────────────────────────┘
                           │
                           │
              ┌────────────▼────────────────┐
              │          INVEST              │
              │  POST /fractional/invest     │
              │  { property_id,              │
              │    fraction_percent: 5,      │
              │    investor_email }          │
              └────────────┬────────────────┘
                           │
              ┌────────────▼────────────────┐
              │  tokens = (5/100)*2000 = 100 │
              │  amount = 100 * token_price  │
              │  Insert → fractional_holdings│
              │  Decrement available_tokens  │
              │  Insert → transactions       │
              └────────────┬────────────────┘
                           │ add_transaction()
                    ┌──────▼──────────────────────────────────┐
                    │  BLOCKCHAIN BLOCK N+1 (FRACTIONAL_TRANSFER)│
                    │  data: investor_email, tokens, amount    │
                    └─────────────────────────────────────────┘
                           │
                           │
              ┌────────────▼────────────────┐
              │    STRUCTURED EXIT (Sell)    │
              │  POST /fractional/sell       │
              │  { property_id,              │
              │    investor_email,           │
              │    tokens_to_sell: 50 }      │
              └────────────┬────────────────┘
                           │
              ┌────────────▼────────────────┐
              │  refund = 50 * token_price   │
              │  Update/Delete → holdings    │
              │  Increment available_tokens  │
              │  Insert → transactions       │
              └────────────┬────────────────┘
                           │ add_transaction()
                    ┌──────▼──────────────────────────────────┐
                    │  BLOCKCHAIN BLOCK N+2 (FRACTIONAL_REDEEM)│
                    │  data: investor_email, tokens, refund    │
                    └─────────────────────────────────────────┘
```

---

## 5. Blockchain Hash Chain (Per Property)

```
  ┌──────────────────────────┐
  │  BLOCK 0  (GENESIS)      │
  │  index:  0               │
  │  prev:   000...0         │◄─── genesis anchor
  │  data:   {property meta} │
  │  hash:   abc123...       │──┐
  └──────────────────────────┘  │ previous_hash
                                 ▼
  ┌──────────────────────────┐
  │  BLOCK 1  (DOC_VERIFY)   │
  │  index:  1               │
  │  prev:   abc123...       │◄─── must match block 0 hash
  │  data:   {fraud_score}   │
  │  hash:   def456...       │──┐
  └──────────────────────────┘  │ previous_hash
                                 ▼
  ┌──────────────────────────┐
  │  BLOCK 2  (TRANSFER)     │
  │  index:  2               │
  │  prev:   def456...       │◄─── must match block 1 hash
  │  data:   {from, to, ₹}   │
  │  hash:   ghi789...       │──┐
  └──────────────────────────┘  │
                                 ▼
                              ...N blocks

  hash = SHA-256(block_index + property_id + data + previous_hash + timestamp)

  Tamper detection: GET /blockchain/verify/{property_id}
  → recomputes each hash; mismatch → COMPROMISED
```

---

## 8-A. AI Document Verification Pipeline

```
  User uploads PDF/Image
          │
          ▼
  POST /ai/verify (multipart/form-data)
          │
  ┌───────▼──────────────────────────────────────┐
  │  1. Compute SHA-256 hash of file              │
  │  2. Detect format (PDF / PNG / JPEG / TIFF)   │
  │  3. Convert to JPEG pages (max 20 pages)      │
  │     (PyMuPDF for PDF, Pillow for images)      │
  └───────┬──────────────────────────────────────┘
          │
          ▼
  ┌───────────────────────────────────────────────┐
  │  AWS Bedrock — Nova Pro (ap-south-1)          │
  │  Model: apac.amazon.nova-pro-v1:0             │
  │  API:   bedrock.converse()                    │
  │                                               │
  │  Prompt asks Nova to:                         │
  │  - Extract fields (names, dates, values)      │
  │  - Detect fraud indicators                    │
  │  - Score confidence per field                 │
  │  - Return structured JSON                     │
  └───────┬───────────────────────────────────────┘
          │
          ▼
  ┌───────────────────────────────────────────────┐
  │  Rule-Based Overlay (fraud_rules.py)          │
  │  - Missing mandatory fields → +penalty        │
  │  - Suspiciously round values → +penalty       │
  │  - Date inconsistencies → +penalty            │
  │  - Conflicting names → +penalty               │
  └───────┬───────────────────────────────────────┘
          │
          ▼
  ┌───────────────────────────────────────────────┐
  │  Final Aggregation                            │
  │  fraud_score = AI_score + rule_penalties      │
  │  verdict:                                     │
  │    < 0.35  → AUTHENTIC  ✅                    │
  │    0.35-0.65 → SUSPICIOUS ⚠️                 │
  │    > 0.65  → FLAGGED ❌                       │
  └───────┬───────────────────────────────────────┘
          │
          ▼
  Log on blockchain (DOCUMENT_VERIFICATION block)
  Return result to frontend
```

---

## 7-A. API Route Map

```
  /api
  ├── /auth
  │   ├── POST /register          → create user, return JWT
  │   ├── POST /login             → verify password, return JWT
  │   └── GET  /me                → decode JWT, return user
  │
  ├── /properties
  │   ├── GET  /                  → list with filters (city, status, type)
  │   ├── GET  /{id}              → property passport + fractional holders
  │   ├── POST /register          → register + GENESIS block
  │   ├── POST /{id}/transfer     → ownership transfer + TRANSFER block
  │   └── POST /{id}/enable-fractional → tokenize + FRACTIONAL_MINT block
  │
  ├── /fractional
  │   ├── POST /invest            → buy tokens + FRACTIONAL_TRANSFER block
  │   └── POST /sell              → exit tokens + FRACTIONAL_REDEEM block
  │
  ├── /marketplace
  │   └── GET  /                  → list tokenized properties for investing
  │
  ├── /blockchain
  │   ├── GET  /                  → recent 50 blocks (all properties)
  │   ├── GET  /verify            → chain health check (last 20 blocks)
  │   ├── GET  /verify/{prop_id}  → per-property tamper detection
  │   ├── GET  /passport/{prop_id}→ full history + current owner/status
  │   ├── GET  /block/{hash}      → block explorer lookup
  │   ├── GET  /properties        → list all on-chain properties
  │   ├── POST /mint              → direct genesis block (raw)
  │   ├── POST /transfer          → direct transfer block (raw)
  │   ├── POST /verify-document   → log AI verification on-chain
  │   ├── POST /status            → log status update on-chain
  │   ├── POST /fractional/mint   → direct fractional mint (raw)
  │   └── POST /fractional/transfer → direct fractional transfer (raw)
  │
  ├── /ai
  │   ├── POST /verify            → single document AI analysis
  │   ├── POST /cross-verify      → multi-document consistency check
  │   └── GET  /mode              → check AWS/mock mode
  │
  └── /dashboard
      ├── GET  /stats             → platform KPIs (properties, value, etc.)
      ├── GET  /transactions      → all platform transactions
      └── GET  /transactions/{id} → transactions for one property
```

---

## 8. Transaction Types

```
  ┌──────────────────────┬──────────────────────────────────────────┐
  │  Type                │  Triggered by                            │
  ├──────────────────────┼──────────────────────────────────────────┤
  │  GENESIS             │  POST /properties/register               │
  │  OWNERSHIP_TRANSFER  │  POST /properties/{id}/transfer          │
  │  DOCUMENT_VERIFICATION│ POST /ai/verify (then logged on-chain)  │
  │  STATUS_UPDATE       │  POST /blockchain/status                 │
  │  FRACTIONAL_MINT     │  POST /properties/{id}/enable-fractional │
  │  FRACTIONAL_TRANSFER │  POST /fractional/invest                 │
  │  FRACTIONAL_REDEEM   │  POST /fractional/sell                   │
  └──────────────────────┴──────────────────────────────────────────┘
```

---

## 9. Frontend Page → API Map

```
  Page               Component Action          API Call               Error Handling
  ────────────────────────────────────────────────────────────────────────────────────
  Landing            Load stats               GET /dashboard/stats   try/catch + log
  Login/Register     Auth forms               POST /auth/login|register
                     Token stores in localStorage (48-byte JWT)
  Dashboard          KPI cards                GET /dashboard/stats   Auto data generation
                     Transactions list        GET /dashboard/transactions
                     Area chart (dynamic)     Computed from stats
                     Pie chart (dynamic)      Computed from stats
  Marketplace        Fractional listings      GET /marketplace       try/catch + log
                     Buy Properties tab       GET /properties?status=Verified
                     Invest button            POST /fractional/invest with toast feedback
                     Buy button               POST /properties/{id}/transfer
  Properties         Browse all              GET /properties        try/catch + log
  PropertyDetail     View property            GET /properties/{id}   try/catch + log
                     Transfer (owner)         POST /properties/{id}/transfer
                     Tokenize (owner)         POST /properties/{id}/enable-fractional
                     Buy (non-owner)          POST /properties/{id}/transfer (full price)
                     Invest (fractional)      POST /fractional/invest
                     View blockchain hash     fmt.shortHash() display + copy
                     See transactions         GET /transactions/{id}
  AI Verify          Upload doc              POST /ai/verify
                     Cross-verify docs       POST /ai/cross-verify
  Blockchain         View chain              GET /blockchain        [...array].reverse()
                     Search by hash          GET /blockchain/block/{hash}
                     Verify integrity        GET /blockchain/verify
                     Display full hashes     fmt.shortHash() + title tooltip
  Portfolio          My properties           GET /properties (filter by owner_name)
                     My token holdings       Computed from fractional_holdings
                     Sell tokens             POST /fractional/sell (with refund)
  Profile            User info               GET /auth/me
  
  401 Handling: All responses intercepted → auto-logout + redirect to /login (localStorage cleared)
  ────────────────────────────────────────────────────────────────────────────────────
```

---

## 10. Frontend Implementation Details

### Auth Flow & Token Management

```
┌──────────────────────────────────────────────────────────────┐
│  Browser → localStorage                                      │
│  ┌────────────────┐  ┌────────────────────────────────────┐ │
│  │propchain_token │  │propchain_user                      │ │
│  │(JWT from API)  │  │{id, name, email, wallet_balance}  │ │
│  └────────────────┘  └────────────────────────────────────┘ │
│                                                              │
│  AuthContext.useAuth() → { user, token, isAuthenticated }   │
│    - isAuthenticated checks: !!user && !!token              │
│    - login(userData, tokenData) → stores both               │
│    - logout() → clears both                                 │
└──────────────────────────────────────────────────────────────┘

  API Interceptors
  ───────────────────────────────────────────────────────────
  REQUEST:  Get token from localStorage, inject Bearer auth
  RESPONSE: On 401 → clear tokens + redirect to /login
            Logs error for debugging
```

### Error Handling Patterns

```
  All async operations follow this pattern:
  
  try {
    setLoading(true)
    const { data } = await API.get('/endpoint')
    setData(data)
  } catch (err) {
    console.error('Action error:', err)  // Silent failures now logged
    toast.error(err.response?.data?.detail || 'Action failed')
  } finally {
    setLoading(false)
  }
  
  Benefits:
  - All errors logged to console (DevTools visible)
  - User notification via toast
  - Loading state always cleaned up
  - Safe optional chaining (?.)
```

### Data Fetching & Chart Generation

```
  Dashboard Charts (Dynamic Data)
  ────────────────────────────────
  generateChartData(stats)  → Creates 6-month trend from totals
  generatePieData(stats)    → Derives status breakdown from verified count
  Data flows: API stats → generated synthetic data → charts
  
  Example:
  If stats = { total_properties: 100, verified_properties: 80, ... }
  Then chart shows gradual growth from 30 → 98 properties
  And pie shows: Verified 80%, Pending 15%, Review 5%
```

### Hash Display Standardization

```
  All blockchain hashes use fmt.shortHash():
  
  Input:  "abc123def456789...longstring"
  Output: "abc123de...6789"  (first 8 + last 6 chars)
  
  Applied to:
  - Blockchain page (block hash, previous hash)
  - PropertyDetail (blockchain passport, transactions)
  - Marketplace (property blockchain_hash)
  
  Tooltip shows full hash on hover
  Copy button sends full hash to clipboard
```

### Component Data Flow

```
  ┌──────────────────────────────────────────────────────┐
  │  Component mounted                                   │
  │         ↓                                            │
  │  useEffect → set loading = true                      │
  │         ↓                                            │
  │  API.get(...) with try/catch                         │
  │         ↓                                            │
  │  ├─ Success: setState + console.log ('data loaded')  │
  │  ├─ Error: console.error + toast.error              │
  │  └─ Finally: setLoading = false                      │
  │                                                      │
  │  Render:
  │  - if (loading) → spinner                           │
  │  - if (!data) → empty state                          │
  │  - else → display with optional chaining (?.data)   │
  └──────────────────────────────────────────────────────┘
```

---

## 10. Frontend Implementation Details

### Auth Flow & Token Management

```
Request Interceptor: Inject Bearer token from localStorage
Response Interceptor: On 401 error → clear tokens + redirect to /login + console log

AuthContext:
- isAuthenticated = !!user && !!token (checks both present)
- login(userData, tokenData) → stores both in localStorage + state
- logout() → clears both from localStorage + state

Session Persistence:
- On app load, AuthContext reads from localStorage
- Protected routes check useAuth().isAuthenticated
- API failure → auto-logout if 401 received
```

### Error Handling Patterns

```javascript
// Applied across Dashboard, Blockchain, Marketplace, Portfolio, PropertyDetail

const load = async () => {
  setLoading(true)
  try {
    const { data } = await API.get('/endpoint')
    setData(data)
  } catch (err) {
    console.error('Load error:', err)  // Now visible in DevTools
    toast.error(err.response?.data?.detail || 'Failed to load')
  } finally {
    setLoading(false)
  }
}

// Safe data access with optional chaining
const value = data?.properties?.[0]?.market_value || 0
```

### Dynamic Chart Data Generation

```
Dashboard Charts (Dashboard.jsx):

generateChartData(stats)
  ├─ Creates 6-month trend from stats.total_properties
  ├─ Scales: 30% → 150% of monthly average
  └─ Output: [{ month, properties, value }, ...]

generatePieData(stats)
  ├─ Verified: (verified_properties / total_properties) * 100
  ├─ Pending: 30% of verified percentage (realistic ratio)
  ├─ Review: remainder to 100%
  └─ Output: [{ name, value, color }, ...]

Before: Hardcoded chartData & pieData arrays
After: Computed from live API stats (fallback to defaults if missing)
```

### Hash Display & Copy

```
fmt.shortHash(hash)
  Input:  "a1b2c3d4e5f6g7h8i9j0..."
  Output: "a1b2c3d4...g7h8"
          (first 8 + last 6 characters with ellipsis)

Applied To:
  - Blockchain: block hash, previous hash
  - PropertyDetail: blockchain passport, transaction block_hash
  - Marketplace: property blockchain_hash
  
UI: [hash-text (copy button)] + title="full hash" for tooltip
```

---

## 11. Seed Data Summary

```
  Demo Accounts (password: Demo@1234)  |  Wallet: ₹10,00,000 each
  ─────────────────────────────────────────────────────────────────
  rajesh@propchain.in  →  Mumbai 2BHK + Bangalore Tech Park (owner)
  priya@propchain.in   →  Pune Warehouse + Nashik Farmland (owner)
  amit@propchain.in    →  Hyderabad Villa + Apollo Wing (owner)
  sunita@propchain.in  →  Delhi Connaught Place (owner)

  Properties
  ─────────────────────────────────────────────────────────────────
  PROP-xxxx  Residential   2BHK Sea-View, Bandra West        ₹1.85 Cr
  PROP-xxxx  Residential   4BHK Villa, Jubilee Hills          ₹6.50 Cr
  PROP-xxxx  Agricultural  Vineyard Farmland, Nashik          ₹0.85 Cr  → transferred to Priya
  PROP-xxxx  Industrial    Logistics Warehouse, Chakan        ₹4.20 Cr
  PROP-xxxx  Commercial    Prestige Tech Park, Bangalore     ₹28.00 Cr  → 2000 tokens @ ₹1.40L
  PROP-xxxx  Healthcare    Apollo Diagnostics, Chennai       ₹19.50 Cr  → 1000 tokens @ ₹1.95L
  PROP-xxxx  Commercial    Connaught Place Retail, Delhi     ₹32.00 Cr  → 3000 tokens @ ₹1.07L

  Fractional Investments
  ─────────────────────────────────────────────────────────────────
  Tech Park (2000 tokens):   Priya 5% · Amit 3% · Sunita 2%
  Apollo Wing (1000 tokens): Rajesh 8% · Priya 4% · Sunita 3%
  Connaught Place (3000):    Amit 6% · Rajesh 4% · Priya 2%
```
