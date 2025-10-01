"""Database operations for price alerts."""

from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, update, delete
from sqlalchemy.orm import selectinload, joinedload

from ...models.alert import (
    Alert as AlertModel,
    AlertCreate,
    AlertUpdate,
    AlertDirection,
)
from ..models import Alert as AlertDB, User
from ...models.user import User as UserModel


async def get_alert(
    db: AsyncSession, alert_id: int, user_id: Optional[int] = None
) -> Optional[AlertModel]:
    """
    Get an alert by ID, optionally filtered by user ID.

    Args:
        db: Database session
        alert_id: ID of the alert to retrieve
        user_id: Optional user ID to filter by (for user-specific access)

    Returns:
        Optional[AlertModel]: The alert if found, None otherwise
    """
    query = select(AlertDB).where(AlertDB.id == alert_id)

    # If user_id is provided, filter by user_id
    if user_id is not None:
        query = query.where(AlertDB.user_id == user_id)

    result = await db.execute(query)
    alert = result.scalars().first()

    return AlertModel.from_orm(alert) if alert else None


async def get_user_alerts(
    db: AsyncSession,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    active_only: bool = False,
    symbol: Optional[str] = None,
) -> Tuple[List[AlertModel], int]:
    """
    Get paginated list of alerts for a specific user.

    Args:
        db: Database session
        user_id: ID of the user to get alerts for
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return (for pagination)
        active_only: If True, only return active alerts
        symbol: Optional symbol to filter by

    Returns:
        Tuple containing a list of alerts and the total count
    """
    # Build the base query
    query = select(AlertDB).where(AlertDB.user_id == user_id)

    # Apply filters
    if active_only:
        query = query.where(AlertDB.is_active == True)  # noqa: E712

    if symbol:
        query = query.where(AlertDB.symbol == symbol.upper())

    # Get total count for pagination
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    # Apply pagination and ordering
    query = query.order_by(AlertDB.created_at.desc()).offset(skip).limit(limit)

    # Execute the query
    result = await db.execute(query)
    alerts = result.scalars().all()

    return [AlertModel.from_orm(alert) for alert in alerts], total


