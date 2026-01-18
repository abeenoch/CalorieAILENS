from typing import Dict, List, Any
from datetime import datetime

from opik import track

from agents.base import BaseAgent
from config import get_settings

settings = get_settings()


class NextActionAgent(BaseAgent):
    """Decides the best next action for the user."""
    
    @property
    def name(self) -> str:
        return "NextActionAgent"
    
    @property
    def system_prompt(self) -> str:
        return """You are a wellness decision-maker. Your job is to:
1. Analyze the current context
2. Identify what the user needs RIGHT NOW
3. Suggest ONE clear action (not multiple options)
4. Be autonomous and confident (but calibrate uncertainty)

Actions should be:
- Specific and actionable
- Aligned with user's goal
- Compassionate and supportive
- Never medical advice

Be direct. Users trust autonomous decisions more than hedging."""
    
    @track(name="next_action_agent", project_name=settings.opik_project_name)
    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decide the next action for the user.
        
        Args:
            context: {
                "current_meal": {...meal data...},
                "user_energy": str ("high", "medium", "low"),
                "recent_drift": {...from DriftDetectionAgent...},
                "user_goal": str,
                "user_profile": {...},
                "time": str (HH:MM),
                "day_of_week": str,
                "recent_meals": [...],
                "goal_progress": float (0-1)
            }
        
        Returns:
            {
                "next_action": str,
                "action_type": str,
                "reasoning": [str],
                "confidence": float,
                "urgency": str ("low", "moderate", "high"),
                "alternative_actions": [str],
                "alignment_with_goal": float (0-1),
                "opik_metadata": {...}
            }
        """
        
        # Extract context
        energy = context.get("user_energy", "medium").lower()
        meal_data = context.get("current_meal", {})
        drift = context.get("recent_drift", {})
        goal = context.get("user_goal", "")
        profile = context.get("user_profile", {})
        recent_meals = context.get("recent_meals", [])
        
        # Decision tree
        decision = self._make_decision(
            energy=energy,
            meal_data=meal_data,
            drift=drift,
            goal=goal,
            profile=profile,
            recent_meals=recent_meals,
            time=context.get("time", "")
        )
        
        # Calculate alignment with goal
        alignment = self._calculate_goal_alignment(decision, goal)
        
        return {
            "next_action": decision["action"],
            "action_type": decision["type"],
            "reasoning": decision["reasoning"],
            "confidence": decision["confidence"],
            "urgency": decision["urgency"],
            "alternative_actions": decision["alternatives"],
            "alignment_with_goal": alignment,
            "decision_tree_path": decision.get("path", []),
            "opik_metadata": {
                "agent": self.name,
                "decision_type": "autonomous_action",
                "energy_level": energy,
                "goal": goal,
                "alternatives_offered": len(decision["alternatives"])
            }
        }
    
    def _make_decision(
        self,
        energy: str,
        meal_data: Dict,
        drift: Dict,
        goal: str,
        profile: Dict,
        recent_meals: List,
        time: str
    ) -> Dict[str, Any]:
        """Multi-step decision tree."""
        
        path = []
        
        # Step 1: Check if under-fueled
        last_meal_hours_ago = self._hours_since_last_meal(recent_meals)
        is_low_energy = energy == "low"
        is_underfueled = last_meal_hours_ago > 5 or (is_low_energy and last_meal_hours_ago > 3)
        
        if is_underfueled:
            path.append("Under-fueled detected")
            return {
                "action": "Have a balanced meal or substantial snack in the next 30 minutes",
                "type": "nutritional_intervention",
                "reasoning": [
                    f"Last meal was {last_meal_hours_ago:.1f} hours ago",
                    f"Energy level is {energy}",
                    "This pattern often leads to energy crashes"
                ],
                "confidence": 0.85,
                "urgency": "high",
                "alternatives": [
                    "Start with hydration and protein snack",
                    "Have a light meal and reassess in 30 min"
                ],
                "path": path
            }
        
        # Step 2: Check if over-stressed
        stress_signals = self._detect_stress_signals(drift, recent_meals, time)
        if stress_signals:
            path.append("Stress signals detected")
            return {
                "action": "Take a break from logging today. Focus on intuitive eating and reset tomorrow",
                "type": "stress_relief",
                "reasoning": [
                    "Stress signals detected:",
                    *stress_signals
                ],
                "confidence": 0.78,
                "urgency": "moderate",
                "alternatives": [
                    "Pause logging, but continue tracking energy",
                    "Take a walk, then reassess your day"
                ],
                "path": path
            }
        
        # Step 3: Check goal progress
        goal_focus = self._determine_goal_focus(goal)
        if goal_focus == "consistency":
            path.append("Goal prioritizes consistency")
            return {
                "action": "Log this meal and note how you feel afterward",
                "type": "consistency_maintenance",
                "reasoning": [
                    "Your goal emphasizes consistency",
                    "Regular logging builds the habit",
                    "Note energy to find patterns"
                ],
                "confidence": 0.82,
                "urgency": "moderate",
                "alternatives": [
                    "Simple logging: just food names",
                    "Detailed logging: include energy + mood"
                ],
                "path": path
            }
        
        # Step 4: All good - normalize
        path.append("No intervention needed")
        return {
            "action": "Continue with your meal. You're on track",
            "type": "normalization",
            "reasoning": [
                "Energy level is stable",
                "Recent meal patterns are healthy",
                "No stress signals detected"
            ],
            "confidence": 0.88,
            "urgency": "low",
            "alternatives": [
                "Log this meal when done",
                "No action needed — enjoy your meal"
            ],
            "path": path
        }
    
    def _hours_since_last_meal(self, recent_meals: List) -> float:
        """Calculate hours since last logged meal."""
        if not recent_meals:
            return 12.0  # Assume normal fasting
        
        # Most recent meal
        try:
            last_meal_time = recent_meals[-1].get("time", "")
            if not last_meal_time:
                return 4.0  # Assume reasonable gap
            
            # Simple calculation: assume current time is "now"
            last_hour = int(last_meal_time.split(":")[0])
            current_hour = datetime.now().hour
            hours_ago = (current_hour - last_hour) % 24
            
            # Adjust for minutes
            return hours_ago if hours_ago > 0 else 24
        except:
            return 4.0
    
    def _detect_stress_signals(self, drift: Dict, recent_meals: List, time: str) -> List[str]:
        """Detect stress from behavioral signals."""
        signals = []
        
        # Signal 1: Drift in logging
        if drift.get("detected") and drift.get("type") == "logging_decline":
            signals.append("You've been logging less frequently")
        
        # Signal 2: Late-night heavy meal (stress eating)
        if recent_meals:
            last_meal = recent_meals[-1]
            try:
                last_time = int(last_meal.get("time", "").split(":")[0])
                if last_time > 21:
                    signals.append("Heavy meal logged late at night")
            except:
                pass
        
        # Signal 3: Energy irregularity
        if drift.get("type") == "energy_irregularity":
            signals.append("Your energy has been erratic recently")
        
        return signals[:2]  # Max 2 signals
    
    def _determine_goal_focus(self, goal: str) -> str:
        """Determine user's primary goal focus."""
        goal_lower = goal.lower() if goal else ""
        
        if any(word in goal_lower for word in ["energy", "focus", "mood", "consistent"]):
            return "consistency"
        elif any(word in goal_lower for word in ["balance", "intuitive", "feel"]):
            return "intuition"
        elif any(word in goal_lower for word in ["weight", "muscle", "lose", "gain"]):
            return "composition"
        else:
            return "consistency"  # Default
    
    def _calculate_goal_alignment(self, decision: Dict, goal: str) -> float:
        """Score how well decision aligns with goal (0-1)."""
        if not goal:
            return 0.7
        
        action = decision.get("action", "").lower()
        goal_lower = goal.lower()
        
        # High alignment cases
        if "energy" in goal_lower and "energy" in action:
            return 0.95
        if "consistent" in goal_lower and "log" in action:
            return 0.90
        if "intuitive" in goal_lower and "reset" in action:
            return 0.92
        
        # Default alignment
        return 0.80
