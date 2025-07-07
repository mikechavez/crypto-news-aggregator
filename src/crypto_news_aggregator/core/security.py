"""Security and authentication utilities."""
from datetime import datetime, timezone, timedelta
from typing import Optional, Union, Any, Dict

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, HTTPBearer, HTTPAuthorizationCredentials
from fastapi.security.utils import get_authorization_scheme_param
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, ValidationError

from ..core.config import settings
from ..models.user import User as UserModel

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False
)

class TokenData(BaseModel):
    """Token data model."""
    sub: str  # user ID
    username: str
    email: str
    is_superuser: bool = False

class Token(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: Optional[str] = None

class TokenPayload(BaseModel):
    """JWT token payload."""
    sub: str  # user ID
    exp: int
    username: str
    email: str
    is_superuser: bool = False

class JWTBearer(HTTPBearer):
    """JWT Bearer token authentication."""
    
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
    
    async def __call__(self, request: Request) -> str:
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authenticated"
            )
        if credentials.scheme != "Bearer":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid authentication scheme"
            )
        return credentials.credentials

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate a password hash."""
    return pwd_context.hash(password)

def create_access_token(
    subject: Union[str, Any], 
    expires_delta: Optional[timedelta] = None,
    **extra_data
) -> str:
    """
    Create a JWT access token.
    
    Args:
        subject: The subject of the token (usually user ID)
        expires_delta: Optional timedelta for token expiration
        **extra_data: Additional data to include in the token
        
    Returns:
        str: Encoded JWT token
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        **extra_data
    }
    
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

def create_refresh_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None,
    **extra_data
) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        subject: The subject of the token (usually user ID)
        expires_delta: Optional timedelta for token expiration
        **extra_data: Additional data to include in the token
        
    Returns:
        str: Encoded JWT refresh token
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "refresh": True,
        **extra_data
    }
    
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

async def get_current_user(
    token: str = Depends(oauth2_scheme)
) -> UserModel:
    """
    Get the current user from the JWT token.
    
    Args:
        token: JWT token from the Authorization header
        
    Returns:
        UserModel: The authenticated user
        
    Raises:
        HTTPException: If the token is invalid or the user doesn't exist
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        # Check if this is a refresh token being used as access token
        if payload.get("refresh"):
            raise credentials_exception
            
        token_data = TokenPayload(**payload)
        
    except (JWTError, ValidationError) as e:
        raise credentials_exception from e
    
    # In a real app, you would fetch the user from the database here
    # For now, we'll return a mock user based on the token data
    return UserModel(
        id=token_data.sub,
        username=token_data.username,
        email=token_data.email,
        is_superuser=token_data.is_superuser,
        is_active=True,
        email_verified=True
    )

async def get_current_active_user(
    current_user: UserModel = Depends(get_current_user),
) -> UserModel:
    """
    Get the current active user.
    
    Args:
        current_user: The current authenticated user
        
    Returns:
        UserModel: The active user
        
    Raises:
        HTTPException: If the user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_active_superuser(
    current_user: UserModel = Depends(get_current_user),
) -> UserModel:
    """
    Get the current active superuser.
    
    Args:
        current_user: The current authenticated user
        
    Returns:
        UserModel: The active superuser
        
    Raises:
        HTTPException: If the user is not a superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user
