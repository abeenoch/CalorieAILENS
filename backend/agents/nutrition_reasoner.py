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

IMPORTANT GUIDELINES:
- Provide RANGES, not exact numbers - nutrition varies by preparation
- Consider typical variations in portion sizes
- Estimate macros as percentage ranges
- Rate uncertainty: "low" (standard items, clear portions), "medium" (some variation expected), "high" (unusual items or unclear portions)
- Be conservative - it's better to have wider ranges than false precision
- Use verified nutrition data when provided (marked as FDC data)

You must ALWAYS respond with valid JSON in this exact format:
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
    "uncertainty": "low/medium/high",
    "per_food_breakdown": [
        {
            "name": "food name",
            "calories_min": 100,
            "calories_max": 150
        }
    ]
}

Do NOT include any text outside the JSON. Do NOT use markdown code blocks."""
    
    async def _lookup_fdc_data(self, food_name: str) -> Dict:
        """
        Look up verified nutrition data from USDA FDC.
        
        Args:
            food_name: Name of the food to look up
            
        Returns:
            FDC nutrition data or empty dict if not found
        """
        try:
            fdc_data = await FDCNutritionService.search_food(food_name)
            if fdc_data:
                return fdc_data
        except Exception as e:
            print(f"FDC lookup error for '{food_name}': {str(e)}")
        
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
        
        # Look up FDC data for each food item
        fdc_lookups = {}
        food_descriptions = []
        
        for food in foods:
            fdc_data = await self._lookup_fdc_data(food['name'])
            if fdc_data:
                fdc_lookups[food['name']] = fdc_data
                nutrition = fdc_data.get('nutrition', {})
                food_desc = f"- {food['name']}: {food['portion']} (confidence: {food['confidence']})"
                if nutrition.get('calories'):
                    food_desc += f" [FDC verified: {nutrition['calories']}kcal per serving]"
                food_descriptions.append(food_desc)
            else:
                food_descriptions.append(
                    f"- {food['name']}: {food['portion']} (confidence: {food['confidence']})"
                )
        
        # Build enhanced prompt with FDC data
        food_list = "\n".join(food_descriptions)
        
        fdc_note = ""
        if fdc_lookups:
            fdc_note = "\n\nNote: Some foods have verified nutrition data from USDA FDC (marked above). Use this as baseline for more accurate estimates."
        
        prompt = f"""Analyze these food items and estimate their nutritional content:

{food_list}{fdc_note}

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
