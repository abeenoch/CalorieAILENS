from datetime import datetime
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import get_settings
from database import init_db
from services.opik_service import init_opik
from routers import auth, profile, analyze, feedback, balance, debug, metrics, experiments
from schemas import HealthCheck

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    # Startup
    print("Starting Calorie Tracker API...")
    
    # Initialize database
    await init_db()
    print("Database initialized")
    
    # Initialize Opik
    init_opik()
    
    # Print config info (without sensitive data)
    print(f"Opik Project: {settings.opik_project_name}")
    print(f"Gemini Model: {settings.gemini_model}")
    print("All systems ready!")
    
    yield
    
    # Shutdown
    print("Shutting down Calorie Tracker API...")


# Create FastAPI application
app = FastAPI(
    title="Calorie Tracker API",
    description="""
## Wellness-Focused Calorie Tracker

A multi-agent AI system for analyzing meals and providing supportive wellness guidance.

### Features
- **Meal Photo Analysis**: Snap a photo, get instant nutrition insights
- **Multi-Agent AI**: 4 specialized agents work together for accurate analysis
- **Opik Observability**: Full tracing of AI decision chains
- **Wellness-First**: Supportive, non-judgmental feedback

### Agents
1. **Vision Interpreter**: Identifies foods and portions
2. **Nutrition Reasoner**: Calculates calorie/macro ranges
3. **Personalization Agent**: Adjusts based on your profile
4. **Wellness Coach**: Provides empathetic feedback

### Important Note
> This app provides general wellness insights, not medical advice.
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(analyze.router)
app.include_router(feedback.router)
app.include_router(balance.router)
app.include_router(debug.router)
app.include_router(metrics.router)
app.include_router(experiments.router)


# Serve static frontend files
# Build frontend first: cd frontend && npm run build
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
    print(f"Frontend static files mounted from {frontend_dist}")
else:
    print(f"Frontend dist not found at {frontend_dist}")
    print("   Run: cd frontend && npm run build")


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Calorie Tracker API",
        "version": "1.0.0",
        "description": "Wellness-focused calorie tracker with multi-agent AI",
        "docs": "/docs",
        "disclaimer": "This app provides general wellness insights, not medical advice."
    }


@app.get("/health", response_model=HealthCheck, tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return HealthCheck(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow()
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
