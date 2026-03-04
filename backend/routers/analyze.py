from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from database import get_db
from models import User, Meal
from schemas import MealAnalysisRequest, MealAnalysisResponse, MealHistoryItem, BarcodeScanRequest
from auth import get_current_user
from agents import MealAnalysisOrchestrator
from services.fdc_service import FDCNutritionService
from config import get_settings

router = APIRouter(prefix="/analyze", tags=["Meal Analysis"])
settings = get_settings()

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
    if len(request.image_data) > settings.max_image_bytes * 2:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image payload too large. Please upload a smaller image."
        )

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
            "created_at": meal.created_at.isoformat(),
            "time": meal.created_at.strftime("%H:%M"),
            "date": meal.created_at.strftime("%Y-%m-%d"),
            "calories_estimate": (
                (
                    (meal.nutrition_result or {}).get("total_calories", {}).get("min", 0) +
                    (meal.nutrition_result or {}).get("total_calories", {}).get("max", 0)
                ) / 2
            )
        }
        for meal in today_meals
    ]
    
    # Get historical meals (last 30 days) for drift detection
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    result = await db.execute(
        select(Meal).where(
            and_(
                Meal.user_id == current_user.id,
                Meal.created_at >= thirty_days_ago
            )
        ).order_by(Meal.created_at)
    )
    historical_meals = result.scalars().all()
    
    # Build historical meals for drift detector
    historical_meals_data = [
        {
            "nutrition_result": meal.nutrition_result,
            "vision_result": meal.vision_result,
            "created_at": meal.created_at.isoformat(),
            "context": meal.context,
            "time": meal.created_at.strftime("%H:%M"),
            "date": meal.created_at.strftime("%Y-%m-%d"),
            "calories_estimate": (
                (
                    (meal.nutrition_result or {}).get("total_calories", {}).get("min", 0) +
                    (meal.nutrition_result or {}).get("total_calories", {}).get("max", 0)
                ) / 2
            )
        }
        for meal in historical_meals
    ]
    
    # Build user profile dict
    user_profile = {
        "id": current_user.id,
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
            daily_meals_so_far=daily_meals_so_far,
            historical_meals=historical_meals_data
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Analysis failed. Please try again."
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
        agent_results=analysis.get("agents"),
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
            "context_applied": analysis.get("vision_result", {}).get("context_applied"),
            "barcode_detected": analysis.get("vision_result", {}).get("barcode_detected")
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
        agents=analysis.get("agents"),
        confidence_score=analysis.get("confidence_score", "medium"),
        created_at=new_meal.created_at
    )


