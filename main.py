import jwt
import time
from typing import Annotated
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, status, HTTPException, Depends, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Field, Session, SQLModel, create_engine, select
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jwt.exceptions import InvalidTokenError
from datetime import datetime, timezone, timedelta

# to get a string like this run:
# openssl rand -hex 32
SECRET_KEY = "4888181d1e0fdd9fa67ce8bec4cf58d3f3fdf75e8b12d03eb51e1f0bf995bb16"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
    
fake_users_db = {
    "johndoe": {
        "username": "johndoe",
        "full_name": "John Doe",
        "email": "johndoe@example.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # bcrypt hash for "secret"
        "disabled": False, 
    },
}

# Database SQL 

# Models for DB
class ItemBase(SQLModel):
    name: str = Field(index=True)
    quantity: int = Field(ge=1, index=True)
    priority: int = Field(ge=1, le=5, index=True)
    
class Item(ItemBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    
class ItemCreate(ItemBase):
    name: str
    quantity: int = Field(ge=1)
    priority: int = Field(ge=1, le=5)
    
class ItemUpdate(ItemBase):
    name: str
    quantity: int = Field(ge=1)
    priority: int = Field(ge=1, le=5)

# Create DB Engine    
sqlite_file_name = "items_database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

# Create Session Dependency
def get_session():
    with Session(engine) as session:
        yield session
        
SessionDep = Annotated[Session, Depends(get_session)]


# Modern lifespan apprach to DB
@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

# Instance of the class FastAPI framework
app = FastAPI(lifespan=lifespan)

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


# Auth2 Security models and user authentication helper functions
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None
    
class User(BaseModel):
    username: str
    email: EmailStr | None = None
    full_name: str | None = None
    disabled: bool | None = None

class UserInDB(User):
    hashed_password: str

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)

def authenticate_user(fake_db, username: str, password: str):
    user = get_user(fake_db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except InvalidTokenError:
        raise credentials_exception
    user = get_user(fake_users_db, username=token_data.username) # type: ignore
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],    
):
    if current_user.disabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user


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

        
@app.post("/token", status_code=status.HTTP_201_CREATED)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")

@app.get("/users/me", status_code=status.HTTP_200_OK)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    return current_user

@app.post("/items/", status_code=status.HTTP_201_CREATED)
def create_items(
    current_user: Annotated[User, Depends(get_current_active_user)],
    item: ItemCreate,
    session: SessionDep,
    ) -> Item:
    db_item = Item.model_validate(item)
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item

# Read all items
@app.get("/items/", status_code=status.HTTP_200_OK)
def read_items(
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: SessionDep,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
    ):
    my_items = session.exec(select(Item).offset(offset).limit(limit)).all()
    return my_items

# Read an item
@app.get("/items/{item_id}", status_code=status.HTTP_200_OK)
def read_item(
    current_user: Annotated[User, Depends(get_current_active_user)],
    item_id: int,
    session: SessionDep,
    ) -> Item:
    item = session.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item

# Update an update
@app.put("/items/{item_id}", status_code=status.HTTP_200_OK)
def update_item(
    current_user: Annotated[User, Depends(get_current_active_user)],
    item_id: int,
    item: ItemUpdate,
    session: SessionDep,
):
    item_db = session.get(Item, item_id)
    if not item_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    item_data = item.model_dump(exclude_unset=True)
    item_db.sqlmodel_update(item_data)
    session.add(item_db)
    session.commit()
    session.refresh(item_db)
    return item_db

# Delete an item
@app.delete("/items/{item_id}", status_code=status.HTTP_200_OK)
def delete_item(
    current_user: Annotated[User, Depends(get_current_active_user)],
    item_id: int,
    session: SessionDep,
    ):
    item = session.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    session.delete(item)
    session.commit()
    return {"ok": True}
