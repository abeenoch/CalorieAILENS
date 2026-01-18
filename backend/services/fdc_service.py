import httpx
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from functools import lru_cache
from config import get_settings

FDC_API_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

# Get settings for API key
settings = get_settings()
FDC_API_KEY = settings.fdc_api_key or "DEMO_KEY"  # Default to demo key for testing

# Cache for nutrition data 
_nutrition_cache: Dict[str, Dict[str, Any]] = {}
_cache_timestamps: Dict[str, datetime] = {}

# 7 days
CACHE_DURATION = timedelta(days=7)


class FDCNutritionService:
    """Service to fetch and cache nutrition data from USDA FDC."""

    @staticmethod
    def _get_cache_key(food_name: str) -> str:
        """Generate cache key for a food item."""
        return food_name.lower().strip()

    @staticmethod
    def _is_cache_valid(cache_key: str) -> bool:
        """Check if cached data is still valid."""
        if cache_key not in _cache_timestamps:
            return False
        age = datetime.now() - _cache_timestamps[cache_key]
        return age < CACHE_DURATION

    @staticmethod
    async def search_food(food_name: str) -> Optional[Dict[str, Any]]:
        """
        Search for a food item in USDA FDC database.
        
        Args:
            food_name: Name of the food to search for
            
        Returns:
            Dictionary with nutrition data or None if not found
        """
        cache_key = FDCNutritionService._get_cache_key(food_name)
        
        # Check cache first
        if cache_key in _nutrition_cache and FDCNutritionService._is_cache_valid(cache_key):
            print(f"FDC: Using cached data for '{food_name}'")
            return _nutrition_cache[cache_key]
        
        try:
            # Search USDA FDC with correct endpoint and API key
            params = {
                "query": food_name,
                "pageSize": 1,  # Get top result only
                "sortBy": "fdcId",  # Sort by food ID (most reliable)
                "sortOrder": "desc",  # Descending order
                "api_key": FDC_API_KEY  # CRITICAL: API key is required!
            }
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(FDC_API_URL, params=params)
                response.raise_for_status()
                
            data = response.json()
            
            if not data.get("foods"):
                print(f"FDC: No results found for '{food_name}'")
                return None
            
            # Process top result
            food = data["foods"][0]
            nutrition_data = FDCNutritionService._extract_nutrition(food)
            
            # Cache the result
            _nutrition_cache[cache_key] = nutrition_data
            _cache_timestamps[cache_key] = datetime.now()
            
            print(f"FDC: Found nutrition data for '{food_name}' ({food.get('dataType', 'Unknown')})")
            return nutrition_data
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                print(f"FDC API error for '{food_name}': Authentication failed - Check your API key")
            elif e.response.status_code == 404:
                print(f"FDC API error for '{food_name}': Not found (404)")
            else:
                print(f"FDC API error for '{food_name}': HTTP {e.response.status_code}")
            return None
        except Exception as e:
            print(f"FDC API error for '{food_name}': {str(e)}")
            return None

    @staticmethod
    def _extract_nutrition(fdc_food: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract relevant nutrition data from FDC response.
        
        Args:
            fdc_food: Food item from FDC API response
            
        Returns:
            Simplified nutrition data
        """
        nutrients = {}
        if "foodNutrients" in fdc_food:
            for nutrient in fdc_food["foodNutrients"]:
                nutrient_name = nutrient.get("nutrientName", "").lower()
                value = nutrient.get("value", 0)
                unit = nutrient.get("unitName", "")
                
                # Map common nutrients
                if "energy" in nutrient_name or "calor" in nutrient_name:
                    # Convert to kcal if needed
                    if "kj" in unit.lower():
                        value = value / 4.184
                    nutrients["calories"] = round(value, 1)
                elif "protein" in nutrient_name:
                    nutrients["protein_g"] = round(value, 1)
                elif "carbohydrate" in nutrient_name:
                    nutrients["carbs_g"] = round(value, 1)
                elif "total lipid" in nutrient_name or "fat" in nutrient_name:
                    nutrients["fat_g"] = round(value, 1)
                elif "fiber" in nutrient_name:
                    nutrients["fiber_g"] = round(value, 1)
                elif "sugar" in nutrient_name:
                    nutrients["sugars_g"] = round(value, 1)
                elif "sodium" in nutrient_name:
                    nutrients["sodium_mg"] = round(value, 1)
        
        return {
            "food_name": fdc_food.get("description", ""),
            "data_type": fdc_food.get("dataType", ""),  # FNDDS, SR-Legacy, etc.
            "fdc_id": fdc_food.get("fdcId"),
            "nutrition": nutrients,
            "serving_size": fdc_food.get("servingSize"),
            "serving_unit": fdc_food.get("servingSizeUnit", ""),
            "source": "USDA FDC"
        }

    @staticmethod
    def get_cache_stats() -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "cached_items": len(_nutrition_cache),
            "cache_size_kb": len(json.dumps(_nutrition_cache)) / 1024,
            "items": list(_nutrition_cache.keys())
        }

    @staticmethod
    def clear_cache() -> None:
        """Clear the nutrition cache."""
        global _nutrition_cache, _cache_timestamps
        _nutrition_cache.clear()
        _cache_timestamps.clear()
        print("FDC nutrition cache cleared")


async def get_fdc_nutrition(food_name: str) -> Optional[Dict[str, Any]]:
    """
    Convenience function to get nutrition data from USDA FDC.
    
    Args:
        food_name: Name of the food item
        
    Returns:
        Nutrition data dictionary or None
    """
    return await FDCNutritionService.search_food(food_name)
