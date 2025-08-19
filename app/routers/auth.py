# routers/auth.py
from typing import Annotated
from fastapi import APIRouter, status, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from ..security import ACCESS_TOKEN_EXPIRE_MINUTES
from ..dependencies import authenticate_user, create_access_token, get_password_hash, SessionDep
from ..models import Token
from ..db.database import User, UserCreate, UserPublic, select

router = APIRouter(tags=["auth"])

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


@router.post("/token/", status_code=status.HTTP_201_CREATED)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: SessionDep
) -> Token:
    """Login endpoint that authenticates against the database"""
    user = authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")