"""
Alert service for handling alert-related operations.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from bson import ObjectId

from ..models.alert import AlertInDB, AlertCreate, AlertUpdate, AlertCondition
from ..db.mongodb import mongo_manager, COLLECTION_ALERTS
from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class AlertService:
    """Service for handling alert operations."""
    
    def __init__(self):
        self.collection_name = COLLECTION_ALERTS
    
    async def _get_collection(self) -> Any:
        """Get the MongoDB collection for alerts."""
        if not hasattr(self, '_collection'):
            self._collection = await mongo_manager.get_async_collection(self.collection_name)
        return self._collection
    
    async def create_alert(self, alert: AlertCreate) -> AlertInDB:
        """
        Create a new alert.
        
        Args:
            alert: Alert data to create
            
        Returns:
            AlertInDB: The created alert
        """
        collection = await self._get_collection()
        alert_dict = alert.dict(by_alias=True, exclude={"id"})
        alert_dict["created_at"] = datetime.utcnow()
        
        result = await collection.insert_one(alert_dict)
        created_alert = await collection.find_one({"_id": result.inserted_id})
        return AlertInDB(**created_alert)
    
    async def get_alert(self, alert_id: str, user_id: str) -> Optional[AlertInDB]:
        """
        Get an alert by ID and user ID.
        
        Args:
            alert_id: The ID of the alert to retrieve
            user_id: The ID of the user who owns the alert
            
        Returns:
            Optional[AlertInDB]: The alert if found, None otherwise
        """
        collection = await self._get_collection()
        alert = await collection.find_one({"_id": ObjectId(alert_id), "user_id": user_id})
        return AlertInDB(**alert) if alert else None
    
    async def list_alerts(
        self, 
        user_id: str, 
        skip: int = 0, 
        limit: int = 100,
        is_active: Optional[bool] = None
    ) -> List[AlertInDB]:
        """
        List alerts for a user with optional filtering.
        
        Args:
            user_id: The ID of the user
            skip: Number of records to skip
            limit: Maximum number of records to return
            is_active: Filter by active status
            
        Returns:
            List[AlertInDB]: List of alerts
        """
        collection = await self._get_collection()
        query = {"user_id": user_id}
        
        if is_active is not None:
            query["is_active"] = is_active
            
        cursor = collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
        return [AlertInDB(**alert) async for alert in cursor]
    
    async def update_alert(
        self, 
        alert_id: str, 
        user_id: str, 
        alert_update: AlertUpdate
    ) -> Optional[AlertInDB]:
        """
        Update an alert.
        
        Args:
            alert_id: The ID of the alert to update
            user_id: The ID of the user who owns the alert
            alert_update: The fields to update
            
        Returns:
            Optional[AlertInDB]: The updated alert if found, None otherwise
        """
        collection = await self._get_collection()
        update_data = alert_update.dict(exclude_unset=True)
        
        # Don't update these fields
        update_data.pop("id", None)
        update_data.pop("user_id", None)
        
        # Update the last_updated timestamp
        update_data["updated_at"] = datetime.utcnow()
        
        result = await collection.update_one(
            {"_id": ObjectId(alert_id), "user_id": user_id},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            return None
            
        updated_alert = await collection.find_one({"_id": ObjectId(alert_id)})
        return AlertInDB(**updated_alert) if updated_alert else None
    
    async def delete_alert(self, alert_id: str, user_id: str) -> bool:
        """
        Delete an alert.
        
        Args:
            alert_id: The ID of the alert to delete
            user_id: The ID of the user who owns the alert
            
        Returns:
            bool: True if the alert was deleted, False otherwise
        """
        collection = await self._get_collection()
        result = await collection.delete_one({"_id": ObjectId(alert_id), "user_id": user_id})
        return result.deleted_count > 0
    
    async def get_active_alerts_for_crypto(
        self, 
        crypto_id: str
    ) -> List[AlertInDB]:
        """
        Get all active alerts for a specific cryptocurrency.
        
        Args:
            crypto_id: The ID of the cryptocurrency
            
        Returns:
            List[AlertInDB]: List of active alerts for the cryptocurrency
        """
        collection = await self._get_collection()
        query = {
            "crypto_id": crypto_id.lower(),
            "is_active": True
        }
        cursor = collection.find(query)
        return [AlertInDB(**alert) async for alert in cursor]
    
    async def mark_alert_triggered(self, alert_id: str) -> None:
        """
        Update the last_triggered timestamp for an alert.
        
        Args:
            alert_id: The ID of the alert that was triggered
        """
        collection = await self._get_collection()
        await collection.update_one(
            {"_id": ObjectId(alert_id)},
            {"$set": {"last_triggered": datetime.utcnow()}}
        )


# Singleton instance
alert_service = AlertService()
