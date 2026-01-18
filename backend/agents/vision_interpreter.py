import base64
from typing import Optional

from opik import track

from .base import BaseAgent
from config import get_settings

settings = get_settings()


class VisionInterpreterAgent(BaseAgent):
    """
    Agent 1 - Vision Interpreter
    
    Responsibilities:
    - Accepts image (base64) + optional context
    - Uses Gemini Vision to identify food items
    - Estimates rough portion sizes
    - Outputs structured JSON with confidence scores
    """
    
    @property
    def name(self) -> str:
        return "vision_interpreter"
    
    @property
    def system_prompt(self) -> str:
        return """You are a food vision analysis expert. Your task is to identify food items in images and estimate portion sizes.

IMPORTANT GUIDELINES:
- Identify all visible food items
- Estimate portions as rough ranges (small, medium, large) with approximate grams
- Be honest about uncertainty - if something is unclear, say so
- Consider the context provided (homemade, restaurant, snack, meal)
- Rate your confidence: "high" (clear image, common foods), "medium" (some uncertainty), "low" (unclear or unusual items)
- Rate image ambiguity: "low" (clear), "medium" (partially obscured), "high" (unclear/blurry)

You must ALWAYS respond with valid JSON in this exact format:
{
    "foods": [
        {
            "name": "food item name",
            "portion": "size description (e.g., 'medium (150-200g)')",
            "confidence": "high/medium/low"
        }
    ],
    "image_ambiguity": "low/medium/high",
    "context_applied": "the context if provided, or null"
}

Do NOT include any text outside the JSON. Do NOT use markdown code blocks."""
    
    @track(name="vision_interpreter", project_name=settings.opik_project_name)
    async def process(
        self,
        image_base64: str,
        image_mime_type: str = "image/jpeg",
        context: Optional[str] = None
    ) -> dict:
        """
        Analyze food image and identify items with portions.
        
        Args:
            image_base64: Base64 encoded image data
            image_mime_type: MIME type of the image
            context: Optional context (homemade, restaurant, snack, meal)
            
        Returns:
            Dictionary with identified foods and metadata
        """
        # Decode base64 image
        try:
            image_bytes = base64.b64decode(image_base64)
        except Exception as e:
            raise Exception(f"Invalid base64 image data: {str(e)}")
        
        # Build prompt
        prompt = "Analyze this food image and identify all food items with estimated portions."
        if context:
            prompt += f"\n\nContext: This is a {context} meal/food."
        prompt += "\n\nRespond with JSON only, following the exact schema specified."
        
        # Generate response
        response = await self.generate_text(
            prompt=prompt,
            image_data=image_bytes,
            image_mime_type=image_mime_type
        )
        
        # Parse and validate response
        result = self.parse_json_response(response)
        
        # Ensure required fields exist
        if "foods" not in result:
            result["foods"] = []
        if "image_ambiguity" not in result:
            result["image_ambiguity"] = "medium"
        if "context_applied" not in result:
            result["context_applied"] = context
        
        # DEDUPLICATE FOODS: Remove exact duplicates while preserving order
        seen_foods = set()
        unique_foods = []
        
        for food in result["foods"]:
            # Create a normalized key for comparison (case-insensitive, trimmed)
            food_key = f"{food.get('name', '').lower().strip()}|{food.get('portion', '').lower().strip()}"
            
            if food_key not in seen_foods:
                seen_foods.add(food_key)
                unique_foods.append(food)
        
        result["foods"] = unique_foods
        
        return result
