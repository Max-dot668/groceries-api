from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from ..dependencies import get_current_active_user, SessionDep
from ..db.database import Item, ItemCreate, ItemUpdate, ItemPublic, User, select

router = APIRouter(
    prefix="/items",
    tags=["items"],
    dependencies=[Depends(get_current_active_user)],
    responses={404: {"description": "Item not found"}},
)

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_item(
    current_user: Annotated[User, Depends(get_current_active_user)],
    item: ItemCreate,
    session: SessionDep,
) -> ItemPublic:
    """Create an item for the current user"""
    # Type checker doesn't know that current_user.id is always set after DB retrieval
    if current_user.id is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User ID not found")
    
    # Create item and automatically assign to current user
    db_item = Item(
        name=item.name,
        quantity=item.quantity,
        priority=item.priority,
        owner_id=current_user.id  # Now type checker is happy!
    )
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return ItemPublic.model_validate(db_item)

@router.get("/", status_code=status.HTTP_200_OK)
def read_items(
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: SessionDep,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
) -> List[ItemPublic]:
    """Get all items for the current user only"""
    if current_user.id is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User ID not found")
    
    # Only return items that belong to the current user
    statement = select(Item).where(Item.owner_id == current_user.id).offset(offset).limit(limit)
    my_items = session.exec(statement).all()
    return [ItemPublic.model_validate(item) for item in my_items]

@router.get("/{item_id}/", status_code=status.HTTP_200_OK)
def read_item(
    current_user: Annotated[User, Depends(get_current_active_user)],
    item_id: int,
    session: SessionDep,
) -> ItemPublic:
    """Get a specific item (only if it belongs to current user)"""
    if current_user.id is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User ID not found")
    
    item = session.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    
    # Security check: make sure item belongs to current user
    if item.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this item")
    
    return ItemPublic.model_validate(item)

@router.put("/{item_id}/", status_code=status.HTTP_200_OK)
def update_item(
    current_user: Annotated[User, Depends(get_current_active_user)],
    item_id: int,
    item_update: ItemUpdate,
    session: SessionDep,
) -> ItemPublic:
    """Update an item (only if it belongs to current user)"""
    if current_user.id is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User ID not found")
    
    item = session.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    
    # Security check: make sure item belongs to current user
    if item.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to modify this item")
    
    # Update only the fields that were provided
    item_data = item_update.model_dump(exclude_unset=True)
    item.sqlmodel_update(item_data)
    session.add(item)
    session.commit()
    session.refresh(item)
    return ItemPublic.model_validate(item)

@router.delete("/{item_id}/", status_code=status.HTTP_200_OK)
def delete_item(
    current_user: Annotated[User, Depends(get_current_active_user)],
    item_id: int,
    session: SessionDep,
):
    """Delete an item (only if it belongs to current user)"""
    if current_user.id is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User ID not found")
    
    item = session.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    
    # Security check: make sure item belongs to current user
    if item.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this item")
    
    session.delete(item)
    session.commit()
    return {"message": "Item deleted successfully"}