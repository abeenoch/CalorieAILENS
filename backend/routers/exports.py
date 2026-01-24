import secrets
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from database import get_db
from models import User, Meal, WeeklyExport
from schemas import WeeklyExportResponse
from auth import get_current_user
from agents import MealAnalysisOrchestrator

router = APIRouter(prefix="/exports", tags=["Exports"])

orchestrator = MealAnalysisOrchestrator()


def get_week_bounds(date: datetime = None):
    """Get Monday and Sunday of the week containing the given date."""
    if date is None:
        date = datetime.utcnow()
    
    # Get Monday of this week
    monday = date - timedelta(days=date.weekday())
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Get Sunday of this week
    sunday = monday + timedelta(days=6)
    sunday = sunday.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    return monday, sunday


@router.get("/weekly-summary")
async def get_weekly_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get this week's summary (insights, macros, patterns).
    
    Returns high-level wellness insights without obsessive tracking data.
    """
    monday, sunday = get_week_bounds()
    
    # Get meals for this week
    result = await db.execute(
        select(Meal).where(
            and_(
                Meal.user_id == current_user.id,
                Meal.created_at >= monday,
                Meal.created_at <= sunday
            )
        ).order_by(Meal.created_at)
    )
    meals = result.scalars().all()
    
    # Calculate summary statistics
    total_calories = 0
    total_protein_calories = 0
    total_carbs_calories = 0
    total_fat_calories = 0
    days_with_meals = set()
    
    def extract_percentage(value):
        """Extract percentage from strings like '20-25%'."""
        if not value or value == "N/A":
            return 0
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            value = value.strip()
            if "%" in value:
                try:
                    num_str = value.split("-")[0].replace("%", "").strip()
                    return float(num_str)
                except ValueError:
                    return 0
        return 0
    
    for meal in meals:
        nutrition = meal.nutrition_result or {}
        macros = nutrition.get("macros", {})
        
        # Track days with meals
        days_with_meals.add(meal.created_at.date())
        
        # Parse calorie range
        cal_range = nutrition.get("total_calories", {})
        if cal_range:
            cal_min = cal_range.get("min", 0)
            cal_max = cal_range.get("max", 0)
            meal_calories = (cal_min + cal_max) / 2
            total_calories += meal_calories
            
            # Extract macro percentages
            protein_pct = extract_percentage(macros.get("protein", 0))
            carbs_pct = extract_percentage(macros.get("carbs", 0))
            fat_pct = extract_percentage(macros.get("fat", 0))
            
            # Convert to calories
            total_protein_calories += (protein_pct / 100) * meal_calories
            total_carbs_calories += (carbs_pct / 100) * meal_calories
            total_fat_calories += (fat_pct / 100) * meal_calories
    
    # Convert to grams
    total_protein_g = total_protein_calories / 4 if total_protein_calories > 0 else 0
    total_carbs_g = total_carbs_calories / 4 if total_carbs_calories > 0 else 0
    total_fat_g = total_fat_calories / 9 if total_fat_calories > 0 else 0
    
    # Calculate macro percentages
    macro_calories_total = total_protein_calories + total_carbs_calories + total_fat_calories
    if macro_calories_total > 0:
        protein_pct = round((total_protein_calories / macro_calories_total) * 100, 1)
        carbs_pct = round((total_carbs_calories / macro_calories_total) * 100, 1)
        fat_pct = round((total_fat_calories / macro_calories_total) * 100, 1)
    else:
        protein_pct = carbs_pct = fat_pct = 0
    
    # Collect unique wellness messages for insights
    wellness_messages = []
    seen_messages = set()
    for meal in meals:
        wellness = meal.wellness_result or {}
        if wellness.get("message"):
            msg = wellness["message"]
            if msg not in seen_messages:
                wellness_messages.append(msg)
                seen_messages.add(msg)
    
    # Build summary
    summary_data = {
        "week_start": monday.isoformat(),
        "week_end": sunday.isoformat(),
        "meals_logged": len(meals),
        "days_tracked": len(days_with_meals),
        "total_calories": round(total_calories, 1),
        "macros": {
            "protein_g": round(total_protein_g, 1),
            "carbs_g": round(total_carbs_g, 1),
            "fat_g": round(total_fat_g, 1),
            "protein_pct": protein_pct,
            "carbs_pct": carbs_pct,
            "fat_pct": fat_pct
        },
        "average_calories_per_day": round(total_calories / len(days_with_meals), 1) if days_with_meals else 0,
        "consistency": f"{len(days_with_meals)}/7 days tracked",
        "wellness_highlights": wellness_messages[:3]  # Top 3 unique insights
    }
    
    return summary_data


@router.post("/weekly-summary/share")
async def create_shareable_weekly_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a shareable weekly summary with a public link.
    
    Returns a share token that can be used to view the summary publicly.
    """
    monday, sunday = get_week_bounds()
    
    # Get meals for this week
    result = await db.execute(
        select(Meal).where(
            and_(
                Meal.user_id == current_user.id,
                Meal.created_at >= monday,
                Meal.created_at <= sunday
            )
        ).order_by(Meal.created_at)
    )
    meals = result.scalars().all()
    
    # Calculate summary (same as above)
    total_calories = 0
    total_protein_calories = 0
    total_carbs_calories = 0
    total_fat_calories = 0
    days_with_meals = set()
    
    def extract_percentage(value):
        if not value or value == "N/A":
            return 0
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            value = value.strip()
            if "%" in value:
                try:
                    num_str = value.split("-")[0].replace("%", "").strip()
                    return float(num_str)
                except ValueError:
                    return 0
        return 0
    
    for meal in meals:
        nutrition = meal.nutrition_result or {}
        macros = nutrition.get("macros", {})
        days_with_meals.add(meal.created_at.date())
        
        cal_range = nutrition.get("total_calories", {})
        if cal_range:
            cal_min = cal_range.get("min", 0)
            cal_max = cal_range.get("max", 0)
            meal_calories = (cal_min + cal_max) / 2
            total_calories += meal_calories
            
            protein_pct = extract_percentage(macros.get("protein", 0))
            carbs_pct = extract_percentage(macros.get("carbs", 0))
            fat_pct = extract_percentage(macros.get("fat", 0))
            
            total_protein_calories += (protein_pct / 100) * meal_calories
            total_carbs_calories += (carbs_pct / 100) * meal_calories
            total_fat_calories += (fat_pct / 100) * meal_calories
    
    total_protein_g = total_protein_calories / 4 if total_protein_calories > 0 else 0
    total_carbs_g = total_carbs_calories / 4 if total_carbs_calories > 0 else 0
    total_fat_g = total_fat_calories / 9 if total_fat_calories > 0 else 0
    
    macro_calories_total = total_protein_calories + total_carbs_calories + total_fat_calories
    if macro_calories_total > 0:
        protein_pct = round((total_protein_calories / macro_calories_total) * 100, 1)
        carbs_pct = round((total_carbs_calories / macro_calories_total) * 100, 1)
        fat_pct = round((total_fat_calories / macro_calories_total) * 100, 1)
    else:
        protein_pct = carbs_pct = fat_pct = 0
    
    wellness_messages = []
    seen_messages = set()
    for meal in meals:
        wellness = meal.wellness_result or {}
        if wellness.get("message"):
            msg = wellness["message"]
            if msg not in seen_messages:
                wellness_messages.append(msg)
                seen_messages.add(msg)
    
    summary_data = {
        "week_start": monday.isoformat(),
        "week_end": sunday.isoformat(),
        "meals_logged": len(meals),
        "days_tracked": len(days_with_meals),
        "total_calories": round(total_calories, 1),
        "macros": {
            "protein_g": round(total_protein_g, 1),
            "carbs_g": round(total_carbs_g, 1),
            "fat_g": round(total_fat_g, 1),
            "protein_pct": protein_pct,
            "carbs_pct": carbs_pct,
            "fat_pct": fat_pct
        },
        "average_calories_per_day": round(total_calories / len(days_with_meals), 1) if days_with_meals else 0,
        "consistency": f"{len(days_with_meals)}/7 days tracked",
        "wellness_highlights": wellness_messages[:3]
    }
    
    # Generate share token
    share_token = secrets.token_urlsafe(32)
    
    # Check if export already exists for this week
    result = await db.execute(
        select(WeeklyExport).where(
            and_(
                WeeklyExport.user_id == current_user.id,
                WeeklyExport.week_start == monday,
                WeeklyExport.week_end == sunday
            )
        )
    )
    export = result.scalar_one_or_none()
    
    if export:
        export.summary_data = summary_data
        export.share_token = share_token
        export.is_public = True
    else:
        export = WeeklyExport(
            user_id=current_user.id,
            week_start=monday,
            week_end=sunday,
            summary_data=summary_data,
            share_token=share_token,
            is_public=True
        )
        db.add(export)
    
    await db.commit()
    await db.refresh(export)
    
    return {
        "share_token": share_token,
        "share_url": f"/exports/shared/{share_token}",
        "summary": summary_data
    }


@router.get("/shared/{share_token}", response_class=None)
async def get_shared_summary(
    share_token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a publicly shared weekly summary.
    
    No authentication required - anyone with the token can view.
    Returns JSON data that the frontend can render.
    """
    result = await db.execute(
        select(WeeklyExport).where(
            and_(
                WeeklyExport.share_token == share_token,
                WeeklyExport.is_public == True
            )
        )
    )
    export = result.scalar_one_or_none()
    
    if not export:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shared summary not found"
        )
    
    return {
        "summary": export.summary_data,
        "created_at": export.created_at.isoformat()
    }
