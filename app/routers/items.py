from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Query
from ..dependencies import get_current_active_user, SessionDep
from ..db.database import Item, ItemCreate, ItemUpdate, select
from ..models import User

router = APIRouter(
    prefix="/items",
    tags=["items"],
    dependencies=[Depends(get_current_active_user)],
    responses={404: {"Error": "Item not found"}},
)

# Create an item
@router.post("/")
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
@router.get("/")
def read_items(
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: SessionDep,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
    ):
    my_items = session.exec(select(Item).offset(offset).limit(limit)).all()
    return my_items

# Read an item
@router.get("/{item_id}/")
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
@router.put("/{item_id}/")
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
@router.delete("/{item_id}/")
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