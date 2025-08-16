from sqlmodel import Field, Session, SQLModel, create_engine, select, Relationship
from pydantic import EmailStr
from typing import List, Optional

# User Models
class UserBase(SQLModel):
    username: str = Field(index=True, unique=True)
    email: EmailStr | None = None
    full_name: str | None = None
    disabled: bool = False

class User(UserBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    hashed_password: str
    
    # Relationship to items - this creates the connection!
    items: List["Item"] = Relationship(back_populates="owner")

class UserCreate(UserBase):
    password: str  # Plain password, will be hashed

class UserPublic(UserBase):
    id: int

# Item Models  
class ItemBase(SQLModel):
    name: str = Field(index=True)
    quantity: int = Field(ge=1, index=True)
    priority: int = Field(ge=1, le=5, index=True)

class Item(ItemBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    
    # Foreign key to connect items to users
    owner_id: int = Field(foreign_key="user.id")
    
    # Relationship back to user
    owner: User = Relationship(back_populates="items")

class ItemCreate(ItemBase):
    pass  # owner_id will be set automatically from current user

class ItemUpdate(SQLModel):
    name: str | None = None
    quantity: int | None = Field(default=None, ge=1)
    priority: int | None = Field(default=None, ge=1, le=5)

class ItemPublic(ItemBase):
    id: int
    owner_id: int

# Database setup
sqlite_file_name = "app_database.db"  # Single database file
sqlite_url = f"sqlite:///{sqlite_file_name}"
connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session