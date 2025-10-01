from datetime import datetime
from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import Alert, User
from ...models import alert as alert_models


async def get_active_alerts(db: AsyncSession) -> List[Alert]:
    """
    Retrieve all active alerts from the database.

    Args:
        db: AsyncSession - Database session

    Returns:
        List[Alert]: List of active Alert objects with user relationship loaded
    """
    result = await db.execute(
        select(Alert)
        .where(Alert.is_active == True)  # noqa: E712
        .options(selectinload(Alert.user))
    )
    return result.scalars().all()


async def update_alert_last_triggered(
    db: AsyncSession, alert_id: int, triggered_at: Optional[datetime] = None
) -> None:
    """
    Update the last_triggered timestamp for an alert.

    Args:
        db: AsyncSession - Database session
        alert_id: int - ID of the alert to update
        triggered_at: Optional[datetime] - Timestamp to set (defaults to current UTC time)
    """
    if triggered_at is None:
        triggered_at = datetime.utcnow()

    await db.execute(
        update(Alert).where(Alert.id == alert_id).values(last_triggered=triggered_at)
    )
    await db.commit()


async def get_alert_by_id(
    db: AsyncSession, alert_id: int, include_user: bool = True
) -> Optional[Alert]:
    """
    Retrieve an alert by its ID, optionally including the user relationship.

    Args:
        db: AsyncSession - Database session
        alert_id: int - ID of the alert to retrieve
        include_user: bool - Whether to include the user relationship

    Returns:
        Optional[Alert]: The Alert object if found, None otherwise
    """
    query = select(Alert).where(Alert.id == alert_id)

    if include_user:
        query = query.options(selectinload(Alert.user))

    result = await db.execute(query)
    return result.scalars().first()


async def add_alert(db: AsyncSession, alert_in: alert_models.AlertCreate) -> Alert:
    """
    Add a new alert to the database.

    Args:
        db: AsyncSession - Database session
        alert_in: AlertCreate - Pydantic model for alert creation

    Returns:
        Alert: The newly created Alert object
    """
    alert_data = alert_in.model_dump()
    alert_data["symbol"] = alert_data.pop("crypto_id", "BTC")

    condition = alert_data.pop("condition")
    threshold = alert_data.pop("threshold")

    if condition == alert_models.AlertCondition.PERCENT_UP:
        alert_data["direction"] = "above"
        alert_data["threshold_percentage"] = threshold
    elif condition == alert_models.AlertCondition.PERCENT_DOWN:
        alert_data["direction"] = "below"
        alert_data["threshold_percentage"] = threshold
    elif condition == alert_models.AlertCondition.ABOVE:
        alert_data["direction"] = "above"
        alert_data["price_target"] = threshold
    elif condition == alert_models.AlertCondition.BELOW:
        alert_data["direction"] = "below"
        alert_data["price_target"] = threshold

    # Remove fields from Pydantic model that are not in the SQLAlchemy model
    alert_data.pop("cooldown_minutes", None)
    alert_data.pop("initial_price", None)

    new_alert = Alert(**alert_data)
    db.add(new_alert)
    await db.commit()
    await db.refresh(new_alert)
    return new_alert
