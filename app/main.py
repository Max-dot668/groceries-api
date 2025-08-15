import time
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from .dependencies import get_current_active_user, get_current_user, get_password_hash, get_user
from .routers import items, users, auth
from contextlib import asynccontextmanager
from .db.database import create_db_and_tables

# Modern lifespan apprach to DB
@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(
    lifespan=lifespan,
    )

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(items.router)

# CORS handling for compatibility with frontend, e.g. javascript in browser
origins = [
    "http://localhost",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware to benchmark process time for each CRUD operation
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Application logic 
@app.get("/")
async def root() -> dict:
    return {"message": "groceries list manager"}