@router.post("/barcode", response_model=MealAnalysisResponse)
async def scan_barcode(
    request: BarcodeScanRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Barcode scan with full agent analysis.
    
    This endpoint:
    1. Accepts a barcode (EAN/UPC)
    2. Looks up product in Open Food Facts
    3. Runs through full agent pipeline (personalization, wellness coaching, etc.)
    4. Stores result in database
    5. Returns comprehensive analysis
    
    This ensures packaged foods get the same personalized treatment as photo analysis.
    """
    barcode = request.barcode
    context = request.context
    notes = request.notes

    try:
        # Look up product by barcode
        nutrition_data = await FDCNutritionService._search_open_food_facts_by_barcode(barcode)
        
        if not nutrition_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with barcode {barcode} not found in Open Food Facts database. Try a different product or upload a food photo instead."
            )
        
        # Check if nutrition data is empty
        nutrition = nutrition_data.get("nutrition", {})
        # Continue even if nutrition is sparse; users can still log the product.
        
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
                "created_at": meal.created_at.isoformat(),
                "time": meal.created_at.strftime("%H:%M"),
                "date": meal.created_at.strftime("%Y-%m-%d"),
                "calories_estimate": (
                    (
                        (meal.nutrition_result or {}).get("total_calories", {}).get("min", 0) +
                        (meal.nutrition_result or {}).get("total_calories", {}).get("max", 0)
                    ) / 2
                )
            }
            for meal in today_meals
        ]
        
        # Get historical meals (last 30 days) for drift detection
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        result = await db.execute(
            select(Meal).where(
                and_(
                    Meal.user_id == current_user.id,
                    Meal.created_at >= thirty_days_ago
                )
            ).order_by(Meal.created_at)
        )
        historical_meals = result.scalars().all()
        
        # Build historical meals for drift detector
        historical_meals_data = [
            {
                "nutrition_result": meal.nutrition_result,
                "vision_result": meal.vision_result,
                "created_at": meal.created_at.isoformat(),
                "context": meal.context,
                "time": meal.created_at.strftime("%H:%M"),
                "date": meal.created_at.strftime("%Y-%m-%d"),
                "calories_estimate": (
                    (
                        (meal.nutrition_result or {}).get("total_calories", {}).get("min", 0) +
                        (meal.nutrition_result or {}).get("total_calories", {}).get("max", 0)
                    ) / 2
                )
            }
            for meal in historical_meals
        ]
        
        # Build user profile dict
        user_profile = {
            "id": current_user.id,
            "age_range": current_user.age_range,
            "height_range": current_user.height_range,
            "weight_range": current_user.weight_range,
            "activity_level": current_user.activity_level,
            "goal": current_user.goal
        }
        
        # Create synthetic vision result from barcode data
        vision_result = {
            "foods": [
                {
                    "name": nutrition_data.get("food_name", "Unknown product"),
                    "portion": f"1 serving ({nutrition_data.get('serving_size', 100)}{nutrition_data.get('serving_unit', 'g')})",
                    "confidence": "high",
                    "barcode": barcode,
                    "source": "barcode_scan"
                }
            ],
            "image_ambiguity": "low",
            "context_applied": context or "packaged_food",
            "barcode_source": nutrition_data.get("source", "Open Food Facts")
        }
        
        # Create nutrition result from barcode data
        calories = nutrition.get("calories", 0)
        protein = nutrition.get("protein_g", 0)
        carbs = nutrition.get("carbs_g", 0)
        fat = nutrition.get("fat_g", 0)
        
        nutrition_result = {
            "total_calories": {
                "min": calories,
                "max": calories
            },
            "macros": {
                "protein": f"{protein:.0f}g" if protein else "N/A",
                "carbs": f"{carbs:.0f}g" if carbs else "N/A",
                "fat": f"{fat:.0f}g" if fat else "N/A"
            },
            "uncertainty": "low" if calories > 0 else "medium",
            "per_food_breakdown": [
                {
                    "name": nutrition_data.get("food_name", "Unknown product"),
                    "calories_min": calories,
                    "calories_max": calories
                }
            ],
            "source": "barcode_verified"
        }
        
        # Run full orchestrator with precomputed barcode outputs.
        analysis = await orchestrator.analyze_meal(
            image_base64="",  # unused when precomputed vision+nutrition are provided
            image_mime_type="barcode",
            context=context or "packaged_food",
            user_profile=user_profile,
            daily_meals_so_far=daily_meals_so_far,
            historical_meals=historical_meals_data,
            precomputed_vision_result=vision_result,
            precomputed_nutrition_result=nutrition_result
        )

        personalization_result = analysis.get("personalization_result", {})
        wellness_result = analysis.get("wellness_result", {})

        # Store meal in database
        new_meal = Meal(
            user_id=current_user.id,
            image_data=f"barcode:{barcode}",
            image_mime_type="barcode",
            context=context or "packaged_food",
            notes=notes or f"Barcode: {barcode} - {nutrition_data.get('food_name')}",
            vision_result=analysis.get("vision_result", vision_result),
            nutrition_result=analysis.get("nutrition_result", nutrition_result),
            personalization_result=personalization_result,
            wellness_result=wellness_result,
            agent_results=analysis.get("agents"),
            confidence_score=analysis.get("confidence_score", "high"),
            image_ambiguity=analysis.get("vision_result", {}).get("image_ambiguity", "low")
        )
        
        db.add(new_meal)
        await db.commit()
        await db.refresh(new_meal)
        
        # Build response
        return MealAnalysisResponse(
            meal_id=new_meal.id,
            vision={
                "foods": analysis.get("vision_result", {}).get("foods", []),
                "image_ambiguity": analysis.get("vision_result", {}).get("image_ambiguity", "low"),
                "context_applied": analysis.get("vision_result", {}).get("context_applied", context or "packaged_food")
            },
            nutrition={
                "total_calories": analysis.get("nutrition_result", {}).get("total_calories", {"min": 0, "max": 0}),
                "macros": analysis.get("nutrition_result", {}).get("macros", {}),
                "uncertainty": analysis.get("nutrition_result", {}).get("uncertainty", "medium")
            },
            personalization={
                "balance_status": personalization_result.get("balance_status", "roughly_aligned"),
                "daily_context": personalization_result.get("daily_context", ""),
                "remaining_estimate": personalization_result.get("remaining_estimate")
            },
            wellness={
                "message": wellness_result.get("message", ""),
                "emoji_indicator": wellness_result.get("emoji_indicator", "🟢"),
                "suggestions": wellness_result.get("suggestions", []),
                "disclaimer_shown": True
            },
            agents=analysis.get("agents"),
            confidence_score=analysis.get("confidence_score", "high"),
            created_at=new_meal.created_at
        )
        
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Barcode analysis failed. Please try again."
        )


@router.get("/history", response_model=List[MealHistoryItem])
async def get_meal_history(
    limit: int = 20,
    offset: int = 0,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    context: Optional[str] = None,
    food_name: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the user's meal analysis history with optional filtering.
    
    Query Parameters:
    - limit: Number of results (default: 20)
    - offset: Pagination offset (default: 0)
    - start_date: Filter by start date (ISO format: YYYY-MM-DD)
    - end_date: Filter by end date (ISO format: YYYY-MM-DD)
    - context: Filter by meal context (homemade, restaurant, snack, meal)
    - food_name: Search by food name (partial match, case-insensitive)
    """
    if limit < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="limit must be >= 1")
    if offset < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="offset must be >= 0")
    limit = min(limit, settings.max_history_limit)

    query = select(Meal).where(Meal.user_id == current_user.id)
    
    # Date range filtering
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date).replace(hour=0, minute=0, second=0, microsecond=0)
            query = query.where(Meal.created_at >= start_dt)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_date format. Use YYYY-MM-DD"
            )
    
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59, microsecond=999999)
            query = query.where(Meal.created_at <= end_dt)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_date format. Use YYYY-MM-DD"
            )
    
    # Context filtering
    if context:
        query = query.where(Meal.context == context)
    
    # Food name search (searches in vision_result foods)
    if food_name:
        # This is a simple text search in the notes field
        # For more advanced search, consider using full-text search
        query = query.where(
            (Meal.notes.ilike(f"%{food_name}%")) |
            (Meal.vision_result.astext.ilike(f"%{food_name}%"))
        )
    
    # Execute query with ordering and pagination
    result = await db.execute(
        query.order_by(Meal.created_at.desc())
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
            agent_results=meal.agent_results,
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
        "agent_results": meal.agent_results,
        "confidence_score": meal.confidence_score,
        "image_ambiguity": meal.image_ambiguity,
        "created_at": meal.created_at
    }


