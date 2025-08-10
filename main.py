from typing import Annotated, Any
from fastapi import FastAPI,Path, Query
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

class UserIn(BaseModel):
    username: str
    password: str
    email: EmailStr
    full_name: str | None = None
    
class UserOut(BaseModel):
    username: str
    email: EmailStr
    fullname: str

app = FastAPI()

class FilterParams(BaseModel):
    name: str | None = None
    priority: int | None = None

items = {} 

@app.get("/")
async def root() -> dict:
    return {"message": "groceries list manager"}

@app.get("/user", response_model=UserOut)
async def get_user(user: UserIn) -> Any:
    return user

@app.get("/user/items")
async def read_items() -> dict:
    return items

@app.get("/user/items/item")
async def read_item(filter: Annotated[FilterParams, Query()]) -> list:
    result = []
    for id in items:
        if filter.name == items[id]["name"] or filter.priority == items[id]["priority"]:
            result.append({"name": items[id]["name"], "quantity": items[id]["quantity"]})
    return result
        
@app.post("/user/items/{item_id}")
async def create_item(item_id: Annotated[int, Path()], item: Item,) -> dict:
    item_data = item.model_dump()
    item_data.update({"date": datetime.now()})
    items[item_id] = item_data
    return {"item added": item_data}

@app.put("/user/items/{item_id}")
async def update_item(item_id: Annotated[int, Path()], item: Item) -> dict:
    if item_id not in items:
        raise ValueError("item id was not found")
    else:
        items[item_id] = item.model_dump()
    return {"message": "item was updated"}
