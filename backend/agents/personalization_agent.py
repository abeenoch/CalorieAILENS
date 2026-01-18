from typing import Optional, Dict

from opik import track

from .base import BaseAgent
from config import get_settings

settings = get_settings()


class PersonalizationAgent(BaseAgent):
    """
    Agent 3 - Personalization Agent
    
    Responsibilities:
    - Takes nutrition data + user profile
    - Adjusts recommendations based on activity level and goal
    - Compares against typical daily needs (ranges)
    - Determines energy balance status
    """
    
    @property
    def name(self) -> str:
        return "personalization_agent"
    
    @property
    def system_prompt(self) -> str:
        return """You are a personalized nutrition advisor. Your task is to contextualize nutrition data based on a user's profile.

IMPORTANT GUIDELINES:
- Consider activity level when estimating daily needs
- Respect the user's goal (maintain, gain energy, reduce excess)
- Use RANGES for all estimates - people vary
- Never give exact calorie targets
- Determine balance status:
  * "under_fueled" - significantly below typical needs
  * "roughly_aligned" - within reasonable range
  * "slightly_over" - somewhat above typical needs
- Be supportive, not judgmental

You must ALWAYS respond with valid JSON in this exact format:
{
    "balance_status": "under_fueled/roughly_aligned/slightly_over",
    "daily_context": "A brief explanation of the assessment based on their profile",
    "remaining_estimate": {
        "min": 800,
        "max": 1200
    },
    "personalization_factors": {
        "activity_adjustment": "description of how activity level affected assessment",
        "goal_alignment": "how well this aligns with their goal"
    }
}

If no profile is provided, use reasonable defaults for a moderately active adult.
Do NOT include any text outside the JSON. Do NOT use markdown code blocks."""
    
    @track(name="personalization_agent", project_name=settings.opik_project_name)
    async def process(
        self,
        nutrition_result: dict,
        user_profile: Optional[dict] = None,
        daily_meals_so_far: Optional[list] = None
    ) -> dict:
        """
        Personalize nutrition assessment based on user profile.
        
        Args:
            nutrition_result: Output from Nutrition Reasoner agent
            user_profile: User's profile data (age_range, weight_range, etc.)
            daily_meals_so_far: List of previous meals today for context
            
        Returns:
            Dictionary with personalized balance assessment
        """
        # Calculate daily totals if we have previous meals
        daily_calories_min = nutrition_result.get("total_calories", {}).get("min", 0)
        daily_calories_max = nutrition_result.get("total_calories", {}).get("max", 0)
        
        if daily_meals_so_far:
            for meal in daily_meals_so_far:
                if meal.get("nutrition_result"):
                    prev_cal = meal["nutrition_result"].get("total_calories", {})
                    daily_calories_min += prev_cal.get("min", 0)
                    daily_calories_max += prev_cal.get("max", 0)
        
        # Build profile context
        profile_context = "No profile provided - using defaults for moderately active adult."
        if user_profile:
            parts = []
            if user_profile.get("age_range"):
                parts.append(f"Age range: {user_profile['age_range']}")
            if user_profile.get("weight_range"):
                parts.append(f"Weight range: {user_profile['weight_range']}")
            if user_profile.get("height_range"):
                parts.append(f"Height range: {user_profile['height_range']}")
            if user_profile.get("activity_level"):
                parts.append(f"Activity level: {user_profile['activity_level']}")
            if user_profile.get("goal"):
                parts.append(f"Goal: {user_profile['goal']}")
            if parts:
                profile_context = "User profile: " + ", ".join(parts)
        
        # Build prompt
        prompt = f"""Analyze this meal in the context of the user's daily energy needs:

Current meal calories: {nutrition_result.get('total_calories', {})}
Today's total so far (including this meal): {daily_calories_min}-{daily_calories_max} calories
Number of meals today: {len(daily_meals_so_far) + 1 if daily_meals_so_far else 1}

{profile_context}

Provide a personalized energy balance assessment. Respond with JSON only."""
        
        # Generate response
        response = await self.generate_text(prompt=prompt)
        
        # Parse and validate response
        result = self.parse_json_response(response)
        
        # Ensure required fields exist
        if "balance_status" not in result:
            result["balance_status"] = "roughly_aligned"
        if "daily_context" not in result:
            result["daily_context"] = "Unable to determine context."
        
        return result
