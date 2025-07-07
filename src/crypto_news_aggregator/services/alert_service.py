"""
Alert service for handling alert-related operations.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Union
from bson import ObjectId

from ..models.alert import AlertInDB, AlertCreate, AlertUpdate, AlertStatus
from ..db.mongodb import mongo_manager, COLLECTION_ALERTS
from ..core.config import settings

logger = logging.getLogger(__name__)

class AlertService:
    """Service for handling alert operations."""
    
    def __init__(self):
        self.collection_name = COLLECTION_ALERTS
    
    async def _get_collection(self) -> Any:
        """Get the MongoDB collection for alerts."""
        if not hasattr(self, '_collection'):
            self._collection = await mongo_manager.get_async_collection(self.collection_name)
        return self._collection
    
    async def create_alert(self, alert: Union[AlertCreate, Dict[str, Any]]) -> AlertInDB:
        """
        Create a new alert.
        
        Args:
            alert: Alert data to create (can be dict or Pydantic model)
            
        Returns:
            AlertInDB: The created alert
        """
        collection = await self._get_collection()
        
        if isinstance(alert, dict):
            alert_dict = alert
        else:
            alert_dict = alert.dict(by_alias=True, exclude={"id"})
        
        # Set timestamps
        now = datetime.now(timezone.utc)
        alert_dict.update({
            "created_at": now,
            "updated_at": now,
            "status": AlertStatus.ACTIVE.value
        })
        
        result = await collection.insert_one(alert_dict)
        created_alert = await collection.find_one({"_id": result.inserted_id})
        
        # Convert ObjectId to string for Pydantic model
        if created_alert and "_id" in created_alert:
            created_alert["_id"] = str(created_alert["_id"])
            
        return AlertInDB(**created_alert)
    
    async def get_active_alerts(self) -> List[AlertInDB]:
        """
        Get all active alerts that are not deleted.
        
        Returns:
            List[AlertInDB]: List of active alerts
        """
        collection = await self._get_collection()
        cursor = collection.find({
            "status": AlertStatus.ACTIVE.value
        })
        
        alerts = []
        async for doc in cursor:
            # Convert ObjectId to string for Pydantic model
            if "_id" in doc:
                doc["id"] = str(doc["_id"])
                del doc["_id"]
            alerts.append(AlertInDB(**doc))
            
        return alerts
        
    async def update_alert(
        self, 
        alert_id: str, 
        update_data: Union[AlertUpdate, Dict[str, Any]],
        **kwargs
    ) -> Optional[AlertInDB]:
        """
        Update an alert.
        
        Args:
            alert_id: ID of the alert to update
            update_data: Data to update
            **kwargs: Additional fields to update
            
        Returns:
            Optional[AlertInDB]: The updated alert, or None if not found
        """
        collection = await self._get_collection()
        
        if isinstance(update_data, dict):
            update_dict = update_data
        else:
            update_dict = update_data.dict(exclude_unset=True, exclude={"id"})
        
        # Add any additional fields from kwargs
        update_dict.update(kwargs)
        
        # Always update the updated_at timestamp
        update_dict["updated_at"] = datetime.now(timezone.utc)
        
        # Ensure we're using a valid ObjectId
        try:
            alert_oid = ObjectId(alert_id)
        except Exception as e:
            logger.error(f"Invalid alert ID format: {alert_id}")
            return None
        
        result = await collection.update_one(
            {"_id": alert_oid},
            {"$set": update_dict}
        )
        
        if result.modified_count == 0:
            logger.warning(f"No alert found with ID {alert_id} or no changes made")
            return None
            
        # Retrieve the updated document
        updated_doc = await collection.find_one({"_id": alert_oid})
        if not updated_doc:
            logger.error(f"Failed to retrieve updated alert {alert_id}")
            return None
            
        # Convert ObjectId to string for Pydantic model
        if "_id" in updated_doc:
            updated_doc["id"] = str(updated_doc["_id"])
            del updated_doc["_id"]
            
        return AlertInDB(**updated_doc)
    
    async def get_alert(self, alert_id: str) -> Optional[AlertInDB]:
        """
        Get an alert by ID.
        
        Args:
            alert_id: ID of the alert to get
            
        Returns:
            Optional[AlertInDB]: The alert if found, None otherwise
        """
        collection = await self._get_collection()
        
        try:
            alert_oid = ObjectId(alert_id)
        except Exception as e:
            logger.error(f"Invalid alert ID format: {alert_id}")
            return None
            
        alert = await collection.find_one({"_id": alert_oid})
        
        if not alert:
            logger.debug(f"No alert found with ID {alert_id}")
            return None
            
        # Convert ObjectId to string for Pydantic model
        if "_id" in alert:
            alert["id"] = str(alert["_id"])
            del alert["_id"]
            
        return AlertInDB(**alert)
    
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
