from typing import Annotated
from fastapi import APIRouter, status, Depends
from ..dependencies import get_current_active_user
from ..models import User

router = APIRouter()

@router.get("/users/me", tags=["users"], status_code=status.HTTP_200_OK)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    return current_user

@router.get("/users/{username}", tags=["users"], status_code=status.HTTP_200_OK)
async def read_user(username: str):
    return {"username": username}