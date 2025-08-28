"""Service for user management operations."""
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from uuid import uuid4

from bson import ObjectId
from passlib.context import CryptContext

from ..core.config import get_settings
from ..core.security import create_access_token, get_password_hash, verify_password
from ..db.mongodb import get_mongodb
from ..models.user import (
    UserInDB,
    UserCreate,
    UserUpdate,
    UserResponse,
    EmailVerificationStatus,
    UserSubscriptionPreferences,
    UserTrackingSettings,
)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserService:
    """Service for user management operations."""
    
    def __init__(self):
        self.collection_name = "users"
        self._db = None  # Will be set asynchronously
    
    async def _get_collection(self):
        """Get the users collection (async Motor)."""
        import logging
        if self._db is None:
            self._db = await get_mongodb()
            logging.warning(f"[UserService._get_collection] Acquired async DB: type={type(self._db)}, value={self._db}")
        collection = self._db[self.collection_name]
        collection = self.db[self.collection_name]
        logging.warning(f"[UserService._get_collection] collection type: {type(collection)}, value: {collection}")
        return collection
    
    async def get_by_id(self, user_id: str) -> Optional[UserInDB]:
        """Get a user by ID."""
        collection = await self._get_collection()
        user = await collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            return None
        return UserInDB(**user)
    
    async def get_by_email(self, email: str) -> Optional[UserInDB]:
        """Get a user by email (case-insensitive)."""
        collection = await self._get_collection()
        user = await collection.find_one({"email": {"$regex": f'^{email}$', "$options": 'i'}})
        if not user:
            return None
        return UserInDB(**user)
    
    async def create_user(self, user_data: UserCreate) -> UserInDB:
        """Create a new user with hashed password."""
        # Check if user already exists
        existing_user = await self.get_by_email(user_data.email)
        if existing_user:
            raise ValueError("User with this email already exists")
        
        # Generate verification token
        verification_token = secrets.token_urlsafe(32)
        unsubscribe_token = secrets.token_urlsafe(32)
        
        # Create user document
        user_dict = user_data.model_dump(exclude={"password"})
        user_dict.update({
            "hashed_password": get_password_hash(user_data.password),
            "email_verification_token": verification_token,
            "email_verification_sent_at": datetime.utcnow(),
            "unsubscribe_token": unsubscribe_token,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        })
        
        # Insert into database
        collection = await self._get_collection()
        result = await collection.insert_one(user_dict)
        user_dict["_id"] = result.inserted_id
        
        return UserInDB(**user_dict)
    
    async def update_user(
        self, 
        user_id: str, 
        update_data: UserUpdate,
        updated_by_admin: bool = False
    ) -> Optional[UserInDB]:
        """Update user information."""
        collection = await self._get_collection()
        update_dict = update_data.model_dump(exclude_unset=True)
        
        # Don't allow certain fields to be updated this way
        for field in ["email", "hashed_password", "is_superuser"]:
            update_dict.pop(field, None)
        
        # Only admins can update certain fields
        if not updated_by_admin:
            for field in ["is_active", "email_verified", "email_verification_status"]:
                update_dict.pop(field, None)
        
        if not update_dict:
            return await self.get_by_id(user_id)
        
        update_dict["updated_at"] = datetime.utcnow()
        
        result = await collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_dict}
        )
        
        if result.modified_count == 1:
            return await self.get_by_id(user_id)
        return None
    
    async def update_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str
    ) -> bool:
        """Update user's password after verifying current password."""
        user = await self.get_by_id(user_id)
        if not user:
            return False
            
        if not verify_password(current_password, user.hashed_password):
            return False
            
        collection = await self._get_collection()
        result = await collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "hashed_password": get_password_hash(new_password),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return result.modified_count == 1
    
    async def verify_email(self, token: str) -> bool:
        """Verify user's email using the verification token."""
        collection = await self._get_collection()
        
        user = await collection.find_one({
            "email_verification_token": token,
            "email_verified": False
        })
        
        if not user:
            return False
        
        # Check if token is expired (24 hours)
        token_age = datetime.utcnow() - user.get("email_verification_sent_at", datetime.utcnow())
        if token_age > timedelta(hours=24):
            return False
        
        result = await collection.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "email_verified": True,
                    "email_verification_status": "verified",
                    "is_active": True,
                    "updated_at": datetime.utcnow()
                },
                "$unset": {
                    "email_verification_token": "",
                    "email_verification_sent_at": ""
                }
            }
        )
        
        return result.modified_count == 1
    
    async def initiate_password_reset(self, email: str) -> Optional[Dict[str, str]]:
        """Initiate password reset process."""
        user = await self.get_by_email(email)
        if not user:
            return None
            
        reset_token = secrets.token_urlsafe(32)
        reset_token_expires = datetime.utcnow() + timedelta(hours=1)
        
        collection = await self._get_collection()
        await collection.update_one(
            {"_id": ObjectId(user.id)},
            {
                "$set": {
                    "reset_password_token": reset_token,
                    "reset_password_expires": reset_token_expires,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return {
            "email": user.email,
            "reset_token": reset_token,
            "expires_at": reset_token_expires.isoformat()
        }
    
    async def reset_password(self, token: str, new_password: str) -> bool:
        """Reset user's password using a valid reset token."""
        collection = await self._get_collection()
        
        user = await collection.find_one({
            "reset_password_token": token,
            "reset_password_expires": {"$gt": datetime.utcnow()}
        })
        
        if not user:
            return False
        
        result = await collection.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "hashed_password": get_password_hash(new_password),
                    "updated_at": datetime.utcnow()
                },
                "$unset": {
                    "reset_password_token": "",
                    "reset_password_expires": ""
                }
            }
        )
        
        return result.modified_count == 1
    
    async def update_subscription_preferences(
        self,
        user_id: str,
        preferences: UserSubscriptionPreferences
    ) -> Optional[UserInDB]:
        """Update user's email subscription preferences."""
        collection = await self._get_collection()
        
        result = await collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "subscription_preferences": preferences.model_dump(),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count == 1:
            return await self.get_by_id(user_id)
        return None
    
    async def unsubscribe_user(
        self,
        token: str,
        email_type: Optional[str] = None
    ) -> bool:
        """Unsubscribe user from emails, either all or specific type."""
        collection = await self._get_collection()
        
        if email_type and email_type != 'all':
            # Unsubscribe from specific email type
            result = await collection.update_one(
                {"unsubscribe_token": token},
                {
                    "$set": {
                        f"subscription_preferences.{email_type}": False,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
        else:
            # Unsubscribe from all emails
            result = await collection.update_one(
                {"unsubscribe_token": token},
                {
                    "$set": {
                        "unsubscribed": True,
                        "subscription_preferences": {
                            "price_alerts": False,
                            "market_updates": False,
                            "newsletter": False,
                            "marketing": False
                        },
                        "updated_at": datetime.utcnow()
                    }
                }
            )
        
        return result.modified_count == 1
    
    async def track_email_open(self, user_id: str, email_type: str) -> bool:
        """Track when a user opens an email."""
        collection = await self._get_collection()
        
        result = await collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$inc": {f"email_metrics.{email_type}.opens": 1},
                "$set": {"email_metrics.last_opened": datetime.utcnow()},
                "$push": {"email_metrics.open_history": {
                    "email_type": email_type,
                    "opened_at": datetime.utcnow()
                }}
            }
        )
        
        return result.modified_count == 1
    
    async def track_email_click(
        self,
        user_id: str,
        email_type: str,
        link_url: str,
        link_text: Optional[str] = None
    ) -> bool:
        """Track when a user clicks a link in an email."""
        collection = await self._get_collection()
        
        click_data = {
            "email_type": email_type,
            "link_url": link_url,
            "clicked_at": datetime.utcnow()
        }
        
        if link_text:
            click_data["link_text"] = link_text
        
        result = await collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$inc": {f"email_metrics.{email_type}.clicks": 1},
                "$set": {"email_metrics.last_clicked": datetime.utcnow()},
                "$push": {"email_metrics.click_history": click_data}
            }
        )
        
        return result.modified_count == 1



