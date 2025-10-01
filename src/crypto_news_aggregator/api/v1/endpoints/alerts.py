"""
Alert management endpoints for the Crypto News Aggregator API.
"""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from ....db.session import get_db
from ....models.alert import Alert, AlertCreate, AlertUpdate, AlertDirection
from ....db.operations import alerts as alert_ops
from ....db.models import Alert as AlertDB
from ....core.security import get_current_active_user
from ....models.user import User as UserModel

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post(
    "/",
    response_model=Alert,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new alert",
    description="Create a new price alert for the authenticated user.",
)
async def create_alert(
    alert: AlertCreate,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Alert:
    """
    Create a new price alert.

    - **symbol**: Cryptocurrency symbol (e.g., 'BTC')
    - **threshold_percentage**: Percentage change to trigger the alert
    - **direction**: Alert direction (up, down, both)
    - **active**: Whether the alert is active (default: True)
    """
    try:
        created_alert = await alert_ops.create_alert(
            db=db, alert_in=alert, user_id=current_user.id
        )
        return created_alert
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the alert",
        )


@router.get(
    "/",
    response_model=Dict[str, Any],
    summary="List user's alerts",
    description="List all alerts for the authenticated user with pagination.",
)
async def list_alerts(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of records to return"
    ),
    active: Optional[bool] = Query(None, description="Filter by active status"),
    symbol: Optional[str] = Query(None, description="Filter by cryptocurrency symbol"),
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    List all alerts for the authenticated user with optional filtering and pagination.
    """
    try:
        alerts, total = await alert_ops.get_user_alerts(
            db=db,
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            active_only=active if active is not None else False,
            symbol=symbol,
        )

        return {"items": alerts, "total": total, "skip": skip, "limit": limit}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching alerts",
        )


@router.get(
    "/{alert_id}",
    response_model=Alert,
    summary="Get alert by ID",
    description="Get a specific alert by its ID.",
    responses={404: {"description": "Alert not found or access denied"}},
)
async def get_alert(
    alert_id: int,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Alert:
    """
    Get a specific alert by ID.
    """
    try:
        alert = await alert_ops.get_alert(
            db=db, alert_id=alert_id, user_id=current_user.id
        )

        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found or access denied",
            )

        return alert
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching the alert",
        )


@router.put(
    "/{alert_id}",
    response_model=Alert,
    summary="Update an alert",
    description="Update an existing alert by its ID.",
    responses={
        404: {"description": "Alert not found or access denied"},
        400: {"description": "Invalid update data"},
    },
)
async def update_alert(
    alert_id: int,
    alert_update: AlertUpdate,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Alert:
    """
    Update an existing alert.
    """
    try:
        # First get the alert to ensure it exists and belongs to the user
        db_alert = await db.execute(
            select(AlertDB).where(
                and_(AlertDB.id == alert_id, AlertDB.user_id == current_user.id)
            )
        )
        db_alert = db_alert.scalars().first()

        if not db_alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found or access denied",
            )

        # Update the alert
        updated_alert = await alert_ops.update_alert(
            db=db, db_alert=db_alert, alert_in=alert_update
        )

        return updated_alert

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the alert",
        )


@router.delete(
    "/{alert_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an alert",
    description="Delete an alert by its ID.",
    responses={404: {"description": "Alert not found or access denied"}},
)
async def delete_alert(
    alert_id: int,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete an alert.
    """
    try:
        success = await alert_ops.delete_alert(
            db=db, alert_id=alert_id, user_id=current_user.id
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found or access denied",
            )

        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the alert",
        )


@router.get(
    "/directions",
    response_model=List[Dict[str, str]],
    summary="List alert directions",
    description="List all available alert direction types.",
)
async def list_alert_directions():
    """
    List all available alert direction types.
    """
    return [
        {
            "name": direction.value,
            "description": f"Alert when price moves {direction.value}",
        }
        for direction in AlertDirection
    ]


@router.post(
    "/check/{symbol}",
    response_model=List[Dict[str, Any]],
    summary="Check for triggered alerts",
    description="Check if any alerts should be triggered for a symbol at the given price.",
    responses={
        200: {"description": "List of triggered alerts"},
        400: {"description": "Invalid symbol or price"},
    },
)
async def check_alerts(
    symbol: str,
    price: float = Query(..., gt=0, description="Current price of the symbol"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[UserModel] = Depends(get_current_active_user),
) -> List[Dict[str, Any]]:
    """
    Check if any alerts should be triggered for a symbol at the given price.

    This endpoint is primarily for internal use by the price monitoring service.
    """
    if not symbol or price <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid symbol or price"
        )

    try:
        # Get all active alerts that should be triggered
        triggered_alerts = await alert_ops.get_active_alerts_for_symbol(
            db=db, symbol=symbol, current_price=price
        )

        # Mark alerts as triggered (in the background)
        for alert_data in triggered_alerts:
            await alert_ops.mark_alert_triggered(
                db=db, alert_id=alert_data["alert"].id, current_price=price
            )

        return triggered_alerts

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while checking alerts",
        )
