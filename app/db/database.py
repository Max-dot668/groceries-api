from sqlmodel import Field, Session, SQLModel, create_engine, select
from typing import Annotated

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

# TODO: replace with actual user DB
fake_users_db = {
    "johndoe": {
        "username": "johndoe",
        "full_name": "John Doe",
        "email": "johndoe@example.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        "disabled": False, 
    },
}