@router.get("/macros/today")
async def get_today_macros(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get aggregated macros for today (for pie chart visualization).
    
    Returns:
    - total_calories: Total calories consumed
    - protein_g: Total protein in grams
    - carbs_g: Total carbs in grams
    - fat_g: Total fat in grams
    - macro_percentages: Percentage breakdown for pie chart
    - meals_count: Number of meals logged today
    """
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = datetime.utcnow().replace(hour=23, minute=59, second=59, microsecond=999999)
    
    result = await db.execute(
        select(Meal).where(
            and_(
                Meal.user_id == current_user.id,
                Meal.created_at >= today_start,
                Meal.created_at <= today_end
            )
        ).order_by(Meal.created_at)
    )
    meals = result.scalars().all()
    
    # Aggregate macros
    total_calories = 0
    total_protein_calories = 0
    total_carbs_calories = 0
    total_fat_calories = 0
    
    def extract_percentage(value):
        """Extract percentage from strings like '20-25%' or '20%'."""
        if not value or value == "N/A":
            return 0
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            value = value.strip()
            # Extract first number from percentage range (e.g., "20-25%" -> 20)
            if "%" in value:
                try:
                    # Get the first number before the dash or %
                    num_str = value.split("-")[0].replace("%", "").strip()
                    return float(num_str)
                except ValueError:
                    return 0
        return 0
    
    for meal in meals:
        nutrition = meal.nutrition_result or {}
        macros = nutrition.get("macros", {})
        
        # Parse calorie range (use midpoint)
        cal_range = nutrition.get("total_calories", {})
        if cal_range:
            cal_min = cal_range.get("min", 0)
            cal_max = cal_range.get("max", 0)
            meal_calories = (cal_min + cal_max) / 2
            total_calories += meal_calories
            
            # Extract macro percentages and convert to calories
            protein_pct = extract_percentage(macros.get("protein", 0))
            carbs_pct = extract_percentage(macros.get("carbs", 0))
            fat_pct = extract_percentage(macros.get("fat", 0))
            
            # Convert percentages to calories
            total_protein_calories += (protein_pct / 100) * meal_calories
            total_carbs_calories += (carbs_pct / 100) * meal_calories
            total_fat_calories += (fat_pct / 100) * meal_calories
    
    # Convert calories back to grams
    # Protein: 4 cal/g, Carbs: 4 cal/g, Fat: 9 cal/g
    total_protein_g = total_protein_calories / 4 if total_protein_calories > 0 else 0
    total_carbs_g = total_carbs_calories / 4 if total_carbs_calories > 0 else 0
    total_fat_g = total_fat_calories / 9 if total_fat_calories > 0 else 0
    
    # Calculate macro percentages
    macro_calories_total = total_protein_calories + total_carbs_calories + total_fat_calories
    
    if macro_calories_total > 0:
        protein_percentage = round((total_protein_calories / macro_calories_total) * 100, 1)
        carbs_percentage = round((total_carbs_calories / macro_calories_total) * 100, 1)
        fat_percentage = round((total_fat_calories / macro_calories_total) * 100, 1)
    else:
        protein_percentage = carbs_percentage = fat_percentage = 0
    
    return {
        "total_calories": round(total_calories, 1),
        "protein_g": round(total_protein_g, 1),
        "carbs_g": round(total_carbs_g, 1),
        "fat_g": round(total_fat_g, 1),
        "macro_percentages": {
            "protein": protein_percentage,
            "carbs": carbs_percentage,
            "fat": fat_percentage
        },
        "meals_count": len(meals)
    }


@router.get("/macros/date-range")
async def get_macros_by_date_range(
    start_date: str,
    end_date: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get aggregated macros for a date range (for pie chart visualization).
    
    Query Parameters:
    - start_date: Start date (ISO format: YYYY-MM-DD)
    - end_date: End date (ISO format: YYYY-MM-DD)
    
    Returns:
    - total_calories: Total calories consumed
    - protein_g: Total protein in grams
    - carbs_g: Total carbs in grams
    - fat_g: Total fat in grams
    - macro_percentages: Percentage breakdown for pie chart
    - meals_count: Number of meals logged
    - days_count: Number of days in range
    """
    try:
        start_dt = datetime.fromisoformat(start_date).replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59, microsecond=999999)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD"
        )
    
    result = await db.execute(
        select(Meal).where(
            and_(
                Meal.user_id == current_user.id,
                Meal.created_at >= start_dt,
                Meal.created_at <= end_dt
            )
        ).order_by(Meal.created_at)
    )
    meals = result.scalars().all()
    
    # Aggregate macros
    total_calories = 0
    total_protein_calories = 0
    total_carbs_calories = 0
    total_fat_calories = 0
    
    def extract_percentage(value):
        """Extract percentage from strings like '20-25%' or '20%'."""
        if not value or value == "N/A":
            return 0
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            value = value.strip()
            # Extract first number from percentage range (e.g., "20-25%" -> 20)
            if "%" in value:
                try:
                    # Get the first number before the dash or %
                    num_str = value.split("-")[0].replace("%", "").strip()
                    return float(num_str)
                except ValueError:
                    return 0
        return 0
    
    for meal in meals:
        nutrition = meal.nutrition_result or {}
        macros = nutrition.get("macros", {})
        
        # Parse calorie range (use midpoint)
        cal_range = nutrition.get("total_calories", {})
        if cal_range:
            cal_min = cal_range.get("min", 0)
            cal_max = cal_range.get("max", 0)
            meal_calories = (cal_min + cal_max) / 2
            total_calories += meal_calories
            
            # Extract macro percentages and convert to calories
            protein_pct = extract_percentage(macros.get("protein", 0))
            carbs_pct = extract_percentage(macros.get("carbs", 0))
            fat_pct = extract_percentage(macros.get("fat", 0))
            
            # Convert percentages to calories
            total_protein_calories += (protein_pct / 100) * meal_calories
            total_carbs_calories += (carbs_pct / 100) * meal_calories
            total_fat_calories += (fat_pct / 100) * meal_calories
    
    # Convert calories back to grams
    # Protein: 4 cal/g, Carbs: 4 cal/g, Fat: 9 cal/g
    total_protein_g = total_protein_calories / 4 if total_protein_calories > 0 else 0
    total_carbs_g = total_carbs_calories / 4 if total_carbs_calories > 0 else 0
    total_fat_g = total_fat_calories / 9 if total_fat_calories > 0 else 0
    
    # Calculate macro percentages
    macro_calories_total = total_protein_calories + total_carbs_calories + total_fat_calories
    
    if macro_calories_total > 0:
        protein_percentage = round((total_protein_calories / macro_calories_total) * 100, 1)
        carbs_percentage = round((total_carbs_calories / macro_calories_total) * 100, 1)
        fat_percentage = round((total_fat_calories / macro_calories_total) * 100, 1)
    else:
        protein_percentage = carbs_percentage = fat_percentage = 0
    
    # Calculate days in range
    days_count = (end_dt - start_dt).days + 1
    
    return {
        "total_calories": round(total_calories, 1),
        "protein_g": round(total_protein_g, 1),
        "carbs_g": round(total_carbs_g, 1),
        "fat_g": round(total_fat_g, 1),
        "macro_percentages": {
            "protein": protein_percentage,
            "carbs": carbs_percentage,
            "fat": fat_percentage
        },
        "meals_count": len(meals),
        "days_count": days_count,
        "average_calories_per_day": round(total_calories / days_count, 1) if days_count > 0 else 0
    }
