from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User
from schemas import ProfileUpdate, ProfileResponse
from auth import get_current_user
from constants import VALID_AGE_RANGES, VALID_ACTIVITY_LEVELS, VALID_GOALS

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("/", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get the current user's profile.
    """
    return current_user


@router.put("/", response_model=ProfileResponse)
async def update_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update the current user's profile.
    All fields are optional and use ranges for safety.
    """
    # Validate activity level if provided
    if profile_data.activity_level and profile_data.activity_level not in VALID_ACTIVITY_LEVELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid activity level. Must be one of: {VALID_ACTIVITY_LEVELS}"
        )
    
    # Validate goal if provided - allow both predefined and custom goals
    # Only reject if empty string is provided
    if profile_data.goal is not None and profile_data.goal.strip() == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Goal cannot be empty. Either select a predefined goal or enter a custom one."
        )
    
    # Update profile fields
    update_data = profile_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    await db.commit()
    await db.refresh(current_user)
    
    return current_user


@router.get("/options")
async def get_profile_options():
    """
    Get valid options for profile fields.
    Useful for frontend form building.
    """
    return {
        "age_ranges": VALID_AGE_RANGES,
        "height_ranges": [
            "under 150cm", "150-160cm", "160-170cm", 
            "170-180cm", "180-190cm", "over 190cm"
        ],
        "weight_ranges": [
            "under 50kg", "50-60kg", "60-70kg", "70-80kg",
            "80-90kg", "90-100kg", "over 100kg"
        ],
        "activity_levels": [
            {"value": "low", "description": "Sedentary or light activity"},
            {"value": "medium", "description": "Moderate activity (exercise 3-5 days/week)"},
            {"value": "high", "description": "Very active (daily exercise or physical job)"}
        ],
        "goals": [
            {"value": "maintain", "description": "Maintain current energy levels"},
            {"value": "gain_energy", "description": "Increase energy intake"},
            {"value": "reduce_excess", "description": "Reduce excess intake"}
        ]
    }
