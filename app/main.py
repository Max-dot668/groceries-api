# main.py
import time
from fastapi import Request, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import items, users, auth
from contextlib import asynccontextmanager
from .db.database import create_db_and_tables

# Modern lifespan approach to DB
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database tables on startup
    create_db_and_tables()
    yield


description = """
A REST API for managing grocery lists. 🚀

## Auth
User login with jwt authentication system.
* **Login with account**.

## Users

You will be able to:

* **Create a user account**.
* **Create users**.
* **Read users**.

## Items

You can **read items**.
You can **create items**.
You can **update items**.
You can **delete items**.

"""

app = FastAPI(
    title="Groceries API",
    description=description,
    version="1.0.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(items.router)

# CORS handling for compatibility with frontend
origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:3000",  # Common React port
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware to benchmark process time for each operation
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

@app.get("/")
async def root() -> dict:
    return {
        "message": "Groceries List Manager API",
        "docs": "/docs",
        "version": "1.0.0"
    }