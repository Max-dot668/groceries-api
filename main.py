import jwt
from enum import Enum
from typing import Annotated
from fastapi import FastAPI,Path, Query, status, Form, File, UploadFile, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field, HttpUrl, EmailStr
from passlib.context import CryptContext
from jwt.exceptions import InvalidTokenError
from datetime import datetime, timezone, timedelta

# to get a string like this run:
# openssl rand -hex 32
SECRET_KEY = "4888181d1e0fdd9fa67ce8bec4cf58d3f3fdf75e8b12d03eb51e1f0bf995bb16"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
    
fake_users_db = {
    "johndoe": {
        "username": "johndoe",
        "full_name": "John Doe",
        "email": "johndoe@example.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # bcrypt hash for "secret"
        "disabled": False, 
    },
}

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None

items = {} 

class Image(BaseModel):
    url: HttpUrl

class Item(BaseModel):
    name: str = Field(min_length=1)
    priority: int = Field(ge=1, le=5)
    quantity: int = Field(ge=1)
    tags: set[str] = set()
    image: Image | None = None

class User(BaseModel):
    username: str
    email: EmailStr | None = None
    full_name: str | None = None
    disabled: bool | None = None

class UserInDB(User):
    hashed_password: str

class FormData(BaseModel):
    username: str
    password: str

class FilterParams(BaseModel):
    name: str | None = None
    priority: int | None = None

class Tags(Enum):
    items = "items"
    users = "users"
    files = "files"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()

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

@app.get("/")
async def root() -> dict:
    return {"message": "groceries list manager"}

@app.post("/token", tags=[Tags.users])
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

@app.get("/users/me", tags=[Tags.users])
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    return current_user

@app.get("/users/me/items/", tags=[Tags.items])
async def read_item(current_user: Annotated[User, Depends(get_current_active_user)], filter: Annotated[FilterParams, Query()]):
    """
    Gets a list of items that matches the filters arguments, else it returns all the items in the database:
    
    - **name**: If the user does not provide the name of the item, this will get omitted
    - **priority**: If the user does not provide the priority from an item in list, this will get omitted
    """
    result = []
    if filter.name is None and filter.priority is None:
        return items
    for id in items:
        if filter.name == items[id]["name"] or filter.priority == items[id]["priority"]:
            result.append({"name": items[id]["name"], "quantity": items[id]["quantity"]})
    return result
        
@app.post("/users/me/items/{item_id}/", response_model_exclude_unset=True, tags=[Tags.items], status_code=status.HTTP_201_CREATED)
async def create_item(current_user: Annotated[User, Depends(get_current_active_user)], item_id: Annotated[int, Path()], item: Item,) -> dict:
    """
    Create an item with all the information:
    
    - **item_id**: The item must have an id 
    - **name**: Each item must have a name
    - **priority**: Each item must have a priority from 1-5 inclusive
    - **tags**: A set of unique tag strings for this item
    - **image**: If the image is not provided, you can omit this 
    """
    item_data = item.model_dump()
    item_data.update({"date": jsonable_encoder(datetime.now())})
    items[item_id] = item_data
    return {"item added": item_data}

@app.put("/users/me/items/{item_id}/", response_model_exclude_unset=True, tags=[Tags.items])
async def update_item(current_user: Annotated[User, Depends(get_current_active_user)], item_id: Annotated[int, Path()], item: Item) -> dict:
    """
    Update an existing item in the groceries list with all the information:
    
    - **item_id**: The id must match the id of the item to be updated
    - **name**: The item must have a name
    - **priority**: Each item must have a priority from 1-5 inclusive
    - **tags**: A set of unique tag strings for this item
    - **image**: If the image is not provided, you can omit this 
    """
    if item_id not in items:
        raise HTTPException(status_code=404, detail="Item not found")
    else:
        items[item_id] = item.model_dump()
    return {"message": "item was updated"}

@app.delete("/users/me/items/{item_id}", tags=[Tags.items])
async def delete_item(current_user: Annotated[User, Depends(get_current_active_user)], item_id: Annotated[int, Path()]):
    """
    Delete an existing item in the groceries list with the information:
    
    - **item_id**: The id must match the id of the item to be deleted
    """
    my_item = items.get(item_id)
    if my_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    del items[item_id]
    return my_item

@app.post("/users/me/files/", tags=[Tags.files], status_code=status.HTTP_201_CREATED)
async def create_upload_file(
    current_user: Annotated[User, Depends(get_current_active_user)],
    file: Annotated[bytes, File()],
    fileb: Annotated[UploadFile, File()],
    token: Annotated[str, Form()],
    ):
    """
    Upload a file with all the information:
    - **file**: Relatively small sized file  
    - **fileb**: A better file input handling for bigger files
    - **Token**: An input token that accepts a string
    """
    return {
        "file_size": len(file),
        "token": token,
        "fileb_content_type": fileb.content_type,
    }
