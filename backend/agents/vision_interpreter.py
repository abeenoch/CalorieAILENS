import base64
from typing import Optional
from PIL import Image
from io import BytesIO

from opik import track

from .base import BaseAgent
from config import get_settings

settings = get_settings()


class VisionInterpreterAgent(BaseAgent):
    """
    Agent 1 - Vision Interpreter
    
    Responsibilities:
    - Accepts image (base64) + optional context
    - Detects if image contains a barcode
    - Uses Gemini Vision to identify food items (if not barcode)
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
    
    @staticmethod
    def _detect_barcode(image_bytes: bytes) -> Optional[str]:
        """
        Detect if image contains a barcode and extract it.
        
        Returns:
            Barcode string if detected, None otherwise
        """
        try:
            from pyzbar.pyzbar import decode
            
            # Convert bytes to PIL Image
            image = Image.open(BytesIO(image_bytes))
            
            # Try to decode barcodes
            decoded_objects = decode(image)
            
            if decoded_objects:
                # Return first barcode found
                barcode_data = decoded_objects[0].data.decode("utf-8")
                print(f"Barcode detected: {barcode_data}")
                return barcode_data
            
            return None
        except ImportError:
            print("pyzbar not available - barcode detection disabled. Install with: pip install pyzbar")
            return None
        except Exception as e:
            print(f"Barcode detection error (non-critical): {str(e)}")
            # Don't fail - just continue with regular vision analysis
            return None
    
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
        
        # Try to detect barcode first
        detected_barcode = self._detect_barcode(image_bytes)
        if detected_barcode:
            print(f"Barcode detected in image: {detected_barcode}. Frontend should call /analyze/barcode endpoint.")
            return {
                "foods": [],
                "image_ambiguity": "low",
                "context_applied": context,
                "barcode_detected": detected_barcode,
                "is_barcode_image": True,
                "message": "Barcode detected in image. Processing with barcode endpoint..."
            }
        
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
        
        # DEDUPLICATE FOOD
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
