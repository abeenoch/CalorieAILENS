from typing import Dict, List, Any
from datetime import datetime, timedelta

from opik import track

from agents.base import BaseAgent
from config import get_settings

settings = get_settings()


class AdaptiveStrategyAgent(BaseAgent):
    """Adapts system strategy based on user behavior and acceptance."""
    
    @property
    def name(self) -> str:
        return "AdaptiveStrategyAgent"
    
    @property
    def system_prompt(self) -> str:
        return """You are a strategic optimizer. Your job is to:
1. Measure whether current strategies are working
2. Identify when adaptation is needed
3. Make strategic switches autonomously
4. Justify each decision with data

Think at the meta-level: which approach helps this specific user thrive?
Be willing to change. Rigidity is failure."""
    
    @track(name="strategy_adapter", project_name=settings.opik_project_name)
    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze metrics and decide on strategy changes.
        
        Args:
            context: {
                "current_strategy": str,
                "acceptance_rate": float (0-1),
                "engagement_trend": float (-1 to 1),
                "logging_frequency": float,
                "intervention_success_rate": float,
                "user_goal": str,
                "days_with_strategy": int,
                "prior_strategies": [str],
                "user_feedback_sentiment": float (-1 to 1),
                "recent_meals": [dict],
                "user_profile": dict,
                "personalization": dict,
                "engagement_metrics": dict
            }
        
        Returns:
            {
                "strategy_switch": bool,
                "old_strategy": str,
                "new_strategy": str,
                "trigger": str,
                "trigger_metric": str,
                "trigger_value": float,
                "threshold": float,
                "confidence": float,
                "expected_impact": str,
                "adaptation_reasoning": [str],
                "experiment_id": str,
                "opik_metadata": {...}
            }
        """
        
        current_strategy = context.get("current_strategy", "calorie_focused")
        acceptance = context.get("acceptance_rate", 0.5)
        engagement = context.get("engagement_trend", 0.0)
        logging_freq = context.get("logging_frequency", 1.5)
        intervention_success = context.get("intervention_success_rate", 0.6)
        goal = context.get("user_goal", "")
        days_with_strategy = context.get("days_with_strategy", 3)
        
        # Need minimum data before switching
        if days_with_strategy < 2:
            return {
                "strategy_switch": False,
                "reason": "Insufficient data for adaptation decision",
                "data_required": 2,
                "days_tracked": days_with_strategy
            }
        
        # Evaluate current strategy
        evaluation = self._evaluate_strategy(
            strategy=current_strategy,
            acceptance=acceptance,
            engagement=engagement,
            logging_freq=logging_freq,
            intervention_success=intervention_success
        )
        
        # Decide on switch
        if not evaluation["should_switch"]:
            return {
                "strategy_switch": False,
                "current_strategy": current_strategy,
                "reason": evaluation["reason"],
                "metrics": {
                    "acceptance_rate": acceptance,
                    "engagement_trend": engagement,
                    "intervention_success": intervention_success
                },
                "recommendation": "Continue monitoring"
            }
        
        # Recommend new strategy
        new_strategy = self._recommend_strategy(
            old_strategy=current_strategy,
            trigger=evaluation["trigger"],
            goal=goal
        )
        
        return {
            "strategy_switch": True,
            "old_strategy": current_strategy,
            "new_strategy": new_strategy,
            "trigger": evaluation["trigger"],
            "trigger_metric": evaluation["metric"],
            "trigger_value": evaluation["value"],
            "threshold": evaluation["threshold"],
            "confidence": evaluation["confidence"],
            "expected_impact": self._predict_impact(new_strategy),
            "adaptation_reasoning": evaluation["reasoning"],
            "experiment_id": f"strategy_switch_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "opik_metadata": {
                "agent": self.name,
                "decision_type": "strategy_adaptation",
                "old_strategy": current_strategy,
                "new_strategy": new_strategy,
                "trigger_metric": evaluation["metric"],
                "days_on_strategy": days_with_strategy
            }
        }
    
    def _evaluate_strategy(
        self,
        strategy: str,
        acceptance: float,
        engagement: float,
        logging_freq: float,
        intervention_success: float
    ) -> Dict[str, Any]:
        """Evaluate if current strategy needs adaptation."""
        
        reasons = []
        should_switch = False
        trigger = None
        metric = None
        value = None
        threshold = None
        confidence = 0.0
        
        # Check 1: Low acceptance rate
        if acceptance < 0.4:
            should_switch = True
            trigger = "Low user acceptance of suggestions"
            metric = "acceptance_rate"
            value = acceptance
            threshold = 0.4
            confidence = 0.85
            reasons.append(f"Users only accept {acceptance:.0%} of suggestions")
            reasons.append("Strategy likely too aggressive or misaligned")
        
        # Check 2: Declining engagement
        elif engagement < -0.2:
            should_switch = True
            trigger = "Disengagement trend detected"
            metric = "engagement_trend"
            value = engagement
            threshold = -0.2
            confidence = 0.78
            reasons.append("User engagement trending downward")
            reasons.append("Current strategy may be causing overwhelm")
        
        # Check 3: Logging frequency collapse
        elif logging_freq < 1.0:
            should_switch = True
            trigger = "Logging burden causing disengagement"
            metric = "logging_frequency"
            value = logging_freq
            threshold = 1.0
            confidence = 0.82
            reasons.append(f"Logging only {logging_freq:.1f} meals per day")
            reasons.append("Reduce detail to rebuild habit")
        
        # Check 4: Low intervention success
        elif intervention_success < 0.35:
            should_switch = True
            trigger = "Interventions not working for this user"
            metric = "intervention_success_rate"
            value = intervention_success
            threshold = 0.35
            confidence = 0.75
            reasons.append(f"Interventions only succeed {intervention_success:.0%}")
            reasons.append("Different approach needed")
        
        else:
            reasons.append("Current strategy performing adequately")
            reasons.append(f"Acceptance: {acceptance:.0%}, Engagement: {engagement:+.0%}")
        
        return {
            "should_switch": should_switch,
            "reason": reasons[0] if reasons else "No switch needed",
            "trigger": trigger,
            "metric": metric,
            "value": value,
            "threshold": threshold,
            "confidence": confidence,
            "reasoning": reasons
        }
    
    def _recommend_strategy(
        self,
        old_strategy: str,
        trigger: str,
        goal: str
    ) -> str:
        """Recommend new strategy based on trigger."""
        
        goal_lower = goal.lower() if goal else ""
        
        # Trigger: Low acceptance
        if "acceptance" in trigger and "calorie" in old_strategy:
            if "energy" in goal_lower or "mood" in goal_lower:
                return "meal_timing_focused"
            elif "intuitive" in goal_lower:
                return "intuitive_eating_focused"
            else:
                return "meal_regularity_focused"
        
        # Trigger: Disengagement
        elif "disengagement" in trigger:
            return "minimal_tracking"  # Simplify
        
        # Trigger: Logging burden
        elif "logging" in trigger:
            return "trend_only_summaries"  # Less frequent updates
        
        # Trigger: Intervention failure
        elif "interventions" in trigger:
            if "consistency" in goal_lower:
                return "habit_stacking"  # Tie to existing habits
            else:
                return "goal_aligned_tracking"
        
        # Default
        return "adaptive_balanced"
    
    def _predict_impact(self, new_strategy: str) -> str:
        """Predict impact of new strategy."""
        
        impacts = {
            "meal_timing_focused": "Focus on consistent meal timing rather than calories. Expected: Higher acceptance, better energy patterns.",
            "intuitive_eating_focused": "Trust body signals. Log less, feel more. Expected: Higher engagement, reduced anxiety.",
            "minimal_tracking": "Simplify logging to essentials only. Expected: Rebuild habit, reduce overwhelm.",
            "trend_only_summaries": "Weekly summaries instead of daily detail. Expected: Lower friction, maintained insights.",
            "habit_stacking": "Tie healthy eating to existing habits. Expected: Higher intervention success, easier adoption.",
            "goal_aligned_tracking": "Every log aligned to stated goal. Expected: Higher perceived relevance, better acceptance.",
            "adaptive_balanced": "Continue with current balanced approach. Expected: Steady improvement."
        }
        
        return impacts.get(new_strategy, "Strategy adapted for better alignment with your needs.")
    
    def get_strategy_summary(self, current_strategy: str) -> Dict[str, Any]:
        """Get info about a strategy."""
        
        strategies = {
            "calorie_focused": {
                "description": "Track calories, macros, and totals",
                "best_for": "Goals requiring precision (body composition)",
                "engagement_risk": "High detail can overwhelm some users",
                "switch_triggers": ["Low acceptance", "Declining engagement"]
            },
            "meal_timing_focused": {
                "description": "Emphasize consistent meal timing over quantities",
                "best_for": "Energy consistency, habit building",
                "engagement_risk": "Low - aligns with intuition",
                "switch_triggers": ["Low energy tracking"]
            },
            "intuitive_eating_focused": {
                "description": "Trust body signals, minimal tracking",
                "best_for": "Mindfulness and intuitive eating goals",
                "engagement_risk": "Very low",
                "switch_triggers": ["Need more structure"]
            },
            "minimal_tracking": {
                "description": "Log only meal names, minimal detail",
                "best_for": "Rebuilding habit after overwhelm",
                "engagement_risk": "Very low - reduced friction",
                "switch_triggers": ["Ready to increase detail"]
            },
            "trend_only_summaries": {
                "description": "Weekly patterns, not daily granularity",
                "best_for": "High-level consistency tracking",
                "engagement_risk": "Low",
                "switch_triggers": ["Need more frequent feedback"]
            }
        }
        
        return strategies.get(current_strategy, {})
