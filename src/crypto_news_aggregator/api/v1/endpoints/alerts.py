"""
Alert management endpoints for the Crypto News Aggregator API.
"""
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from bson import ObjectId

from ....models.alert import Alert, AlertCreate, AlertUpdate, AlertCondition
from ....services.alert_service import alert_service
from ....core.security import get_current_active_user
from ....models.user import User

router = APIRouter(prefix="/alerts", tags=["alerts"])

@router.post(
    "/", 
    response_model=Alert,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new alert",
    description="Create a new price alert for the authenticated user."
)
async def create_alert(
    alert: AlertCreate,
    current_user: User = Depends(get_current_active_user)
) -> Alert:
    """
    Create a new price alert.
    
    - **crypto_id**: Cryptocurrency symbol (e.g., 'bitcoin')
    - **condition**: Alert condition type (above, below, percent_up, percent_down)
    - **threshold**: Price or percentage threshold for the alert
    - **is_active**: Whether the alert is active (default: True)
    - **cooldown_minutes**: Minutes to wait before sending another alert (default: 60)
    """
    # Ensure the user ID is set to the current user
    alert.user_id = str(current_user.id)
    
    try:
        created_alert = await alert_service.create_alert(alert)
        return created_alert
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get(
    "/", 
    response_model=List[Alert],
    summary="List user's alerts",
    description="List all alerts for the authenticated user."
)
async def list_alerts(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: User = Depends(get_current_active_user)
) -> List[Alert]:
    """
    List all alerts for the authenticated user with optional filtering.
    """
    return await alert_service.list_alerts(
        user_id=str(current_user.id),
        skip=skip,
        limit=limit,
        is_active=is_active
    )

@router.get(
    "/{alert_id}",
    response_model=Alert,
    summary="Get alert by ID",
    description="Get a specific alert by its ID.",
    responses={
        404: {"description": "Alert not found or access denied"}
    }
)
async def get_alert(
    alert_id: str,
    current_user: User = Depends(get_current_active_user)
) -> Alert:
    """
    Get a specific alert by ID.
    """
    alert = await alert_service.get_alert(alert_id, str(current_user.id))
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found or access denied"
        )
    return alert

@router.put(
    "/{alert_id}",
    response_model=Alert,
    summary="Update an alert",
    description="Update an existing alert by its ID.",
    responses={
        404: {"description": "Alert not found or access denied"}
    }
)
async def update_alert(
    alert_id: str,
    alert_update: AlertUpdate,
    current_user: User = Depends(get_current_active_user)
) -> Alert:
    """
    Update an existing alert.
    
    Only the fields provided in the request will be updated.
    """
    updated_alert = await alert_service.update_alert(
        alert_id=alert_id,
        user_id=str(current_user.id),
        alert_update=alert_update
    )
    
    if not updated_alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found or access denied"
        )
    
    return updated_alert

@router.delete(
    "/{alert_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an alert",
    description="Delete an alert by its ID.",
    responses={
        204: {"description": "Alert deleted successfully"},
        404: {"description": "Alert not found or access denied"}
    }
)
async def delete_alert(
    alert_id: str,
    current_user: User = Depends(get_current_active_user)
) -> None:
    """
    Delete an alert.
    """
    success = await alert_service.delete_alert(alert_id, str(current_user.id))
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found or access denied"
        )
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)

@router.get(
    "/conditions/",
    response_model=List[str],
    summary="List available alert conditions",
    description="List all available alert condition types."
)
async def list_alert_conditions() -> List[str]:
    """
    List all available alert condition types.
    """
    return [condition.value for condition in AlertCondition]
