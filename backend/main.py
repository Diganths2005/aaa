from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from config import ALLOWED_ORIGINS, PROJECT_NAME, PROJECT_VERSION, API_V1_STR, DATABASE_URL, OPENAI_API_KEY
from database import Base, engine
from routes import auth, chat, deductions, documents, itr, onboarding, tax_profile, tax, what_if
from tax_engine.models import TaxEngineError

# Create tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title=PROJECT_NAME,
    version=PROJECT_VERSION,
)

@app.exception_handler(TaxEngineError)
async def tax_engine_error_handler(request: Request, exc: TaxEngineError):
    return JSONResponse(status_code=422, content={"error": {"code": exc.code, "message": exc.message}})

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix=API_V1_STR)
app.include_router(tax_profile.router, prefix=API_V1_STR)
app.include_router(deductions.router, prefix=API_V1_STR)
app.include_router(documents.router, prefix=API_V1_STR)
app.include_router(onboarding.router, prefix=API_V1_STR)
app.include_router(chat.router, prefix=API_V1_STR)
app.include_router(itr.router)
app.include_router(tax.router)
app.include_router(what_if.router, prefix=API_V1_STR)


@app.get("/")
def read_root():
    return {
        "message": f"Welcome to {PROJECT_NAME}",
        "version": PROJECT_VERSION,
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    checks = {"database": "ok", "document_storage": "ok", "semantic_rag": "configured" if OPENAI_API_KEY else "unavailable"}
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        checks["database"] = "unavailable"
    try:
        documents_root = documents.DOCUMENT_STORAGE.root
        documents_root.mkdir(parents=True, exist_ok=True)
        test_path = documents_root / ".healthcheck"
        test_path.write_text("ok", encoding="utf-8")
        test_path.unlink(missing_ok=True)
    except Exception:
        checks["document_storage"] = "unavailable"
    overall = "healthy" if all(value in {"ok", "configured"} for value in checks.values()) else "degraded"
    return {"status": overall, "checks": checks}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
