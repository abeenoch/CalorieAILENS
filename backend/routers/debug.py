from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from auth import get_current_user
from models import User
from services.fdc_service import FDCNutritionService

router = APIRouter(prefix="/debug", tags=["Debug"])


@router.get("/fdc-test/{food_name}")
async def test_fdc_lookup(
    food_name: str,
    current_user: User = Depends(get_current_user)
):
    """
    Test USDA FDC nutrition lookup for a food item.
    Returns verified nutrition data if found.
    """
    result = await FDCNutritionService.search_food(food_name)
    
    if not result:
        return {
            "success": False,
            "message": f"No nutrition data found for '{food_name}'",
            "food_name": food_name
        }
    
    return {
        "success": True,
        "food_name": result["food_name"],
        "fdc_id": result["fdc_id"],
        "data_type": result["data_type"],
        "serving_size": result["serving_size"],
        "serving_unit": result["serving_unit"],
        "nutrition": result["nutrition"],
        "source": result["source"]
    }


@router.get("/fdc-cache-stats")
async def get_fdc_cache_stats(
    current_user: User = Depends(get_current_user)
):
    """
    Get statistics about the FDC nutrition cache.
    """
    stats = FDCNutritionService.get_cache_stats()
    return {
        "cache_enabled": True,
        "cache_duration_days": 7,
        "cached_items": stats["cached_items"],
        "cache_size_kb": round(stats["cache_size_kb"], 2),
        "items": stats["items"]
    }


@router.post("/fdc-cache-clear")
async def clear_fdc_cache(
    current_user: User = Depends(get_current_user)
):
    """
    Clear the FDC nutrition cache (admin only).
    """
    FDCNutritionService.clear_cache()
    return {
        "success": True,
        "message": "FDC cache cleared successfully"
    }
