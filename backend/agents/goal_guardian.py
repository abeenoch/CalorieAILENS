from typing import Dict, List, Any

from opik import track

from agents.base import BaseAgent
from config import get_settings

settings = get_settings()


class GoalGuardianAgent(BaseAgent):
    """Ensures all system decisions align with user's goal."""
    
    @property
    def name(self) -> str:
        return "GoalGuardianAgent"
    
    @property
    def system_prompt(self) -> str:
        return """You are a goal protector. Your job is to:
1. Know the user's ACTUAL goal (not assumed)
2. Review every recommendation
3. Ask: "Does this serve the goal?"
4. Redirect if it doesn't
5. Amplify if it does

Be fierce about protecting what matters to them.
Ignore vanity metrics if they don't serve the goal.
Celebrate progress on the actual goal."""
    
    @track(name="goal_guardian", project_name=settings.opik_project_name)
    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Review recommendation for goal alignment.
        
        Args:
            context: {
                "user_goal": str,  # "I want more energy" or "Build consistent habits"
                "goal_specifics": str,  # Details about the goal
                "recommendation": str,  # The suggestion/advice being reviewed
                "recommendation_type": str,  # "action", "insight", "intervention"
                "supporting_data": {...},  # Data backing recommendation
                "user_metrics": {...}  # Current progress on goal
            }
        
        Returns:
            {
                "aligned_with_goal": bool,
                "alignment_score": float (0-1),
                "goal": str,
                "assessment": str,
                "actions_aligned_to_goal": int,  # How many agent outputs align
                "goal_progress": float (0-1),
                "should_modify": bool,
                "modification": str (optional),
                "affirm_goal": str,
                "opik_metadata": {...}
            }
        """
        
        goal = context.get("user_goal", "").lower()
        recommendation = context.get("recommendation", "").lower()
        rec_type = context.get("recommendation_type", "")
        user_metrics = context.get("user_metrics", {})
        
        if not goal:
            return {
                "aligned_with_goal": True,
                "goal_progress": 0.0,
                "message": "No goal set yet. Set a goal to get personalized guidance."
            }
        
        # Assess alignment
        alignment = self._assess_alignment(goal, recommendation, rec_type)
        
        # Check if modification needed
        needs_modification = alignment["score"] < 0.7 and rec_type in ["action", "insight"]
        
        modified_rec = None
        if needs_modification:
            modified_rec = self._modify_recommendation(goal, recommendation, alignment)
        
        # Calculate goal progress
        progress = self._calculate_goal_progress(goal, user_metrics)
        
        # Generate affirmation
        affirmation = self._generate_affirmation(goal, progress)
        
        return {
            "aligned_with_goal": alignment["score"] > 0.7,
            "alignment_score": alignment["score"],
            "goal": goal,
            "assessment": alignment["reasoning"],
            "aligned_keywords": alignment["aligned_keywords"],
            "misaligned_elements": alignment["misaligned"],
            "should_modify": needs_modification,
            "modification": modified_rec,
            "goal_progress": progress,
            "affirm_goal": affirmation,
            "actions_aligned_to_goal": context.get("aligned_action_count", 0),
            "total_actions": context.get("total_action_count", 1),
            "alignment_percentage": int(
                context.get("aligned_action_count", 0) / 
                max(context.get("total_action_count", 1), 1) * 100
            ),
            "opik_metadata": {
                "agent": self.name,
                "decision_type": "goal_alignment",
                "goal": goal.replace(" ", "_"),
                "alignment_score": alignment["score"],
                "goal_progress": progress,
                "modification_needed": needs_modification
            }
        }
    
    def _assess_alignment(
        self,
        goal: str,
        recommendation: str,
        rec_type: str
    ) -> Dict[str, Any]:
        """Assess how well recommendation aligns with goal."""
        
        # Parse goal into keywords
        goal_keywords = self._extract_goal_keywords(goal)
        
        # Check alignment
        aligned_keywords = [
            kw for kw in goal_keywords
            if kw in recommendation
        ]
        
        # Check for misalignment
        misaligned = self._check_misalignment(goal, recommendation)
        
        # Calculate score
        if not goal_keywords:
            score = 0.5
        else:
            score = len(aligned_keywords) / len(goal_keywords)
        
        # Penalize misalignment
        if misaligned:
            score *= 0.7
        
        # Type-specific adjustments
        if rec_type == "action" and score < 0.6:
            score -= 0.1  # Actions should be more aligned
        
        reasoning = self._generate_reasoning(goal, aligned_keywords, misaligned)
        
        return {
            "score": min(1.0, max(0.0, score)),
            "aligned_keywords": aligned_keywords,
            "misaligned": misaligned,
            "reasoning": reasoning
        }
    
    def _extract_goal_keywords(self, goal: str) -> List[str]:
        """Extract key concepts from goal statement."""
        
        # Goal categories
        energy_words = ["energy", "focus", "alert", "awake", "vigor", "vitality"]
        consistency_words = ["consistent", "habit", "routine", "regular", "daily"]
        intuition_words = ["intuitive", "feel", "listen", "trust", "signal"]
        balance_words = ["balance", "moderate", "sustainable", "realistic"]
        wellness_words = ["well", "health", "support", "sustain", "thrive"]
        
        goal_lower = goal.lower()
        keywords = []
        
        if any(w in goal_lower for w in energy_words):
            keywords.extend(energy_words)
        if any(w in goal_lower for w in consistency_words):
            keywords.extend(consistency_words)
        if any(w in goal_lower for w in intuition_words):
            keywords.extend(intuition_words)
        if any(w in goal_lower for w in balance_words):
            keywords.extend(balance_words)
        if any(w in goal_lower for w in wellness_words):
            keywords.extend(wellness_words)
        
        return keywords if keywords else ["wellness", "support"]
    
    def _check_misalignment(self, goal: str, recommendation: str) -> List[str]:
        """Check for things that contradict the goal."""
        
        misaligned = []
        goal_lower = goal.lower()
        rec_lower = recommendation.lower()
        
        # If goal is about intuition, misaligned is rigid calorie tracking
        if "intuitive" in goal_lower:
            if "calories" in rec_lower and "count" in rec_lower:
                misaligned.append("Rigid calorie counting contradicts intuitive eating")
        
        # If goal is about sustainability, misaligned is extremes
        if "sustainable" in goal_lower or "realistic" in goal_lower:
            extremes = ["must", "always", "never", "extreme", "strict", "discipline"]
            if any(e in rec_lower for e in extremes):
                misaligned.append("Extreme advice contradicts sustainable approach")
        
        # If goal is about energy, misaligned is under-fueling
        if "energy" in goal_lower:
            if "restrict" in rec_lower or "fewer" in rec_lower or "cut back" in rec_lower:
                misaligned.append("Restriction contradicts energy goals")
        
        # Universal: No shame language
        shame_words = ["failure", "bad", "undisciplined", "weak", "lazy"]
        if any(w in rec_lower for w in shame_words):
            misaligned.append("Shame-based language contradicts wellness")
        
        return misaligned
    
    def _modify_recommendation(
        self,
        goal: str,
        recommendation: str,
        alignment: Dict
    ) -> str:
        """Modify recommendation to align better with goal."""
        
        goal_lower = goal.lower()
        
        # Example modifications
        if "energy" in goal_lower and "restrict" in recommendation:
            return recommendation.replace(
                "restrict", "consider"
            ) + " while maintaining your energy levels."
        
        if "intuitive" in goal_lower and "calories" in recommendation:
            return "Focus on how you feel after this meal rather than the calorie count."
        
        if "consistent" in goal_lower and "perfect" in recommendation:
            return recommendation.replace("perfect", "consistent")
        
        # Default: Reframe as supportive
        return f"Here's how this supports your goal ({goal}): " + recommendation
    
    def _calculate_goal_progress(
        self,
        goal: str,
        user_metrics: Dict
    ) -> float:
        """Calculate progress toward goal (0-1)."""
        
        progress = 0.5  # Base
        goal_lower = goal.lower()
        
        # Energy goal
        if "energy" in goal_lower:
            energy_avg = user_metrics.get("avg_energy_tag", 0.5)
            progress = energy_avg  # 0-1 from low/medium/high
        
        # Consistency goal
        elif "consistent" in goal_lower or "habit" in goal_lower:
            logging_days = user_metrics.get("days_logged", 0)
            progress = min(logging_days / 7, 1.0)
        
        # Balance goal
        elif "balance" in goal_lower:
            meal_regularity = user_metrics.get("meal_timing_consistency", 0.5)
            progress = meal_regularity
        
        # Intuitive goal
        elif "intuitive" in goal_lower:
            # Progress = comfort with unlogged meals
            unlogged_comfort = user_metrics.get("intuitive_eating_comfort", 0.3)
            progress = min(0.5 + unlogged_comfort, 1.0)
        
        return min(1.0, max(0.0, progress))
    
    def _generate_reasoning(
        self,
        goal: str,
        aligned_keywords: List[str],
        misaligned: List[str]
    ) -> str:
        """Generate explanation of alignment assessment."""
        
        reasoning = f"Checking alignment with goal: '{goal}'\n"
        
        if aligned_keywords:
            reasoning += f"✓ Aligned keywords found: {', '.join(set(aligned_keywords))}\n"
        
        if misaligned:
            reasoning += f"✗ Concerns: {' | '.join(misaligned)}\n"
        
        if not aligned_keywords and not misaligned:
            reasoning += "Neutral on this recommendation — up to you.\n"
        
        return reasoning.strip()
    
    def _generate_affirmation(self, goal: str, progress: float) -> str:
        """Generate affirmation aligned to goal."""
        
        goal_lower = goal.lower()
        
        if progress > 0.8:
            affirmation_base = "You're crushing your goal!"
        elif progress > 0.5:
            affirmation_base = "You're making real progress on your goal."
        else:
            affirmation_base = "You're building toward your goal."
        
        if "energy" in goal_lower:
            return f"{affirmation_base} Keep noticing what fuels your energy. 🔋"
        elif "consistent" in goal_lower:
            return f"{affirmation_base} Consistency builds momentum. Keep going. 💪"
        elif "balance" in goal_lower:
            return f"{affirmation_base} You're finding what works for you. ⚖️"
        elif "intuitive" in goal_lower:
            return f"{affirmation_base} Trust yourself. You've got this. 🧘"
        else:
            return f"{affirmation_base} Your wellness matters. 💚"
