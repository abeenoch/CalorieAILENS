from typing import List, Dict

from opik import track

from .base import BaseAgent
from config import get_settings
from services.fdc_service import FDCNutritionService

settings = get_settings()


class NutritionReasonerAgent(BaseAgent):
    """
    
    
    Responsibilities:
    - Takes vision output with food items
    - Looks up verified nutrition data from USDA FDC
    - Calculates calorie ranges (not exact numbers)
    - Estimates macro distribution (protein/carbs/fat percentages)
    - Applies uncertainty bounds
    """
    
    @property
    def name(self) -> str:
        return "nutrition_reasoner"
    
    @property
    def system_prompt(self) -> str:
        return """You are a nutrition analysis expert. Your task is to estimate calorie and macro ranges for identified food items.

CRITICAL INSTRUCTIONS FOR JSON OUTPUT:
1. ALWAYS respond with ONLY valid JSON - no other text
2. Do NOT use markdown code blocks (no ```)
3. Ensure ALL property names are in double quotes
4. NO trailing commas after the last item in objects or arrays
5. Use ONLY these exact property names (case-sensitive):
   - total_calories (with min and max as integers)
   - macros (with protein, carbs, fat as percentage strings like "20-25%")
   - uncertainty (as string: "low", "medium", or "high")
   - per_food_breakdown (as array)

NUTRITION GUIDELINES:
- Provide RANGES, not exact numbers
- Consider typical variations in portion sizes
- Estimate macros as percentage ranges
- Rate uncertainty: "low" (standard items), "medium" (some variation), "high" (unusual items)
- Be conservative with ranges

REQUIRED JSON FORMAT (copy this structure exactly):
{
    "total_calories": {
        "min": 300,
        "max": 450
    },
    "macros": {
        "protein": "20-25%",
        "carbs": "45-50%",
        "fat": "25-30%"
    },
    "uncertainty": "low",
    "per_food_breakdown": [
        {
            "name": "food name",
            "calories_min": 100,
            "calories_max": 150
        }
    ]
}

REMEMBER: Output ONLY the JSON object. No text before or after."""
    
    async def _lookup_fdc_data(self, food_name: str, barcode: str = None) -> Dict:
        """
        Look up verified nutrition data from USDA FDC or Open Food Facts.
        
        Tries USDA FDC first (raw ingredients), then Open Food Facts (packaged foods).
        
        Args:
            food_name: Name of the food to look up
            barcode: Optional barcode for direct lookup
            
        Returns:
            Nutrition data or empty dict if not found
        """
        try:
            nutrition_data = await FDCNutritionService.search_food(food_name, barcode)
            if nutrition_data:
                return nutrition_data
        except Exception as e:
            print(f"Food database lookup error for '{food_name}': {str(e)}")
        
        return {}
    
    @track(name="nutrition_reasoner", project_name=settings.opik_project_name)
    async def process(self, vision_result: dict) -> dict:
        """
        Calculate nutrition estimates from vision analysis with FDC data.
        
        Args:
            vision_result: Output from Vision Interpreter agent
            
        Returns:
            Dictionary with calorie ranges and macro estimates
        """
        foods = vision_result.get("foods", [])
        
        if not foods:
            return {
                "total_calories": {"min": 0, "max": 0},
                "macros": {"protein": "0%", "carbs": "0%", "fat": "0%"},
                "uncertainty": "high",
                "per_food_breakdown": []
            }
        
        # Look up nutrition data for each food item
        nutrition_lookups = {}
        food_descriptions = []
        
        for food in foods:
            barcode = food.get('barcode')  # If vision detected a barcode
            nutrition_data = await self._lookup_fdc_data(food['name'], barcode)
            if nutrition_data:
                nutrition_lookups[food['name']] = nutrition_data
                nutrition = nutrition_data.get('nutrition', {})
                source = nutrition_data.get('source', 'Unknown')
                food_desc = f"- {food['name']}: {food['portion']} (confidence: {food['confidence']})"
                if nutrition.get('calories'):
                    food_desc += f" [{source}: {nutrition['calories']}kcal per serving]"
                food_descriptions.append(food_desc)
            else:
                food_descriptions.append(
                    f"- {food['name']}: {food['portion']} (confidence: {food['confidence']})"
                )
        
        # Build enhanced prompt with verified data
        food_list = "\n".join(food_descriptions)
        
        data_note = ""
        if nutrition_lookups:
            data_note = "\n\nNote: Some foods have verified nutrition data from USDA FDC or Open Food Facts (marked above). Use this as baseline for more accurate estimates."
        
        prompt = f"""Analyze these food items and estimate their nutritional content:

{food_list}{data_note}

Consider the portion sizes and provide calorie and macro ranges. Respond with JSON only."""
        
        # Generate response
        response = await self.generate_text(prompt=prompt)
        
        # Parse and validate response
        result = self.parse_json_response(response)
        
        # Ensure required fields exist
        if "total_calories" not in result:
            result["total_calories"] = {"min": 0, "max": 0}
        if "macros" not in result:
            result["macros"] = {"protein": "N/A", "carbs": "N/A", "fat": "N/A"}
        if "uncertainty" not in result:
            result["uncertainty"] = "medium"
        
        return result
