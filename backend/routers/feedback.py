from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from database import get_db
from models import User, Meal, Feedback
from schemas import FeedbackCreate, FeedbackResponse
from auth import get_current_user
from services.opik_service import OpikMetrics
from constants import VALID_FEEDBACK_TYPES

router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.post("/", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def create_feedback(
    feedback_data: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit feedback for a meal analysis.
    
    This allows users to indicate if the analysis was accurate
    or if portions were estimated incorrectly.
    
    Feedback is logged to Opik for model improvement tracking.
    """
    # Validate feedback type
    if feedback_data.feedback_type not in VALID_FEEDBACK_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid feedback type. Must be one of: {VALID_FEEDBACK_TYPES}"
        )
    
    # Verify meal exists and belongs to user
    result = await db.execute(
        select(Meal).where(
            and_(
                Meal.id == feedback_data.meal_id,
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
    
    # Create feedback
    new_feedback = Feedback(
        meal_id=feedback_data.meal_id,
        feedback_type=feedback_data.feedback_type,
        comment=feedback_data.comment
    )
    
    db.add(new_feedback)
    await db.commit()
    await db.refresh(new_feedback)
    
    # Log to Opik for observability
    OpikMetrics.log_user_correction(feedback_data.feedback_type, feedback_data.meal_id)
    
    return new_feedback


@router.get("/meal/{meal_id}", response_model=List[FeedbackResponse])
async def get_meal_feedback(
    meal_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all feedback for a specific meal.
    """
    # Verify meal belongs to user
    meal_result = await db.execute(
        select(Meal).where(
            and_(
                Meal.id == meal_id,
                Meal.user_id == current_user.id
            )
        )
    )
    meal = meal_result.scalar_one_or_none()
    
    if not meal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal not found"
        )
    
    # Get feedback
    result = await db.execute(
        select(Feedback)
        .where(Feedback.meal_id == meal_id)
        .order_by(Feedback.created_at.desc())
    )
    feedbacks = result.scalars().all()
    
    return feedbacks


@router.get("/stats")
async def get_feedback_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get feedback statistics for the current user.
    
    This shows:
    - Total feedback submissions
    - Breakdown by feedback type
    - Accuracy rate (how often "accurate" is selected)
    
    Useful for demonstrating model behavior monitoring to hackathon judges.
    """
    # Get user's meal IDs
    meal_result = await db.execute(
        select(Meal.id).where(Meal.user_id == current_user.id)
    )
    meal_ids = [row[0] for row in meal_result.fetchall()]
    
    if not meal_ids:
        return {
            "total_feedback": 0,
            "by_type": {},
            "accuracy_rate": None,
            "message": "No meals or feedback found"
        }
    
    # Count feedback by type
    result = await db.execute(
        select(Feedback.feedback_type, func.count(Feedback.id))
        .where(Feedback.meal_id.in_(meal_ids))
        .group_by(Feedback.feedback_type)
    )
    counts = dict(result.fetchall())
    
    total = sum(counts.values())
    accurate_count = counts.get("accurate", 0)
    accuracy_rate = (accurate_count / total * 100) if total > 0 else None
    
    return {
        "total_feedback": total,
        "by_type": counts,
        "accuracy_rate": round(accuracy_rate, 1) if accuracy_rate else None,
        "message": "Feedback data for Opik observability demonstration"
    }
