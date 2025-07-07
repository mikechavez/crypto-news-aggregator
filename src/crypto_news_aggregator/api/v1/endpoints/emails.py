"""
Email tracking and management endpoints.
"""
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status, Response
from fastapi.responses import RedirectResponse, HTMLResponse
from bson import ObjectId
from pydantic import BaseModel

from ....core.config import settings
from ....db.mongodb import get_database
from ....models.user import User, UserInDB, UserUpdate
from ....services.email_service import email_service
from ....db.mongodb_models import EmailTracking, EmailEvent, EmailEventType
from ....core.security import get_current_active_user
from ....utils.template_renderer import template_renderer

router = APIRouter()
logger = logging.getLogger(__name__)

class UnsubscribeRequest(BaseModel):
    """Request model for unsubscribing from emails."""
    email_type: Optional[str] = None  # Optional: unsubscribe from specific type of emails

@router.get("/track/open/{message_id}", response_class=HTMLResponse)
async def track_email_open(
    message_id: str,
    request: Request,
    response: Response,
):
    """
    Track when an email is opened by the recipient.
    This endpoint is called when the tracking pixel in an email is loaded.
    """
    db = await get_database()
    
    # Record the open event
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    # Get the tracking record
    tracking = await db.email_tracking.find_one({"message_id": message_id})
    if not tracking:
        # Return a 1x1 transparent pixel
        return Response(
            content=b"""\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b""",
            media_type="image/gif"
        )
    
    # Check if we've already recorded an open event for this message
    existing_open = next(
        (e for e in tracking.get("events", []) if e.get("event_type") == EmailEventType.OPENED),
        None
    )
    
    if not existing_open:
        # Record the open event
        event = {
            "event_type": EmailEventType.OPENED,
            "timestamp": datetime.utcnow(),
            "ip_address": ip_address,
            "user_agent": user_agent,
            "details": {
                "headers": dict(request.headers),
                "client": str(request.client) if request.client else None
            }
        }
        
        await db.email_tracking.update_one(
            {"message_id": message_id},
            {"$push": {"events": event}},
            upsert=False
        )
        
        logger.info(f"Email opened: {message_id}")
    
    # Return a 1x1 transparent pixel
    return Response(
        content=b"""\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b""",
        media_type="image/gif"
    )

@router.get("/track/click/{message_id}/{link_hash}")
async def track_link_click(
    message_id: str,
    link_hash: str,
    request: Request,
):
    """
    Track when a link in an email is clicked.
    This endpoint redirects to the original URL after recording the click.
    """
    db = await get_database()
    
    # Get the tracking record
    tracking = await db.email_tracking.find_one({"message_id": message_id})
    if not tracking:
        raise HTTPException(status_code=404, detail="Email not found")
    
    # Get the original URL from the link mapping
    link_mapping = tracking.get("metadata", {}).get("links", {})
    original_url = link_mapping.get(link_hash)
    
    if not original_url:
        raise HTTPException(status_code=404, detail="Link not found")
    
    # Record the click event
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    event = {
        "event_type": EmailEventType.CLICKED,
        "timestamp": datetime.utcnow(),
        "ip_address": ip_address,
        "user_agent": user_agent,
        "details": {
            "link_hash": link_hash,
            "original_url": original_url,
            "headers": dict(request.headers),
            "client": str(request.client) if request.client else None
        }
    }
    
    await db.email_tracking.update_one(
        {"message_id": message_id},
        {
            "$push": {"events": event},
            "$set": {"updated_at": datetime.utcnow()}
        },
        upsert=False
    )
    
    logger.info(f"Link clicked: {original_url} (message: {message_id})")
    
    # Redirect to the original URL
    return RedirectResponse(url=original_url, status_code=302)

@router.post("/unsubscribe/{token}", response_class=HTMLResponse)
async def unsubscribe_email(
    token: str,
    request: Request,
    unsubscribe_request: Optional[UnsubscribeRequest] = None,
):
    """
    Handle email unsubscription requests.
    This endpoint is called when a user clicks the unsubscribe link in an email.
    """
    db = await get_database()
    
    # In a real implementation, you would validate the token and identify the user
    # For now, we'll just log the unsubscription
    logger.info(f"Unsubscribe request received with token: {token}")
    
    # Get user ID and email from the token (in a real app, you would validate this)
    # This is a simplified example - in production, use a proper token validation mechanism
    user = await db.users.find_one({"unsubscribe_token": token})
    
    if not user:
        return HTMLResponse(
            content="<h1>Invalid or expired unsubscribe link</h1>"
                   "<p>The unsubscribe link you used is invalid or has expired.</p>",
            status_code=400
        )
    
    # Update user's email preferences
    update_data = {"unsubscribed": True}
    
    # If a specific email type was specified, update only that preference
    if unsubscribe_request and unsubscribe_request.email_type:
        update_data[f"subscription_preferences.{unsubscribe_request.email_type}"] = False
    
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": update_data}
    )
    
    # Render the unsubscription confirmation page
    html_content = template_renderer.render_template(
        "emails/unsubscribe_success.html",
        user=user,
        email_type=unsubscribe_request.email_type if unsubscribe_request else None,
        support_email=settings.SUPPORT_EMAIL
    )
    
    return HTMLResponse(content=html_content, status_code=200)

@router.get("/tracking/{message_id}", response_model=EmailTracking)
async def get_email_tracking(
    message_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get tracking information for a specific email.
    Only accessible by the recipient or an admin.
    """
    db = await get_database()
    
    # Get the tracking record
    tracking = await db.email_tracking.find_one({"message_id": message_id})
    if not tracking:
        raise HTTPException(status_code=404, detail="Email not found")
    
    # Check if the current user is the recipient or an admin
    if str(tracking["user_id"]) != str(current_user.id) and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this email tracking information"
        )
    
    return tracking

@router.get("/tracking/user/{user_id}", response_model=list[EmailTracking])
async def get_user_email_tracking(
    user_id: str,
    current_user: User = Depends(get_current_active_user),
    limit: int = 50,
    skip: int = 0
):
    """
    Get email tracking information for a specific user.
    Only accessible by the user themselves or an admin.
    """
    # Check if the current user is the requested user or an admin
    if str(user_id) != str(current_user.id) and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this user's email tracking information"
        )
    
    db = await get_database()
    
    # Get tracking records for the user, most recent first
    cursor = db.email_tracking.find({"user_id": ObjectId(user_id)}) \
        .sort("sent_at", -1) \
        .skip(skip) \
        .limit(limit)
    
    return [doc async for doc in cursor]
