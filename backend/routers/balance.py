from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from database import get_db
from models import User, Meal
from schemas import DailyBalanceResponse
from auth import get_current_user
from agents.weekly_reflection import WeeklyReflectionAgent
from constants import ACTIVITY_MULTIPLIERS, DEFAULT_DAILY_CALORIE_NEED
from utils.emoji import get_balance_emoji

router = APIRouter(prefix="/balance", tags=["Daily Balance"])


@router.get("/today", response_model=DailyBalanceResponse)
async def get_today_balance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get today's energy balance summary.
    
    This aggregates all meals logged today and provides:
    - Total calorie range
    - Overall balance status
    - Reasoning based on user profile
    """
    # Get today's start
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Get today's meals
    result = await db.execute(
        select(Meal).where(
            and_(
                Meal.user_id == current_user.id,
                Meal.created_at >= today_start
            )
        ).order_by(Meal.created_at)
    )
    today_meals = result.scalars().all()
    
    if not today_meals:
        return DailyBalanceResponse(
            date=today_start,
            total_calories_min=0,
            total_calories_max=0,
            balance_status="under_fueled",
            reasoning="No meals logged today yet. Remember to nourish yourself!",
            meals_count=0,
            emoji_indicator="🔵"
        )
    
    # Calculate totals
    total_min = 0
    total_max = 0
    
    for meal in today_meals:
        if meal.nutrition_result:
            cal = meal.nutrition_result.get("total_calories", {})
            total_min += cal.get("min", 0)
            total_max += cal.get("max", 0)
    
    # Determine balance status based on rough estimates
    # These are very rough and just for UI indication
    estimated_daily_need = ACTIVITY_MULTIPLIERS.get(
        current_user.activity_level, DEFAULT_DAILY_CALORIE_NEED
    )
    
    # Calculate average of range
    avg_consumed = (total_min + total_max) / 2
    ratio = avg_consumed / estimated_daily_need if estimated_daily_need > 0 else 0
    
    if ratio < 0.7:
        balance_status = "under_fueled"
        emoji = get_balance_emoji(balance_status)
        reasoning = f"Based on your {current_user.activity_level or 'moderate'} activity level, you may want to consider more nourishment today."
    elif ratio > 1.1:
        balance_status = "slightly_over"
        emoji = get_balance_emoji(balance_status)
        reasoning = f"You've had a good amount of energy intake today. Listen to your body about what feels right."
    else:
        balance_status = "roughly_aligned"
        emoji = get_balance_emoji(balance_status)
        reasoning = f"Your energy intake looks balanced for your {current_user.activity_level or 'moderate'} activity level. Nice work!"
    
    return DailyBalanceResponse(
        date=today_start,
        total_calories_min=total_min,
        total_calories_max=total_max,
        balance_status=balance_status,
        reasoning=reasoning,
        meals_count=len(today_meals),
        emoji_indicator=emoji
    )


@router.get("/week")
async def get_week_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get weekly energy balance summary (stretch feature).
    
    Provides a day-by-day breakdown of the past 7 days.
    """
    week_ago = datetime.utcnow() - timedelta(days=7)
    
    result = await db.execute(
        select(Meal).where(
            and_(
                Meal.user_id == current_user.id,
                Meal.created_at >= week_ago
            )
        ).order_by(Meal.created_at)
    )
    meals = result.scalars().all()
    
    # Group by day
    days = {}
    for meal in meals:
        day_key = meal.created_at.strftime("%Y-%m-%d")
        if day_key not in days:
            days[day_key] = {
                "date": day_key,
                "meals_count": 0,
                "total_calories_min": 0,
                "total_calories_max": 0
            }
        
        days[day_key]["meals_count"] += 1
        if meal.nutrition_result:
            cal = meal.nutrition_result.get("total_calories", {})
            days[day_key]["total_calories_min"] += cal.get("min", 0)
            days[day_key]["total_calories_max"] += cal.get("max", 0)
    
    return {
        "week_start": week_ago.strftime("%Y-%m-%d"),
        "week_end": datetime.utcnow().strftime("%Y-%m-%d"),
        "days": list(days.values()),
        "total_meals": len(meals)
    }


@router.get("/reflection/weekly")
async def get_weekly_reflection(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate weekly reflection with AI-powered insights and personalized focus.
    
    This endpoint:
    1. Analyzes the past 7 days of meal data
    2. Identifies patterns in energy tags and activity
    3. Celebrates wins and consistency
    4. Suggests a gentle focus for next week
    5. May suggest goal adjustments based on patterns
    
    The reflection helps users understand their wellness journey
    and may recommend updating their goal for better alignment.
    """
    week_ago = datetime.utcnow() - timedelta(days=7)
    
    # Get week's meals
    result = await db.execute(
        select(Meal).where(
            and_(
                Meal.user_id == current_user.id,
                Meal.created_at >= week_ago
            )
        ).order_by(Meal.created_at)
    )
    weekly_meals = result.scalars().all()
    
    # Extract data for reflection agent
    meals_data = []
    energy_tags = []
    
    for meal in weekly_meals:
        meal_info = {
            "created_at": meal.created_at.isoformat(),
            "foods": meal.vision_result.get("foods", []) if meal.vision_result else [],
            "calories": meal.nutrition_result.get("total_calories", {}) if meal.nutrition_result else {}
        }
        meals_data.append(meal_info)
        
        # Extract energy tags if wellness result has them
        if meal.wellness_result and isinstance(meal.wellness_result, dict):
            if "energy_indicator" in meal.wellness_result:
                energy_tags.append(meal.wellness_result["energy_indicator"])
    
    # Prepare data for weekly reflection agent
    weekly_data = {
        "user_id": current_user.id,
        "week_start": week_ago.isoformat(),
        "meals_logged": len(weekly_meals),
        "days_active": len(set(m.created_at.strftime("%Y-%m-%d") for m in weekly_meals)),
        "meals": meals_data,
        "energy_tags": energy_tags,
        "goal": current_user.goal or "maintain wellness",
        "activity_level": current_user.activity_level or "medium"
    }
    
    # Run weekly reflection agent
    reflection_agent = WeeklyReflectionAgent()
    reflection = await reflection_agent.process(weekly_data)
    
    return {
        "reflection": reflection,
        "period": {
            "start": week_ago.strftime("%Y-%m-%d"),
            "end": datetime.utcnow().strftime("%Y-%m-%d")
        },
        "stats": {
            "meals_logged": len(weekly_meals),
            "days_active": len(set(m.created_at.strftime("%Y-%m-%d") for m in weekly_meals)),
            "goal_recommendation": reflection.get("goal_recommendation")
        }
    }
