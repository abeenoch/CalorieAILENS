from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from database import get_db
from models import User, Meal
from schemas import MealAnalysisRequest, MealAnalysisResponse, MealHistoryItem
from auth import get_current_user
from agents import MealAnalysisOrchestrator

router = APIRouter(prefix="/analyze", tags=["Meal Analysis"])

# Initialize orchestrator 
orchestrator = MealAnalysisOrchestrator()


@router.post("/meal", response_model=MealAnalysisResponse)
async def analyze_meal(
    request: MealAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze a meal photo using the multi-agent system.
    
    This endpoint:
    1. Accepts a base64 encoded image
    2. Runs it through 4 AI agents (Vision, Nutrition, Personalization, Wellness)
    3. Stores the result in the database
    4. Returns comprehensive analysis with supportive feedback
    
    All agent decisions are logged to Opik for observability.
    """
    # Get today's meals for context
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(Meal).where(
            and_(
                Meal.user_id == current_user.id,
                Meal.created_at >= today_start
            )
        ).order_by(Meal.created_at)
    )
    today_meals = result.scalars().all()
    
    # Build daily meals context
    daily_meals_so_far = [
        {
            "nutrition_result": meal.nutrition_result,
            "created_at": meal.created_at.isoformat()
        }
        for meal in today_meals
    ]
    
    # Build user profile dict
    user_profile = {
        "age_range": current_user.age_range,
        "height_range": current_user.height_range,
        "weight_range": current_user.weight_range,
        "activity_level": current_user.activity_level,
        "goal": current_user.goal
    }
    
    # Run multi-agent analysis
    try:
        analysis = await orchestrator.analyze_meal(
            image_base64=request.image_data,
            image_mime_type=request.image_mime_type,
            context=request.context,
            user_profile=user_profile,
            daily_meals_so_far=daily_meals_so_far
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )
    
    # Store meal in database
    new_meal = Meal(
        user_id=current_user.id,
        image_data=request.image_data[:1000] + "..." if len(request.image_data) > 1000 else request.image_data,  # Truncate for storage
        image_mime_type=request.image_mime_type,
        context=request.context,
        notes=request.notes,
        vision_result=analysis.get("vision_result"),
        nutrition_result=analysis.get("nutrition_result"),
        personalization_result=analysis.get("personalization_result"),
        wellness_result=analysis.get("wellness_result"),
        confidence_score=analysis.get("confidence_score"),
        image_ambiguity=analysis.get("vision_result", {}).get("image_ambiguity")
    )
    
    db.add(new_meal)
    await db.commit()
    await db.refresh(new_meal)
    
    # Build response
    return MealAnalysisResponse(
        meal_id=new_meal.id,
        vision={
            "foods": analysis.get("vision_result", {}).get("foods", []),
            "image_ambiguity": analysis.get("vision_result", {}).get("image_ambiguity", "unknown"),
            "context_applied": analysis.get("vision_result", {}).get("context_applied")
        },
        nutrition={
            "total_calories": analysis.get("nutrition_result", {}).get("total_calories", {"min": 0, "max": 0}),
            "macros": analysis.get("nutrition_result", {}).get("macros", {}),
            "uncertainty": analysis.get("nutrition_result", {}).get("uncertainty", "high")
        },
        personalization={
            "balance_status": analysis.get("personalization_result", {}).get("balance_status", "roughly_aligned"),
            "daily_context": analysis.get("personalization_result", {}).get("daily_context", ""),
            "remaining_estimate": analysis.get("personalization_result", {}).get("remaining_estimate")
        },
        wellness={
            "message": analysis.get("wellness_result", {}).get("message", ""),
            "emoji_indicator": analysis.get("wellness_result", {}).get("emoji_indicator", "🟢"),
            "suggestions": analysis.get("wellness_result", {}).get("suggestions", []),
            "disclaimer_shown": True
        },
        confidence_score=analysis.get("confidence_score", "medium"),
        created_at=new_meal.created_at
    )


@router.get("/history", response_model=List[MealHistoryItem])
async def get_meal_history(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the user's meal analysis history.
    """
    result = await db.execute(
        select(Meal)
        .where(Meal.user_id == current_user.id)
        .order_by(Meal.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    meals = result.scalars().all()
    
    return [
        MealHistoryItem(
            id=meal.id,
            context=meal.context,
            vision_result=meal.vision_result,
            nutrition_result=meal.nutrition_result,
            wellness_result=meal.wellness_result,
            confidence_score=meal.confidence_score,
            created_at=meal.created_at
        )
        for meal in meals
    ]


@router.get("/meal/{meal_id}")
async def get_meal_detail(
    meal_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed analysis for a specific meal.
    """
    result = await db.execute(
        select(Meal).where(
            and_(
                Meal.id == meal_id,
                Meal.user_id == current_user.id
            )
        )
    )
    meal = result.scalar_one_or_none()
    
    if not meal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal not found"
        )
    
    return {
        "id": meal.id,
        "context": meal.context,
        "notes": meal.notes,
        "vision_result": meal.vision_result,
        "nutrition_result": meal.nutrition_result,
        "personalization_result": meal.personalization_result,
        "wellness_result": meal.wellness_result,
        "confidence_score": meal.confidence_score,
        "image_ambiguity": meal.image_ambiguity,
        "created_at": meal.created_at
    }
