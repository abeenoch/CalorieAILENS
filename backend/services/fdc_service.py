import httpx
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from functools import lru_cache
from config import get_settings

FDC_API_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
OPEN_FOOD_FACTS_API_URL = "https://world.openfoodfacts.org/api/v3"

# Get settings for API key
settings = get_settings()
FDC_API_KEY = settings.fdc_api_key or "DEMO_KEY"  # Default to demo key for testing

# Cache for nutrition data 
_nutrition_cache: Dict[str, Dict[str, Any]] = {}
_cache_timestamps: Dict[str, datetime] = {}

# 7 days
CACHE_DURATION = timedelta(days=7)


class FDCNutritionService:
    """Service to fetch and cache nutrition data from USDA FDC and Open Food Facts with fallback."""

    @staticmethod
    def _get_cache_key(food_name: str, source: str = "") -> str:
        """Generate cache key for a food item."""
        key = food_name.lower().strip()
        if source:
            key = f"{key}_{source}"
        return key

    @staticmethod
    def _is_cache_valid(cache_key: str) -> bool:
        """Check if cached data is still valid."""
        if cache_key not in _cache_timestamps:
            return False
        age = datetime.now() - _cache_timestamps[cache_key]
        return age < CACHE_DURATION

    @staticmethod
    async def search_food(food_name: str, barcode: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Search for a food item with fallback chain: USDA FDC -> Open Food Facts.
        
        Args:
            food_name: Name of the food to search for
            barcode: Optional barcode (EAN/UPC) for direct lookup
            
        Returns:
            Dictionary with nutrition data or None if not found
        """
        # Try barcode lookup first if provided
        if barcode:
            result = await FDCNutritionService._search_open_food_facts_by_barcode(barcode)
            if result:
                return result
        
        # Try USDA FDC first (raw ingredients, verified data)
        result = await FDCNutritionService._search_fdc(food_name)
        if result:
            return result
        
        # Fallback to Open Food Facts (packaged foods, barcodes)
        result = await FDCNutritionService._search_open_food_facts(food_name)
        if result:
            return result
        
        print(f"Food database: No results found for '{food_name}'")
        return None

    @staticmethod
    async def _search_fdc(food_name: str) -> Optional[Dict[str, Any]]:
        """Search USDA FDC database."""
        cache_key = FDCNutritionService._get_cache_key(food_name, "fdc")
        
        # Check cache first
        if cache_key in _nutrition_cache and FDCNutritionService._is_cache_valid(cache_key):
            print(f"FDC: Using cached data for '{food_name}'")
            return _nutrition_cache[cache_key]
        
        try:
            params = {
                "query": food_name,
                "pageSize": 1,
                "sortBy": "fdcId",
                "sortOrder": "desc",
                "api_key": FDC_API_KEY
            }
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(FDC_API_URL, params=params)
                response.raise_for_status()
                
            data = response.json()
            
            if not data.get("foods"):
                print(f"FDC: No results found for '{food_name}'")
                return None
            
            food = data["foods"][0]
            nutrition_data = FDCNutritionService._extract_nutrition_fdc(food)
            
            # Cache the result
            _nutrition_cache[cache_key] = nutrition_data
            _cache_timestamps[cache_key] = datetime.now()
            
            print(f"FDC: Found nutrition data for '{food_name}'")
            return nutrition_data
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                print(f"FDC API error for '{food_name}': Authentication failed")
            else:
                print(f"FDC API error for '{food_name}': HTTP {e.response.status_code}")
            return None
        except Exception as e:
            print(f"FDC API error for '{food_name}': {str(e)}")
            return None

    @staticmethod
    async def _search_open_food_facts(food_name: str) -> Optional[Dict[str, Any]]:
        """Search Open Food Facts database (packaged foods)."""
        cache_key = FDCNutritionService._get_cache_key(food_name, "off")
        
        # Check cache first
        if cache_key in _nutrition_cache and FDCNutritionService._is_cache_valid(cache_key):
            print(f"Open Food Facts: Using cached data for '{food_name}'")
            return _nutrition_cache[cache_key]
        
        try:
            params = {
                "q": food_name,
                "fields": "product_name,code,nutriments,brands,categories",
                "limit": 1
            }
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{OPEN_FOOD_FACTS_API_URL}/search", params=params)
                response.raise_for_status()
                
            data = response.json()
            
            if not data.get("products"):
                print(f"Open Food Facts: No results found for '{food_name}'")
                return None
            
            product = data["products"][0]
            nutrition_data = FDCNutritionService._extract_nutrition_off(product)
            
            # Cache the result
            _nutrition_cache[cache_key] = nutrition_data
            _cache_timestamps[cache_key] = datetime.now()
            
            print(f"Open Food Facts: Found nutrition data for '{food_name}'")
            return nutrition_data
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                print(f"Open Food Facts: Bad request for '{food_name}' (likely regional/niche food)")
            else:
                print(f"Open Food Facts API error for '{food_name}': HTTP {e.response.status_code}")
            return None
        except Exception as e:
            print(f"Open Food Facts API error for '{food_name}': {str(e)}")
            return None

    @staticmethod
    async def _search_open_food_facts_by_barcode(barcode: str) -> Optional[Dict[str, Any]]:
        """Search Open Food Facts by barcode (EAN/UPC)."""
        cache_key = FDCNutritionService._get_cache_key(barcode, "off_barcode")
        
        # Check cache first
        if cache_key in _nutrition_cache and FDCNutritionService._is_cache_valid(cache_key):
            print(f"Open Food Facts: Using cached barcode data for '{barcode}'")
            return _nutrition_cache[cache_key]
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{OPEN_FOOD_FACTS_API_URL}/product/{barcode}")
                response.raise_for_status()
                
            data = response.json()
            
            if data.get("status") != 1 or not data.get("product"):
                print(f"Open Food Facts: Barcode {barcode} not found")
                return None
            
            product = data["product"]
            nutrition_data = FDCNutritionService._extract_nutrition_off(product)
            
            # Cache the result
            _nutrition_cache[cache_key] = nutrition_data
            _cache_timestamps[cache_key] = datetime.now()
            
            print(f"Open Food Facts: Found product for barcode {barcode}")
            return nutrition_data
            
        except Exception as e:
            print(f"Open Food Facts barcode lookup error for '{barcode}': {str(e)}")
            return None

    @staticmethod
    def _extract_nutrition_fdc(fdc_food: Dict[str, Any]) -> Dict[str, Any]:
        """Extract nutrition data from USDA FDC response."""
        nutrients = {}
        if "foodNutrients" in fdc_food:
            for nutrient in fdc_food["foodNutrients"]:
                nutrient_name = nutrient.get("nutrientName", "").lower()
                value = nutrient.get("value", 0)
                unit = nutrient.get("unitName", "")
                
                if "energy" in nutrient_name or "calor" in nutrient_name:
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
            "data_type": fdc_food.get("dataType", ""),
            "fdc_id": fdc_food.get("fdcId"),
            "nutrition": nutrients,
            "serving_size": fdc_food.get("servingSize"),
            "serving_unit": fdc_food.get("servingSizeUnit", ""),
            "source": "USDA FDC"
        }

    @staticmethod
    def _extract_nutrition_off(product: Dict[str, Any]) -> Dict[str, Any]:
        """Extract nutrition data from Open Food Facts response."""
        nutrients = {}
        nutriments = product.get("nutriments", {})
        
        # Open Food Facts uses standardized keys
        if "energy-kcal_100g" in nutriments:
            nutrients["calories"] = round(nutriments["energy-kcal_100g"], 1)
        elif "energy_100g" in nutriments:
            # Convert kJ to kcal
            nutrients["calories"] = round(nutriments["energy_100g"] / 4.184, 1)
        
        if "proteins_100g" in nutriments:
            nutrients["protein_g"] = round(nutriments["proteins_100g"], 1)
        
        if "carbohydrates_100g" in nutriments:
            nutrients["carbs_g"] = round(nutriments["carbohydrates_100g"], 1)
        
        if "fat_100g" in nutriments:
            nutrients["fat_g"] = round(nutriments["fat_100g"], 1)
        
        if "fiber_100g" in nutriments:
            nutrients["fiber_g"] = round(nutriments["fiber_100g"], 1)
        
        if "sugars_100g" in nutriments:
            nutrients["sugars_g"] = round(nutriments["sugars_100g"], 1)
        
        if "sodium_100g" in nutriments:
            nutrients["sodium_mg"] = round(nutriments["sodium_100g"] * 1000, 1)
        
        return {
            "food_name": product.get("product_name", ""),
            "barcode": product.get("code"),
            "brands": product.get("brands", ""),
            "nutrition": nutrients,
            "serving_size": 100,
            "serving_unit": "g",
            "source": "Open Food Facts"
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


async def get_fdc_nutrition(food_name: str, barcode: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Convenience function to get nutrition data with fallback chain.
    
    Tries USDA FDC first (raw ingredients), then Open Food Facts (packaged foods).
    
    Args:
        food_name: Name of the food item
        barcode: Optional barcode for direct lookup
        
    Returns:
        Nutrition data dictionary or None
    """
    return await FDCNutritionService.search_food(food_name, barcode)
