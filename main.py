from typing import Annotated
from fastapi import FastAPI,Path, Query
from pydantic import BaseModel, Field, HttpUrl

class Image(BaseModel):
    url: HttpUrl

class Item(BaseModel):
    name: str = Field(min_length=1)
    priority: int = Field(ge=1, le=5)
    quantity: int = Field(ge=1)
    tags: set[str] = set()
    image: Image | None = None

app = FastAPI()

# Query Parameter Model for fuzzy filter search
class FilterParams(BaseModel):
    name: str | None = None
    priority: int | None = None

# Fake items DB
items = {} 

@app.get("/")
async def root():
    return {"message": "groceries list manager"}

@app.get("/items")
async def read_items():
    return items

@app.get("/items/item")
async def read_item(filter: Annotated[FilterParams, Query()]):
    result = []
    for id in items:
        if filter.name == items[id]["name"] or filter.priority == items[id]["priority"]:
            result.append({"name": items[id]["name"], "quantity": items[id]["quantity"]})
    return result
        
@app.post("/items/{item_id}")
async def create_item(item_id: Annotated[int, Path()], item: Item):
    item_data = item.model_dump()
    items[item_id] = item_data
    return {"item added": item_data}

@app.put("/items/{item_id}")
async def update_item(item_id: Annotated[int, Path()], item: Item):
    if item_id not in items:
        raise ValueError("item id was not found")
    else:
        items[item_id] = item.model_dump()
    return {"message": "item was updated"}
