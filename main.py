from enum import Enum
from typing import Annotated
from fastapi import FastAPI,Path, Query, status, Form, File, UploadFile, HTTPException
from pydantic import BaseModel, Field, HttpUrl, EmailStr
from datetime import datetime

class Image(BaseModel):
    url: HttpUrl

class Item(BaseModel):
    name: str = Field(min_length=1)
    priority: int = Field(ge=1, le=5)
    quantity: int = Field(ge=1)
    tags: set[str] = set()
    image: Image | None = None

class BaseUser(BaseModel):
    username: str
    email: EmailStr
    full_name: str | None = None
    
class UserIn(BaseUser):
    password: str
    
class UserInDB(BaseUser):
    hashed_password: str
    
app = FastAPI()

class FormData(BaseModel):
    username: str
    password: str

class FilterParams(BaseModel):
    name: str | None = None
    priority: int | None = None

class Tags(Enum):
    items = "items"
    users = "users"

items = {} 

def fake_password_hasher(raw_password: str) -> str:
    return "supersecret" + raw_password

def fake_save_user(user_in: UserIn) -> UserInDB:
    hashed_password = fake_password_hasher(user_in.password)
    user_in_db = UserInDB(**user_in.model_dump(), hashed_password=hashed_password)
    print("User saved!  ..not really")
    return user_in_db

@app.get("/")
async def root() -> dict:
    return {"message": "groceries list manager"}

@app.post("/login/", tags=[Tags.users], status_code=status.HTTP_201_CREATED)
async def login(form_data: Annotated[FormData, Form()]):
    return form_data.username

@app.post("/user/", response_model_exclude_unset=True, tags=[Tags.users], status_code=status.HTTP_201_CREATED)
async def create_user(user: UserIn) -> BaseUser:
    return user 

@app.get("/user/items", tags=[Tags.users])
async def read_items() -> dict:
    return items

@app.get("/user/items/item", tags=[Tags.users])
async def read_item(filter: Annotated[FilterParams, Query()]) -> list:
    result = []
    for id in items:
        if filter.name == items[id]["name"] or filter.priority == items[id]["priority"]:
            result.append({"name": items[id]["name"], "quantity": items[id]["quantity"]})
    return result
        
@app.post("/user/items/{item_id}", response_model_exclude_unset=True, tags=[Tags.items], status_code=status.HTTP_201_CREATED)
async def create_item(item_id: Annotated[int, Path()], item: Item,) -> dict:
    item_data = item.model_dump()
    item_data.update({"date": datetime.now()})
    items[item_id] = item_data
    return {"item added": item_data}

@app.put("/user/items/{item_id}", response_model_exclude_unset=True, tags=[Tags.items])
async def update_item(item_id: Annotated[int, Path()], item: Item) -> dict:
    if item_id not in items:
        raise HTTPException(status_code=404, detail="Item not found")
    else:
        items[item_id] = item.model_dump()
    return {"message": "item was updated"}

@app.post("/files/", tags=[Tags.items], status_code=status.HTTP_201_CREATED)
async def create_upload_file(
    file: Annotated[bytes, File()],
    fileb: Annotated[UploadFile, File()],
    token: Annotated[str, Form()],
    ):
    return {
        "file_size": len(file),
        "token": token,
        "fileb_content_type": fileb.content_type,
    }
