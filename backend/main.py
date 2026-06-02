from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import db
from routers import dashboard, transactions

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage the lifespan of the FastAPI application.
    Initializes and cleans up the PostgreSQL connection pool.
    """
    db.init_pool()
    yield
    db.close_pool()

# Create FastAPI app
app = FastAPI(
    title="Mutual Fund Transaction Dashboard API",
    description="Backend API services for mutual fund analytics and metrics reporting.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router)
app.include_router(transactions.router)

@app.get("/")
def read_root():
    return {
        "message": "Welcome to the Mutual Fund Transaction Dashboard API",
        "docs": "/docs"
    }
