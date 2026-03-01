from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from contextlib import asynccontextmanager

from config.database import init_db
from routes.blockchain import router as blockchain_router
from routes.ai_verify import router as ai_router


# ---------------------------------------------------------------------------
# OpenAPI tag metadata — shows up as sections in Swagger UI
# ---------------------------------------------------------------------------
tags_metadata = [
    {
        "name": "Health",
        "description": "Service health and status endpoints.",
    },
    {
        "name": "AI Document Verification",
        "description": (
            "Upload property documents (PDF/image) for AI-powered fraud detection. "
            "Uses **AWS Textract** to extract fields and **AWS Bedrock (Claude)** to analyze for fraud. "
            "Falls back to mock simulation if AWS credentials are not configured."
        ),
    },
    {
        "name": "Blockchain",
        "description": (
            "Core PropChain blockchain operations. "
            "Every write is an **append-only** SHA-256 hash-chained block stored in MongoDB. "
            "Tamper detection runs on every `GET /verify/{property_id}` call."
        ),
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    print("✅ MongoDB indexes initialized")
    yield


app = FastAPI(
    title="PropChain API",
    description="""
## PropChain — Blockchain & AI-Powered Property Registration

Built for the **AI for Bharat Hackathon** powered by AWS.

### What this API does
- **Property Passport** — Every property gets an immutable, hash-chained digital identity on the blockchain.
- **AI Fraud Detection** — Document verification results (fraud score, flags) are logged on-chain for a permanent audit trail.
- **Guided Registration Flow** — Step-by-step ownership lifecycle: register → verify → transfer → tokenize.
- **Fractional Ownership** — Tokenize premium assets (hospitals, warehouses) into investable shares.

### Blockchain Model
This is a **mock blockchain** backed by MongoDB:
- Each block stores: `block_index`, `property_id`, `data`, `previous_hash`, `timestamp`, `hash`
- Hash = `SHA-256(block_index + property_id + data + previous_hash + timestamp)`
- MongoDB enforces **append-only** via a unique index on `(property_id, block_index)`
- Any direct DB tampering is detected by `GET /blockchain/verify/{property_id}`

### Transaction Types
| Type | Trigger |
|---|---|
| `GENESIS` | First property registration |
| `OWNERSHIP_TRANSFER` | Buyer ↔ Seller transfer |
| `DOCUMENT_VERIFICATION` | AI fraud check logged |
| `STATUS_UPDATE` | Legal status change (disputed, encumbered) |
| `FRACTIONAL_MINT` | Property tokenized |
| `FRACTIONAL_TRANSFER` | Tokens sold to investor |
""",
    version="1.0.0",
    openapi_tags=tags_metadata,
    contact={
        "name": "OpsAI Team",
        "email": "team@propchain.ai",
    },
    license_info={
        "name": "MIT",
    },
    lifespan=lifespan,
    docs_url=None,   # We serve custom Swagger UI below
    redoc_url=None,  # We serve custom ReDoc below
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(blockchain_router)
app.include_router(ai_router)


# ---------------------------------------------------------------------------
# Custom Swagger UI — dark theme, persistent auth, deep linking
# ---------------------------------------------------------------------------
@app.get("/swagger", include_in_schema=False)
async def custom_swagger_ui():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="PropChain API — Swagger UI",
        swagger_ui_parameters={
            "defaultModelsExpandDepth": 2,
            "defaultModelExpandDepth": 3,
            "docExpansion": "list",         # list | full | none
            "filter": True,                  # search bar in Swagger UI
            "tryItOutEnabled": True,         # "Try it out" open by default
            "persistAuthorization": True,    # keep auth across page reloads
            "deepLinking": True,             # shareable URLs per endpoint
            "displayRequestDuration": True,  # show response time
        },
        swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
    )


# ---------------------------------------------------------------------------
# ReDoc UI — cleaner read-only docs
# ---------------------------------------------------------------------------
@app.get("/redoc", include_in_schema=False)
async def redoc_ui():
    return get_redoc_html(
        openapi_url="/openapi.json",
        title="PropChain API — ReDoc",
        redoc_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
    )


# ---------------------------------------------------------------------------
# Health routes
# ---------------------------------------------------------------------------
@app.get("/", tags=["Health"], summary="API root")
async def root():
    return {
        "service": "PropChain API",
        "version": "1.0.0",
        "status": "running",
        "swagger_ui": "/swagger",
        "redoc": "/redoc",
        "openapi_json": "/openapi.json",
    }


@app.get("/health", tags=["Health"], summary="Health check")
async def health():
    return {"status": "ok"}
