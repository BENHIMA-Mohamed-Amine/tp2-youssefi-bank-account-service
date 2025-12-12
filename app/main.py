# app/main.py

import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import (
    init_db,
)  # Assuming this is the correct import path
from app.routers import compte_router


# Define an async context manager for application lifespan events (startup/shutdown)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 🚀 Startup Event: Initialize the database
    print("Application starting up...")
    await init_db()
    yield
    # 🛑 Shutdown Event
    print("Application shutting down...")


# Initialize the FastAPI application
app = FastAPI(
    title="Bank Account Microservice",
    description="A Python microservice for managing bank accounts using FastAPI, SQLModel, and async SQLite.",
    version="0.1.0",
    lifespan=lifespan,
)

# 🔗 Include the routers
app.include_router(compte_router.router, tags=["Comptes"], prefix="/api/v1/comptes")


# Basic root endpoint
@app.get("/", tags=["Root"])
async def read_root():
    return {
        "message": "Bank Account Microservice is running! Navigate to /docs for API details."
    }


# --- New Function for Uvicorn Execution ---
def main():
    """Runs the FastAPI application using Uvicorn."""
    # Note: Assumes the file is run from the project root (e.g., 'python -m app.main')
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        factory=False,  # Use False when passing the app object directly
    )


# Standard entry point to run via `python -m app.main`
if __name__ == "__main__":
    main()
