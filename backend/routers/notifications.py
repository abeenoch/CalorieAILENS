from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import User, NotificationPreference, Meal
from schemas import NotificationPreferenceUpdate, NotificationPreferenceResponse
from auth import get_current_user
from agents.wellness_coach import WellnessCoachAgent

router = APIRouter(prefix="/notifications", tags=["Notifications"])

wellness_coach = WellnessCoachAgent()


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
    Check if user should receive a meal reminder with personalized message.
    
    Uses the wellness coach agent to generate an encouraging, personalized message.
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
    
    # Get recent meals for context
    week_ago = datetime.utcnow() - timedelta(days=7)
    result = await db.execute(
        select(Meal).where(
            Meal.user_id == current_user.id,
            Meal.created_at >= week_ago
        ).order_by(Meal.created_at.desc())
    )
    recent_meals = result.scalars().all()
    
    # Generate personalized message using wellness coach agent
    coach_context = {
        "user_id": current_user.id,
        "user_goal": current_user.goal or "general wellness",
        "recent_meals": [
            {
                "foods": meal.foods_identified or [],
                "time": meal.created_at.strftime("%H:%M"),
                "date": meal.created_at.strftime("%Y-%m-%d")
            }
            for meal in recent_meals[:5]
        ],
        "user_profile": {
            "age_range": current_user.age_range,
            "activity_level": current_user.activity_level,
            "goal": current_user.goal
        },
        "context": "meal_reminder",
        "time_of_day": datetime.utcnow().strftime("%H:%M")
    }
    
    # Call wellness coach for personalized message
    coach_result = await wellness_coach.process(coach_context)
    
    reminder_message = coach_result.get("message", "Time to log a meal!")
    
    return {
        "should_remind": True,
        "message": reminder_message,
        "reminder_time": prefs.meal_reminder_time,
        "emoji": coach_result.get("emoji_indicator", "🍽️")
    }
