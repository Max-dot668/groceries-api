# routers/users.py
from typing import Annotated
from fastapi import APIRouter, status, Depends, HTTPException
from ..dependencies import get_current_active_user, SessionDep
from ..db.database import User, UserPublic

router = APIRouter(prefix="/users", tags=["users"])

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