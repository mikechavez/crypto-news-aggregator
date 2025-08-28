"""Database operations for user management."""
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_

from ...models.user_sql import (
    UserCreateSQL, 
    UserUpdateSQL, 
    UserSQL
)
from ..models import User as UserDB
from ...core.security import get_password_hash, verify_password


async def get_user(db: AsyncSession, user_id: int) -> Optional[UserSQL]:
    """Get a user by ID."""
    result = await db.execute(select(UserDB).filter(UserDB.id == user_id))
    user = result.scalars().first()
    return UserSQL.model_validate(user) if user else None


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[UserSQL]:
    """Get a user by email (case-insensitive)."""
    result = await db.execute(
        select(UserDB).filter(UserDB.email.ilike(email))
    )
    user = result.scalars().first()
    return UserSQL.model_validate(user) if user else None


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[UserSQL]:
    """Get a user by username (case-insensitive)."""
    result = await db.execute(
        select(UserDB).filter(UserDB.username.ilike(username))
    )
    user = result.scalars().first()
    return UserSQL.model_validate(user) if user else None


async def get_user_by_credentials(
    db: AsyncSession, 
    username_or_email: str, 
    password: str
) -> Optional[UserSQL]:
    """Get user by username/email and verify password."""
    # Try to find user by username or email
    result = await db.execute(
        select(UserDB).filter(
            or_(
                UserDB.username.ilike(username_or_email),
                UserDB.email.ilike(username_or_email)
            )
        )
    )
    user = result.scalars().first()
    
    if not user or not verify_password(password, user.hashed_password):
        return None
        
    return UserSQL.model_validate(user)


async def create_user(db: AsyncSession, user_in: UserCreateSQL) -> UserSQL:
    """Create a new user."""
    # Hash the password
    hashed_password = get_password_hash(user_in.password)
    
    # Create the user
    db_user = UserDB(
        username=user_in.username,
        email=user_in.email,
        hashed_password=hashed_password,
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        is_active=True,
        email_verified=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    return UserSQL.model_validate(db_user)


async def update_user(
    db: AsyncSession, 
    db_user: UserDB, 
    user_in: UserUpdateSQL
) -> UserSQL:
    """Update a user."""
    update_data = user_in.model_dump(exclude_unset=True)
    
    # Check if updating to a new username that's already taken
    if 'username' in update_data:
        existing_user = await get_user_by_username(db, update_data['username'])
        if existing_user and existing_user.id != db_user.id:
            raise ValueError("Username already taken")
    
    # Update user fields
    for field, value in update_data.items():
        if field == 'password' and value:
            setattr(db_user, 'hashed_password', get_password_hash(value))
        elif value is not None:
            setattr(db_user, field, value)
    
    db_user.updated_at = datetime.now(timezone.utc)
    
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    return UserSQL.model_validate(db_user)


async def update_last_login(db: AsyncSession, user_id: int, ip_address: str) -> None:
    """Update the user's last login timestamp and IP address."""
    result = await db.execute(select(UserDB).filter(UserDB.id == user_id))
    user = result.scalars().first()
    if user:
        user.last_login_at = datetime.now(timezone.utc)
        user.last_login_ip = ip_address
        user.login_count = (user.login_count or 0) + 1
        db.add(user)
        await db.commit()


async def delete_user(db: AsyncSession, user_id: int) -> bool:
    """Delete a user."""
    result = await db.execute(select(UserDB).filter(UserDB.id == user_id))
    user = result.scalars().first()
    if not user:
        return False
    
    await db.delete(user)
    await db.commit()
    return True


async def get_users(
    db: AsyncSession, 
    skip: int = 0, 
    limit: int = 100
) -> List[UserSQL]:
    """Get a list of users with pagination."""
    result = await db.execute(
        select(UserDB)
        .offset(skip)
        .limit(limit)
        .order_by(UserDB.created_at.desc())
    )
    users = result.scalars().all()
    return [UserSQL.model_validate(user) for user in users]