async def create_alert(
    db: AsyncSession,
    alert_in: AlertCreate,
    user_id: int,
) -> AlertModel:
    """
    Create a new alert for a user.

    Args:
        db: Database session
        alert_in: Alert creation data
        user_id: ID of the user creating the alert

    Returns:
        AlertModel: The created alert

    Raises:
        ValueError: If the user already has an identical is_active alert
    """
    # Check for duplicate is_active alert
    existing_alert = await db.execute(
        select(AlertDB).where(
            and_(
                AlertDB.user_id == user_id,
                AlertDB.symbol == alert_in.symbol.upper(),
                AlertDB.threshold_percentage == alert_in.threshold_percentage,
                AlertDB.direction == alert_in.direction,
                AlertDB.is_active == True,  # noqa: E712
            )
        )
    )

    if existing_alert.scalars().first():
        raise ValueError("An identical is_active alert already exists")

    # Create the alert
    db_alert = AlertDB(
        user_id=user_id,
        symbol=alert_in.symbol.upper(),
        threshold_percentage=alert_in.threshold_percentage,
        direction=alert_in.direction,
        is_active=alert_in.is_active,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(db_alert)
    await db.commit()
    await db.refresh(db_alert)

    return AlertModel.from_orm(db_alert)


async def update_alert(
    db: AsyncSession,
    db_alert: AlertDB,
    alert_in: AlertUpdate,
) -> AlertModel:
    """
    Update an existing alert.

    Args:
        db: Database session
        db_alert: The alert to update
        alert_in: The update data

    Returns:
        AlertModel: The updated alert

    Raises:
        ValueError: If the update would create a duplicate is_active alert
    """
    update_data = alert_in.model_dump(exclude_unset=True)

    # Check if the update would create a duplicate is_active alert
    if any(
        field in update_data
        for field in ["symbol", "threshold_percentage", "direction"]
    ):
        symbol = update_data.get("symbol", db_alert.symbol).upper()
        threshold = update_data.get(
            "threshold_percentage", db_alert.threshold_percentage
        )
        direction = update_data.get("direction", db_alert.direction)

        existing_alert = await db.execute(
            select(AlertDB).where(
                and_(
                    AlertDB.user_id == db_alert.user_id,
                    AlertDB.id != db_alert.id,  # Exclude the current alert
                    AlertDB.symbol == symbol,
                    AlertDB.threshold_percentage == threshold,
                    AlertDB.direction == direction,
                    AlertDB.is_active == True,  # noqa: E712
                )
            )
        )

        if existing_alert.scalars().first():
            raise ValueError("An identical is_active alert already exists")

    # Update the alert
    for field, value in update_data.items():
        if field == "symbol" and value is not None:
            setattr(db_alert, field, value.upper())
        else:
            setattr(db_alert, field, value)

    db_alert.updated_at = datetime.utcnow()

    db.add(db_alert)
    await db.commit()
    await db.refresh(db_alert)

    return AlertModel.from_orm(db_alert)


async def delete_alert(
    db: AsyncSession,
    alert_id: int,
    user_id: Optional[int] = None,
) -> bool:
    """
    Delete an alert.

    Args:
        db: Database session
        alert_id: ID of the alert to delete
        user_id: Optional user ID to verify ownership

    Returns:
        bool: True if the alert was deleted, False if not found
    """
    query = delete(AlertDB).where(AlertDB.id == alert_id)

    if user_id is not None:
        query = query.where(AlertDB.user_id == user_id)

    result = await db.execute(query)
    await db.commit()

    return result.rowcount > 0


async def get_active_alerts_for_symbol(
    db: AsyncSession,
    symbol: str,
    current_price: float,
) -> List[Dict[str, Any]]:
    """
    Get all is_active alerts that should be triggered for a given symbol and price.

    Args:
        db: Database session
        symbol: Cryptocurrency symbol (e.g., 'BTC')
        current_price: Current price of the cryptocurrency

    Returns:
        List of dictionaries containing alert and user information
    """
    symbol = symbol.upper()

    # Calculate price thresholds for up and down alerts
    up_threshold = current_price * 1.01  # 1% above current price
    down_threshold = current_price * 0.99  # 1% below current price

    # Query for alerts that should be triggered
    query = (
        select(AlertDB, User)
        .join(User, AlertDB.user_id == User.id)
        .where(
            and_(
                AlertDB.symbol == symbol,
                AlertDB.is_active == True,  # noqa: E712
                or_(
                    # Price went up and alert is for price going up
                    and_(
                        AlertDB.direction.in_([AlertDirection.UP, AlertDirection.BOTH]),
                        (
                            AlertDB.threshold_percentage
                            <= (
                                (current_price / AlertDB.last_triggered_price - 1) * 100
                            )
                            if AlertDB.last_triggered_price is not None
                            else True
                        ),
                        (
                            AlertDB.threshold_percentage
                            <= ((current_price / AlertDB.created_at_price - 1) * 100)
                            if AlertDB.created_at_price is not None
                            else True
                        ),
                    ),
                    # Price went down and alert is for price going down
                    and_(
                        AlertDB.direction.in_(
                            [AlertDirection.DOWN, AlertDirection.BOTH]
                        ),
                        (
                            AlertDB.threshold_percentage
                            <= (
                                (AlertDB.last_triggered_price / current_price - 1) * 100
                            )
                            if AlertDB.last_triggered_price is not None
                            else True
                        ),
                        (
                            AlertDB.threshold_percentage
                            <= ((AlertDB.created_at_price / current_price - 1) * 100)
                            if AlertDB.created_at_price is not None
                            else True
                        ),
                    ),
                ),
            )
        )
    )

    result = await db.execute(query)
    alerts = result.all()

    # Format the results
    triggered_alerts = []
    for alert_db, user in alerts:
        alert = AlertModel.from_orm(alert_db)
        triggered_alerts.append(
            {
                "alert": alert,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                },
                "current_price": current_price,
            }
        )

    return triggered_alerts


async def mark_alert_triggered(
    db: AsyncSession,
    alert_id: int,
    current_price: float,
) -> None:
    """
    Update an alert's last_triggered timestamp and price.

    Args:
        db: Database session
        alert_id: ID of the alert to update
        current_price: The price at which the alert was triggered
    """
    await db.execute(
        update(AlertDB)
        .where(AlertDB.id == alert_id)
        .values(
            last_triggered=datetime.utcnow(),
            last_triggered_price=current_price,
            updated_at=datetime.utcnow(),
        )
    )
    await db.commit()
