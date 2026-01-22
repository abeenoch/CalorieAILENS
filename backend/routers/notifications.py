from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import User, NotificationPreference, Meal
from schemas import NotificationPreferenceUpdate, NotificationPreferenceResponse
from auth import get_current_user

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/preferences", response_model=NotificationPreferenceResponse)
async def get_notification_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's notification preferences."""
    result = await db.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == current_user.id
        )
    )
    prefs = result.scalar_one_or_none()
    
    if not prefs:
        # Create default preferences
        prefs = NotificationPreference(
            user_id=current_user.id,
            meal_reminders_enabled=True,
            meal_reminder_time="12:00",
            weekly_summary_enabled=True,
            weekly_summary_day="sunday",
            weekly_summary_time="19:00"
        )
        db.add(prefs)
        await db.commit()
        await db.refresh(prefs)
    
    return NotificationPreferenceResponse(
        meal_reminders_enabled=prefs.meal_reminders_enabled,
        meal_reminder_time=prefs.meal_reminder_time,
        weekly_summary_enabled=prefs.weekly_summary_enabled,
        weekly_summary_day=prefs.weekly_summary_day,
        weekly_summary_time=prefs.weekly_summary_time
    )


@router.put("/preferences", response_model=NotificationPreferenceResponse)
async def update_notification_preferences(
    request: NotificationPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user's notification preferences."""
    result = await db.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == current_user.id
        )
    )
    prefs = result.scalar_one_or_none()
    
    if not prefs:
        prefs = NotificationPreference(user_id=current_user.id)
        db.add(prefs)
    
    # Update fields
    if request.meal_reminders_enabled is not None:
        prefs.meal_reminders_enabled = request.meal_reminders_enabled
    if request.meal_reminder_time is not None:
        prefs.meal_reminder_time = request.meal_reminder_time
    if request.weekly_summary_enabled is not None:
        prefs.weekly_summary_enabled = request.weekly_summary_enabled
    if request.weekly_summary_day is not None:
        prefs.weekly_summary_day = request.weekly_summary_day
    if request.weekly_summary_time is not None:
        prefs.weekly_summary_time = request.weekly_summary_time
    
    prefs.updated_at = datetime.now(datetime.now().astimezone().tzinfo)
    
    await db.commit()
    await db.refresh(prefs)
    
    return NotificationPreferenceResponse(
        meal_reminders_enabled=prefs.meal_reminders_enabled,
        meal_reminder_time=prefs.meal_reminder_time,
        weekly_summary_enabled=prefs.weekly_summary_enabled,
        weekly_summary_day=prefs.weekly_summary_day,
        weekly_summary_time=prefs.weekly_summary_time
    )


@router.get("/check-meal-reminder")
async def check_meal_reminder(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Check if user should receive a meal reminder.
    
    Returns whether the user has meal reminders enabled and if it's time to send one.
    """
    result = await db.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == current_user.id
        )
    )
    prefs = result.scalar_one_or_none()
    
    if not prefs or not prefs.meal_reminders_enabled:
        return {"should_remind": False, "reason": "Reminders disabled"}
    
    # Check if user has logged a meal today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(Meal).where(
            Meal.user_id == current_user.id,
            Meal.created_at >= today_start
        )
    )
    meals_today = result.scalars().all()
    
    if len(meals_today) > 0:
        return {"should_remind": False, "reason": "Meal already logged today"}
    
    return {
        "should_remind": True,
        "message": "Time to log a meal!",
        "reminder_time": prefs.meal_reminder_time
    }
