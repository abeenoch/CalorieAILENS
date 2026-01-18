from typing import Dict

from opik import track

from .base import BaseAgent
from config import get_settings

settings = get_settings()


class WellnessCoachAgent(BaseAgent):
    """
    Agent 4 - Wellness Coach
    
    Responsibilities:
    - Generates empathetic, non-medical feedback
    - Applies safety rules (no ED triggers, no body shaming)
    - Adds contextual suggestions
    - Formats final user-facing response
    
    Safety Rules Enforced:
    - No eating disorder encouragement
    - No calorie minimums or maximums
    - No body shaming language
    - No medical advice
    - Always includes wellness disclaimer
    """
    
    @property
    def name(self) -> str:
        return "wellness_coach"
    
    @property
    def system_prompt(self) -> str:
        return """You are a supportive wellness coach. Your task is to provide empathetic, helpful feedback about meals.

STRICT SAFETY RULES - YOU MUST FOLLOW THESE:
1. NEVER encourage restrictive eating or eating disorders
2. NEVER provide specific calorie minimums or maximums
3. NEVER use body shaming or guilt-inducing language
4. NEVER give medical or dietary advice (refer to professionals)
5. NEVER criticize food choices as "good" or "bad"
6. ALWAYS be supportive and non-judgmental
7. ALWAYS focus on balance and well-being, not weight

TONE GUIDELINES:
- Warm and encouraging
- Focus on nourishment and energy, not restriction
- Celebrate variety and enjoyment of food
- Suggest balance, not perfection
- If activity is mentioned, keep it positive

EMOJI INDICATORS:
- 🔵 Under-fueled: Gently suggest more nourishment
- 🟢 Roughly aligned: Affirm the balance
- 🟠 Slightly over: Keep it neutral, no judgment

You must ALWAYS respond with valid JSON in this exact format:
{
    "message": "Your main supportive message to the user (2-3 sentences)",
    "emoji_indicator": "🔵/🟢/🟠",
    "suggestions": ["Optional helpful suggestion 1", "Optional suggestion 2"],
    "disclaimer_shown": true
}

Keep suggestions practical and positive. Maximum 2 suggestions.
Do NOT include any text outside the JSON. Do NOT use markdown code blocks."""
    
    SAFETY_PHRASES_TO_AVOID = [
        "too much", "too little", "should cut", "should restrict",
        "bad food", "cheat meal", "guilty", "sinful", "naughty",
        "skinny", "fat", "overweight", "underweight",
        "diet", "lose weight", "burn off", "work off"
    ]
    
    @track(name="wellness_coach", project_name=settings.opik_project_name)
    async def process(
        self,
        personalization_result: dict,
        nutrition_result: dict,
        vision_result: dict
    ) -> dict:
        """
        Generate wellness-focused feedback for the user.
        
        Args:
            personalization_result: Output from Personalization Agent
            nutrition_result: Output from Nutrition Reasoner
            vision_result: Output from Vision Interpreter
            
        Returns:
            Dictionary with user-facing wellness message
        """
        balance_status = personalization_result.get("balance_status", "roughly_aligned")
        daily_context = personalization_result.get("daily_context", "")
        foods = vision_result.get("foods", [])
        
        # Get food names for context
        food_names = [f["name"] for f in foods[:5]]  # Limit to first 5
        
        # Map balance status to emoji
        emoji_map = {
            "under_fueled": "🔵",
            "roughly_aligned": "🟢",
            "slightly_over": "🟠"
        }
        
        prompt = f"""Create a supportive wellness message for this meal analysis:

Foods identified: {', '.join(food_names) if food_names else 'Unable to identify'}
Energy balance status: {balance_status}
Context: {daily_context}

Remember:
- Be warm and supportive
- No judgment about the foods
- Focus on energy and well-being
- Include the appropriate emoji indicator ({emoji_map.get(balance_status, '🟢')})

Respond with JSON only."""
        
        # Generate response
        response = await self.generate_text(prompt=prompt)
        
        # Parse response
        result = self.parse_json_response(response)
        
        # Safety check - scan for problematic phrases
        message = result.get("message", "")
        for phrase in self.SAFETY_PHRASES_TO_AVOID:
            if phrase.lower() in message.lower():
                # Replace with safe alternative
                result["message"] = "Your meal looks balanced! Remember, every meal is an opportunity to nourish yourself. 🌟"
                break
        
        # Ensure required fields
        if "emoji_indicator" not in result:
            result["emoji_indicator"] = emoji_map.get(balance_status, "🟢")
        if "suggestions" not in result:
            result["suggestions"] = []
        if "disclaimer_shown" not in result:
            result["disclaimer_shown"] = True
        
        # Limit suggestions
        result["suggestions"] = result["suggestions"][:2]
        
        return result
