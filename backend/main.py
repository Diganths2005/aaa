from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import ALLOWED_ORIGINS, PROJECT_NAME, PROJECT_VERSION, API_V1_STR
from database import Base, engine
from routes import auth, tax_profile, tax

# Create tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title=PROJECT_NAME,
    version=PROJECT_VERSION,
)

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
app.include_router(tax.router)

@app.get("/")
def read_root():
    return {
        "message": f"Welcome to {PROJECT_NAME}",
        "version": PROJECT_VERSION,
        "docs": "/docs"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
