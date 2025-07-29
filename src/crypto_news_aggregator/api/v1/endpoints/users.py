"""User management API endpoints."""
from datetime import timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import EmailStr, HttpUrl

from ....core.config import get_settings
from ....core.security import (
    create_access_token,
    get_current_active_user,
    get_current_active_superuser,
)
from ....models.token import Token
from ....models.user import (
    User,
    UserCreate,
    UserInDB,
    UserResponse,
    UserUpdate,
    EmailVerificationRequest,
    UnsubscribeRequest,
    UserSubscriptionPreferences,
)
from ....services.user_service import UserService
from ....services.email_service import email_service
from ....core.templates import templates

router = APIRouter()

# Token expiration times
def get_access_token_expiry():
    settings = get_settings()
    return settings.ACCESS_TOKEN_EXPIRE_MINUTES


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_in: UserCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    user_service: UserService = Depends(UserService)
) -> Any:
    """
    Register a new user.
    
    This will create a new user and send a verification email.
    """
    try:
        # Create the user
        user = await user_service.create_user(user_in)
        
        # Generate verification URL
        verification_url = str(request.base_url) + f"api/v1/users/verify-email?token={user.email_verification_token}"
        
        # Send verification email in background
        background_tasks.add_task(
            email_service.send_verification_email,
            email=user.email,
            name=user.first_name or user.email.split('@')[0],
            verification_url=verification_url
        )
        
        # Return user data (without sensitive info)
        return UserResponse(**user.dict())
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/login", response_model=Token)
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_service: UserService = Depends(UserService)
) -> Dict[str, str]:
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    user = await user_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    access_token_expires = timedelta(minutes=get_access_token_expiry())
    access_token = create_access_token(
        data={"sub": user.email, "user_id": str(user.id)},
        expires_delta=access_token_expires
    )
    
    # Update last login
    await user_service.update_login_info(user.id, request.client.host)
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: UserInDB = Depends(get_current_active_user)
) -> Any:
    """
    Get current user information.
    """
    return UserResponse(**current_user.dict())

@router.put("/me", response_model=UserResponse)
async def update_user_me(
    user_update: UserUpdate,
    current_user: UserInDB = Depends(get_current_active_user),
    user_service: UserService = Depends(UserService)
) -> Any:
    """
    Update current user information.
    """
    updated_user = await user_service.update_user(current_user.id, user_update)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update user"
        )
    return UserResponse(**updated_user.dict())

@router.post("/password/request-reset")
async def request_password_reset(
    email: EmailStr,
    background_tasks: BackgroundTasks,
    request: Request,
    user_service: UserService = Depends(UserService)
) -> Dict[str, str]:
    """
    Request a password reset email.
    """
    result = await user_service.initiate_password_reset(email)
    if not result:
        # Don't reveal that the email doesn't exist
        return {"message": "If your email is registered, you will receive a password reset link"}
    
    # Generate reset URL
    reset_url = f"{request.base_url}reset-password?token={result['reset_token']}"
    
    # Send password reset email in background
    background_tasks.add_task(
        email_service.send_password_reset_email,
        email=result['email'],
        reset_url=reset_url,
        expires_in_hours=1
    )
    
    return {"message": "If your email is registered, you will receive a password reset link"}

@router.post("/password/reset")
async def reset_password(
    token: str,
    new_password: str,
    user_service: UserService = Depends(UserService)
) -> Dict[str, str]:
    """
    Reset password using a valid reset token.
    """
    success = await user_service.reset_password(token, new_password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token"
        )
    return {"message": "Password updated successfully"}

@router.post("/verify-email")
async def verify_email(
    verification: EmailVerificationRequest,
    user_service: UserService = Depends(UserService)
) -> Dict[str, str]:
    """
    Verify user's email using the verification token.
    """
    success = await user_service.verify_email(verification.token)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    return {"message": "Email verified successfully"}

@router.post("/resend-verification")
async def resend_verification(
    email: EmailStr,
    background_tasks: BackgroundTasks,
    request: Request,
    user_service: UserService = Depends(UserService)
) -> Dict[str, str]:
    """
    Resend email verification.
    """
    user = await user_service.get_by_email(email)
    if not user:
        # Don't reveal that the email doesn't exist
        return {"message": "If your email is registered, you will receive a verification link"}
    
    if user.email_verified:
        return {"message": "Email is already verified"}
    
    # Generate new verification token
    verification_token = await user_service.generate_verification_token(user.id)
    if not verification_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to generate verification token"
        )
    
    # Generate verification URL
    verification_url = str(request.base_url) + f"api/v1/users/verify-email?token={verification_token}"
    
    # Send verification email in background
    background_tasks.add_task(
        email_service.send_verification_email,
        email=user.email,
        name=user.first_name or user.email.split('@')[0],
        verification_url=verification_url
    )
    
    return {"message": "Verification email sent"}

@router.post("/unsubscribe")
async def unsubscribe(
    unsubscribe_req: UnsubscribeRequest,
    user_service: UserService = Depends(UserService)
) -> Dict[str, str]:
    """
    Unsubscribe from emails.
    
    If email_type is provided, unsubscribe from that specific type.
    Otherwise, unsubscribe from all emails.
    """
    success = await user_service.unsubscribe_user(
        unsubscribe_req.token,
        unsubscribe_req.email_type
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid unsubscribe token"
        )
    
    return {"message": "Unsubscribed successfully"}

@router.get("/subscription-preferences", response_model=UserSubscriptionPreferences)
async def get_subscription_preferences(
    current_user: UserInDB = Depends(get_current_active_user)
) -> Any:
    """
    Get current user's email subscription preferences.
    """
    return current_user.subscription_preferences

@router.put("/subscription-preferences", response_model=UserSubscriptionPreferences)
async def update_subscription_preferences(
    preferences: UserSubscriptionPreferences,
    current_user: UserInDB = Depends(get_current_active_user),
    user_service: UserService = Depends(UserService)
) -> Any:
    """
    Update current user's email subscription preferences.
    """
    updated_user = await user_service.update_subscription_preferences(
        current_user.id,
        preferences
    )
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update subscription preferences"
        )
    return updated_user.subscription_preferences

# Admin-only endpoints
@router.get("/", response_model=List[UserResponse], dependencies=[Depends(get_current_active_superuser)])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    user_service: UserService = Depends(UserService)
) -> Any:
    """
    Retrieve users (admin only).
    """
    users = await user_service.get_users(skip=skip, limit=limit)
    return [UserResponse(**user.dict()) for user in users]

@router.get("/{user_id}", response_model=UserResponse, dependencies=[Depends(get_current_active_superuser)])
async def get_user(
    user_id: str,
    user_service: UserService = Depends(UserService)
) -> Any:
    """
    Get a specific user by ID (admin only).
    """
    user = await user_service.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return UserResponse(**user.dict())

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_current_active_superuser)])
async def delete_user(
    user_id: str,
    user_service: UserService = Depends(UserService)
) -> None:
    """
    Delete a user (admin only).
    """
    success = await user_service.delete_user(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
