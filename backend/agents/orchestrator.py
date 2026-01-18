from typing import Optional, Dict, List
from datetime import datetime

from opik import track

from .vision_interpreter import VisionInterpreterAgent
from .nutrition_reasoner import NutritionReasonerAgent
from .personalization_agent import PersonalizationAgent
from .wellness_coach import WellnessCoachAgent
from .drift_detector import DriftDetectionAgent
from .next_action_agent import NextActionAgent
from .strategy_adapter import AdaptiveStrategyAgent
from .energy_intervention import EnergyInterventionAgent
from .weekly_reflection import WeeklyReflectionAgent
from .goal_guardian import GoalGuardianAgent
from config import get_settings
from services.opik_service import OpikMetrics
from utils.confidence import calculate_overall_confidence

settings = get_settings()


class MealAnalysisOrchestrator:
    """
    Main orchestrator that chains all  agents for complete meal analysis.
    
    Flow:
    1. Vision Interpreter → Identify foods and portions
    2. Nutrition Reasoner → Calculate calorie/macro ranges
    3. Personalization Agent → Adjust based on user profile
    4. Wellness Coach → Generate supportive feedback
    
    All steps are logged to Opik for observability.
    """
    
    def __init__(self):
        """Initialize all agents."""
        self.vision_agent = VisionInterpreterAgent()
        self.nutrition_agent = NutritionReasonerAgent()
        self.personalization_agent = PersonalizationAgent()
        self.wellness_agent = WellnessCoachAgent()
        # New agentic agents
        self.drift_detector = DriftDetectionAgent()
        self.next_action_agent = NextActionAgent()
        self.strategy_adapter = AdaptiveStrategyAgent()
        self.energy_intervention = EnergyInterventionAgent()
        self.weekly_reflection = WeeklyReflectionAgent()
        self.goal_guardian = GoalGuardianAgent()
    
    @track(name="meal_analysis_orchestrator", project_name=settings.opik_project_name)
    async def analyze_meal(
        self,
        image_base64: str,
        image_mime_type: str = "image/jpeg",
        context: Optional[str] = None,
        user_profile: Optional[dict] = None,
        daily_meals_so_far: Optional[List[dict]] = None
    ) -> Dict:
        """
        Complete meal analysis pipeline.
        
        Args:
            image_base64: Base64 encoded image data
            image_mime_type: MIME type of the image
            context: Optional context (homemade, restaurant, snack, meal)
            user_profile: User's profile data
            daily_meals_so_far: Previous meals today for daily balance
            
        Returns:
            Complete analysis results from all agents
        """
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "context": context,
            "agents": {}
        }
        
        try:
            # Agent 1: Vision Interpreter
            vision_result = await self.vision_agent.process(
                image_base64=image_base64,
                image_mime_type=image_mime_type,
                context=context
            )
            results["agents"]["vision"] = vision_result
            results["vision_result"] = vision_result
            
            # Log metrics to Opik
            OpikMetrics.log_image_ambiguity(vision_result.get("image_ambiguity", "unknown"))
            
            # Calculate overall confidence from foods
            confidences = [f.get("confidence", "medium") for f in vision_result.get("foods", [])]
            overall_confidence = calculate_overall_confidence(confidences)
            
            results["confidence_score"] = overall_confidence
            OpikMetrics.log_confidence(overall_confidence)
            
        except Exception as e:
            results["agents"]["vision"] = {"error": str(e)}
            results["vision_result"] = {"foods": [], "image_ambiguity": "high", "error": str(e)}
            results["confidence_score"] = "low"
        
        try:
            # Agent 2: Nutrition Reasoner
            nutrition_result = await self.nutrition_agent.process(
                vision_result=results["vision_result"]
            )
            results["agents"]["nutrition"] = nutrition_result
            results["nutrition_result"] = nutrition_result
            
        except Exception as e:
            results["agents"]["nutrition"] = {"error": str(e)}
            results["nutrition_result"] = {
                "total_calories": {"min": 0, "max": 0},
                "macros": {"protein": "N/A", "carbs": "N/A", "fat": "N/A"},
                "uncertainty": "high",
                "error": str(e)
            }
        
        try:
            # Agent 3: Personalization Agent
            personalization_result = await self.personalization_agent.process(
                nutrition_result=results["nutrition_result"],
                user_profile=user_profile,
                daily_meals_so_far=daily_meals_so_far
            )
            results["agents"]["personalization"] = personalization_result
            results["personalization_result"] = personalization_result
            
        except Exception as e:
            results["agents"]["personalization"] = {"error": str(e)}
            results["personalization_result"] = {
                "balance_status": "roughly_aligned",
                "daily_context": "Unable to personalize due to an error.",
                "error": str(e)
            }
        
        try:
            # Agent 4: Wellness Coach
            wellness_result = await self.wellness_agent.process(
                personalization_result=results["personalization_result"],
                nutrition_result=results["nutrition_result"],
                vision_result=results["vision_result"]
            )
            results["agents"]["wellness"] = wellness_result
            results["wellness_result"] = wellness_result
            
        except Exception as e:
            results["agents"]["wellness"] = {"error": str(e)}
            results["wellness_result"] = {
                "message": "Your meal has been logged! Remember to enjoy your food and listen to your body.",
                "emoji_indicator": "🟢",
                "suggestions": [],
                "disclaimer_shown": True,
                "error": str(e)
            }
        
        # NEW AGENTS: Agentic insights
        # CRITICAL: Merge current meal into meals list for downstream agents
        meals_with_current = (daily_meals_so_far or []).copy()
        current_meal_entry = {
            "created_at": datetime.utcnow().isoformat(),
            "nutrition": results["nutrition_result"],
            "vision": results["vision_result"],
            "context": context
        }
        meals_with_current.append(current_meal_entry)
        
        try:
            # Agent 5: Drift Detection
            drift_result = await self.drift_detector.process(
                user_data={
                    "user_id": user_profile.get("id") if user_profile else None,
                    "meals": meals_with_current,
                    "days_tracked": 7,
                    "user_goal": user_profile.get("goal") if user_profile else ""
                }
            )
            results["agents"]["drift_detection"] = drift_result
            
        except Exception as e:
            results["agents"]["drift_detection"] = {"error": str(e), "drift_detected": False}
        
        try:
            # Agent 6: Next Action Decision
            next_action_result = await self.next_action_agent.process(
                context={
                    "current_meal": results["nutrition_result"],
                    "user_energy": user_profile.get("recent_energy", "medium") if user_profile else "medium",
                    "recent_drift": results["agents"].get("drift_detection", {}),
                    "user_goal": user_profile.get("goal", "") if user_profile else "",
                    "user_profile": user_profile or {},
                    "recent_meals": meals_with_current,
                    "time": datetime.utcnow().strftime("%H:%M"),
                    "day_of_week": datetime.utcnow().strftime("%A")
                }
            )
            results["agents"]["next_action"] = next_action_result
            
        except Exception as e:
            results["agents"]["next_action"] = {"error": str(e)}
        
        try:
            # Agent 7: Goal Guardian
            goal_guardian_result = await self.goal_guardian.process(
                context={
                    "user_goal": user_profile.get("goal", "") if user_profile else "",
                    "recommendation": results["wellness_result"].get("message", ""),
                    "recommendation_type": "action",
                    "supporting_data": results["nutrition_result"],
                    "user_metrics": {
                        "avg_energy_tag": 0.6,
                        "days_logged": len(meals_with_current) if meals_with_current else 0
                    }
                }
            )
            results["agents"]["goal_guardian"] = goal_guardian_result
            
        except Exception as e:
            results["agents"]["goal_guardian"] = {"error": str(e)}
        
        try:
            # Agent 8: Strategy Adapter (Adaptive Strategy)
            strategy_result = await self.strategy_adapter.process(
                context={
                    "recent_meals": meals_with_current,
                    "user_goal": user_profile.get("goal", "") if user_profile else "",
                    "current_recommendation": results["wellness_result"].get("message", ""),
                    "user_profile": user_profile or {},
                    "personalization": results["personalization_result"],
                    "engagement_metrics": {
                        "last_7_days_meals": len(meals_with_current) if meals_with_current else 0,
                        "streak_days": 5
                    }
                }
            )
            results["agents"]["strategy_adapter"] = strategy_result
            
        except Exception as e:
            results["agents"]["strategy_adapter"] = {"error": str(e)}
        
        try:
            # Agent 9: Energy Intervention
            energy_result = await self.energy_intervention.process(
                context={
                    "user_energy_level": user_profile.get("recent_energy", "medium") if user_profile else "medium",
                    "current_nutrition": results["nutrition_result"],
                    "wellness_message": results["wellness_result"].get("message", ""),
                    "time_of_day": datetime.utcnow().strftime("%H:%M"),
                    "recent_meals": meals_with_current,
                    "user_profile": user_profile or {}
                }
            )
            results["agents"]["energy_intervention"] = energy_result
            
        except Exception as e:
            results["agents"]["energy_intervention"] = {"error": str(e)}
        
        try:
            # Agent 10: Weekly Reflection
            weekly_result = await self.weekly_reflection.process(
                context={
                    "user_id": user_profile.get("id") if user_profile else None,
                    "recent_meals": meals_with_current,
                    "user_goal": user_profile.get("goal", "") if user_profile else "",
                    "user_profile": user_profile or {},
                    "week_summary": {
                        "meals_logged": len(meals_with_current) if meals_with_current else 0,
                        "average_confidence": "high"
                    }
                }
            )
            results["agents"]["weekly_reflection"] = weekly_result
            
        except Exception as e:
            results["agents"]["weekly_reflection"] = {"error": str(e)}
        
        # Add disclaimer
        results["disclaimer"] = "This app provides general wellness insights, not medical advice."
        
        return results
    
    def get_balance_emoji(self, balance_status: str) -> str:
        """Get emoji for balance status."""
        emoji_map = {
            "under_fueled": "🔵",
            "roughly_aligned": "🟢",
            "slightly_over": "🟠"
        }
        return emoji_map.get(balance_status, "🟢")
