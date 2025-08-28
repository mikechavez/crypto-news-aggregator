"""
Test endpoints for manual alert triggering and testing.
"""
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ....db.session import get_db
from ....models.alert import Alert, AlertCreate, AlertDirection
from ....models.user import User as UserModel
from ....core.security import get_current_active_user
from ....services.notification_service import notification_service
from ....services.price_monitor import PriceMonitor
from ....core.config import settings

router = APIRouter(
    prefix="/test/alerts",
    tags=["test"],
    dependencies=[Depends(get_current_active_user)],
    responses={404: {"description": "Not found"}},
)

@router.post(
    "/trigger-manual",
    status_code=status.HTTP_200_OK,
    summary="Trigger a manual price alert",
    description="""
    Manually trigger a price alert for testing purposes.
    This endpoint simulates a price change and sends an alert with the specified parameters.
    """
)
async def trigger_manual_alert(
    symbol: str = Query(..., description="Cryptocurrency symbol (e.g., 'BTC')"),
    price: float = Query(..., gt=0, description="Current price"),
    price_change_24h: float = Query(..., description="24h price change percentage"),
    alert_threshold: float = Query(5.0, gt=0, description="Alert threshold percentage"),
    alert_direction: str = Query("both", description="Alert direction (up/down/both)"),
    include_articles: bool = Query(True, description="Include test articles in the alert"),
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Manually trigger a price alert with the specified parameters.
    
    This endpoint is for testing purposes only and should be disabled in production.
    """
    # Check if testing is enabled
    if not settings.DEBUG and not settings.TESTING:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manual alert triggering is disabled in production"
        )
    
    # Create a test alert
    alert_data = AlertCreate(
        symbol=symbol.upper(),
        threshold_percentage=alert_threshold,
        direction=AlertDirection(alert_direction.lower()),
        active=True
    )
    
    # Prepare test articles if requested
    context_articles = []
    if include_articles:
        context_articles = [
            {
                "title": f"{symbol} Price Analysis: {'Up' if price_change_24h > 0 else 'Down'} {abs(price_change_24h):.2f}% in 24h",
                "source": "Test Source",
                "url": f"https://example.com/{symbol.lower()}-analysis",
                "published_at": datetime.utcnow().isoformat(),
                "snippet": f"The price of {symbol} has changed by {price_change_24h:+.2f}% in the last 24 hours.",
                "score": 0.95
            },
            {
                "title": f"Market Update: {symbol} Shows {'Bullish' if price_change_24h > 0 else 'Bearish'} Momentum",
                "source": "Crypto News",
                "url": f"https://example.com/market-update-{symbol.lower()}",
                "published_at": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
                "snippet": f"Traders are watching {symbol} closely as it shows {'strong' if abs(price_change_24h) > 5 else 'moderate'} {'gains' if price_change_24h > 0 else 'losses'}.",
                "score": 0.85
            }
        ]
    
    try:
        # Simulate alert processing
        stats = await notification_service.process_price_alert(
            db=db,
            crypto_id=symbol.lower(),
            crypto_name=symbol,
            crypto_symbol=symbol.upper(),
            current_price=price,
            price_change_24h=price_change_24h,
            context_articles=context_articles
        )
        
        return {
            "status": "success",
            "message": "Test alert processed successfully",
            "alert_data": alert_data.model_dump(),
            "stats": stats
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process test alert: {str(e)}"
        )

@router.get(
    "/test-email",
    status_code=status.HTTP_200_OK,
    summary="Send a test email",
    response_description="Test email status",
    responses={
        200: {
            "description": "Test email sent successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Test email sent successfully",
                        "email": "user@example.com",
                        "status": "success"
                    }
                }
            }
        },
        400: {"description": "Invalid email address"},
        403: {"description": "Test email is disabled in production"},
        500: {"description": "Failed to send test email"}
    }
)
async def send_test_email(
    email: str = Query(
        ...,
        description="Email address to send the test to",
        example="test@example.com",
        pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    ),
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, str]:
    """
    Send a test email to verify the email service is working.
    
    This endpoint sends a test email to the specified address with a sample
    message to verify that the email service is properly configured.
    
    Args:
        email: The email address to send the test to
        current_user: The currently authenticated user
        
    Returns:
        Dict containing the status of the email sending operation
        
    Raises:
        HTTPException: If test emails are disabled or sending fails
    """
    # Check if testing is enabled
    if not settings.DEBUG and not settings.TESTING:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Test email is disabled in production"
        )
    
    from ....services.email_service import send_email_alert
    from ....utils.template_renderer import template_renderer
    
    try:
        # Render test email template
        context = {
            "user_name": current_user.username or "Test User",
            "current_year": datetime.now().year,
            "email": email,
            "test_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")
        }
        
        # Render both HTML and plain text versions
        html_content = await template_renderer.render_template(
            "emails/test_email.html",
            context
        )
        
        # Send the test email
        success, message_id = await send_email_alert(
            to=email,
            subject="✅ Test Email from Crypto News Aggregator",
            html_content=html_content,
            user_id=str(current_user.id),
            template_name="test_email",
            metadata={
                "test": True,
                "user_id": str(current_user.id),
                "email_type": "test_email"
            }
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send test email: {message_id or 'Unknown error'}"
            )
            
        return {
            "message": "Test email sent successfully",
            "email": email,
            "status": "success",
            "message_id": message_id
        }
        
    except Exception as e:
        logger.error(f"Failed to send test email to {email}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send test email: {str(e)}"
        )
