from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("✅ VideoAI backend starting up...")
    yield
    print("🛑 VideoAI backend shutting down...")


app = FastAPI(
    title="VideoAI Intelligence",
    version="1.0.0",
    description="AI/ML-Driven Video Analysis — REST API",
    docs_url="/docs",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/", tags=["Root"])
async def root():
    return {"message": "VideoAI Intelligence API", "docs": "/docs"}
