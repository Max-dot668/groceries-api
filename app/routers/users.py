# routers/users.py
from typing import Annotated
from fastapi import APIRouter, status, Depends, HTTPException
from ..dependencies import get_current_active_user, SessionDep, get_password_hash
from ..db.database import User, UserCreate, UserPublic, select
from ..models import User as UserModel

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserCreate, session: SessionDep) -> UserPublic:
    """Register a new user"""
    # Check if user already exists
    existing_user = session.exec(
        select(User).where(User.username == user_data.username)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Create new user with hashed password
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        disabled=False
    )
    
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    
    return UserPublic.model_validate(db_user)

@router.get("/me", status_code=status.HTTP_200_OK)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> UserPublic:
    """Get current user info"""
    return UserPublic.model_validate(current_user)

@router.get("/{user_id}", status_code=status.HTTP_200_OK)
async def read_user(
    user_id: int,
    session: SessionDep,
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> UserPublic:
    """Get user by ID (protected endpoint)"""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return UserPublic.model_validate(user)