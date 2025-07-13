"""Authentication endpoints."""
from datetime import timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from src.crypto_news_aggregator.core import security
from src.crypto_news_aggregator.core.config import settings
from src.crypto_news_aggregator.core.security import Token, TokenData
from src.crypto_news_aggregator.db.session import get_session
from src.crypto_news_aggregator.models.user_sql import UserSQL, UserCreateSQL
from src.crypto_news_aggregator.db.operations import users as user_ops

router = APIRouter()

@router.post("/register", response_model=UserSQL, status_code=status.HTTP_201_CREATED)
async def register_user(
    *,
    db: AsyncSession = Depends(get_session),
    user_in: UserCreateSQL,
) -> Any:
    """
    Register a new user.
    
    This endpoint creates a new user with the provided information.
    The user will need to verify their email before they can log in.
    """
    # Check if user with email or username already exists
    existing_user = await user_ops.get_user_by_email(db, user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists",
        )
    
    existing_username = await user_ops.get_user_by_username(db, user_in.username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this username already exists",
        )
    
    # Create the user
    user = await user_ops.create_user(db, user_in)
    
    # TODO: Send verification email
    # await send_verification_email(user.email, user.email_verification_token)
    
    return user

@router.post("/login", response_model=Token)
async def login_for_access_token(
    response: Response,
    db: AsyncSession = Depends(get_session),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    
    This endpoint authenticates a user and returns an access token and refresh token.
    The access token should be included in the Authorization header for protected endpoints.
    """
    # Authenticate user
    user = await user_ops.get_user_by_credentials(
        db, 
        username_or_email=form_data.username,  # Can be either username or email
        password=form_data.password,
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    
    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not verified. Please check your email for the verification link.",
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        subject=str(user.id), expires_delta=access_token_expires
    )

    # Update last login time
    await user_ops.update_last_login(db, user.id, "127.0.0.1")

    return {
        "access_token": access_token,
        "user_id": str(user.id),
    }

@router.post("/refresh", response_model=Token)
async def refresh_access_token(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> Any:
    """
    Refresh an access token using a refresh token.
    
    This endpoint generates a new access token using a valid refresh token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Get refresh token from cookie
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise credentials_exception
    
    # Remove 'Bearer ' prefix if present
    if refresh_token.startswith("Bearer "):
        refresh_token = refresh_token[7:]
    
    try:
        # Verify refresh token
        payload = security.jwt.decode(
            refresh_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        # Check if this is a refresh token
        if not payload.get("refresh"):
            raise credentials_exception
        
        # Get user ID from token
        user_id = payload.get("sub")
        if not user_id:
            raise credentials_exception
        
        # Get user from database
        user = await user_ops.get_user(db, int(user_id))
        if not user or not user.is_active:
            raise credentials_exception
        
        # Create new access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = security.create_access_token(
            subject=str(user.id),
            expires_delta=access_token_expires,
            username=user.username,
            email=user.email,
            is_superuser=user.is_superuser,
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": int(access_token_expires.total_seconds()),
            "refresh_token": refresh_token,  # Return the same refresh token
        }
        
    except security.JWTError as e:
        raise credentials_exception from e

@router.post("/logout")
async def logout(response: Response) -> dict[str, str]:
    """
    Log out the current user.
    
    This endpoint removes the refresh token cookie.
    """
    # Remove the refresh token cookie
    response.delete_cookie("refresh_token")
    
    return {"message": "Successfully logged out"}
