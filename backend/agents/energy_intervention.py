from typing import Dict, List, Any

from opik import track

from agents.base import BaseAgent
from config import get_settings

settings = get_settings()


class EnergyInterventionAgent(BaseAgent):
    """Detects stress signals and offers compassionate interventions."""
    
    @property
    def name(self) -> str:
        return "EnergyInterventionAgent"
    
    @property
    def system_prompt(self) -> str:
        return """You are a compassionate wellness companion. Your job is to:
1. Detect behavioral signals of stress (not diagnose)
2. Offer gentle, supportive interventions
3. NEVER provide medical advice
4. Acknowledge overwhelm without judgment
5. Suggest ONE kind action

Be warm. Be human. Show you care.
Always include: "No medical advice - just support from your wellness companion."
"""
    
    @track(name="energy_intervention", project_name=settings.opik_project_name)
    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze for stress signals and suggest intervention.
        
        Args:
            context: {
                "user_energy_level": str,
                "current_nutrition": dict,
                "wellness_message": str,
                "time_of_day": str,
                "recent_meals": list,
                "user_profile": dict
            }
        
        Returns:
            {
                "stress_detected": bool,
                "stress_level": float (0-1),
                "indicators": [str],
                "intervention_type": str,
                "suggested_action": str,
                "tone_check": str,
                "medical_disclaimer": bool,
                "follow_up": str,
                "compassion_score": float,
                "opik_metadata": {...}
            }
        """
        
        # Detect stress signals
        signals = self._detect_stress_signals(context)
        
        if not signals["detected"]:
            return {
                "stress_detected": False,
                "stress_level": 0.0,
                "message": "You're doing well. Keep it up!"
            }
        
        # Generate intervention
        intervention = self._generate_intervention(
            stress_level=signals["level"],
            indicators=signals["indicators"],
            user_goal=user_data.get("user_goal", "")
        )
        
        # Check tone
        tone = self._check_tone(intervention["message"])
        
        return {
            "stress_detected": True,
            "stress_level": signals["level"],
            "indicators": signals["indicators"],
            "intervention_type": intervention["type"],
            "suggested_action": intervention["action"],
            "suggested_message": intervention["message"],
            "tone_check": tone,
            "tone_score": tone.get("compassion_score", 0.8),
            "medical_disclaimer": True,
            "follow_up": "Optional. No pressure. Just checking in.",
            "compassion_score": self._calculate_compassion_score(intervention),
            "safety_flags": self._check_safety_flags(intervention),
            "opik_metadata": {
                "agent": self.name,
                "signal_type": "stress_detection",
                "stress_level": signals["level"],
                "indicator_count": len(signals["indicators"]),
                "tone_verified": tone.get("compassionate", False)
            }
        }
    
    def _detect_stress_signals(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect behavioral stress signals."""
        
        indicators = []
        signal_strength = 0.0
        
        # Signal 1: Low energy tags
        energy_tags = user_data.get("energy_tags", [])
        if energy_tags:
            low_energy_pct = energy_tags.count("low") / len(energy_tags)
            if low_energy_pct > 0.5:
                indicators.append(f"Low energy tagged {low_energy_pct:.0%} of meals")
                signal_strength += 0.3
        
        # Signal 2: Meal timing irregularity
        recent_meals = user_data.get("recent_meals", [])
        if len(recent_meals) > 3:
            timing_variance = self._calculate_timing_variance(recent_meals)
            if timing_variance > 3.5:  # High variance
                indicators.append(f"Meal timing varies significantly ({timing_variance:.1f} hours std dev)")
                signal_strength += 0.25
        
        # Signal 3: Under-fueling pattern
        under_fueled_count = sum(
            1 for m in recent_meals 
            if m.get("calories_estimate", 500) < 400
        )
        if under_fueled_count > len(recent_meals) * 0.4:
            indicators.append("Several light meals in a row")
            signal_strength += 0.20
        
        # Signal 4: Late-night heavy intake
        late_meals = [
            m for m in recent_meals 
            if self._is_late_meal(m.get("time", ""))
        ]
        if late_meals:
            heavy_late = sum(
                1 for m in late_meals
                if m.get("calories_estimate", 300) > 600
            )
            if heavy_late > 0:
                indicators.append("Heavy meals late at night")
                signal_strength += 0.15
        
        # Signal 5: Logging gaps
        logging_gaps = user_data.get("logging_gaps", 0)
        if logging_gaps > 2:
            indicators.append(f"Haven't logged in {logging_gaps} days")
            signal_strength += 0.20
        
        # Cap stress level
        signal_strength = min(signal_strength, 1.0)
        
        return {
            "detected": len(indicators) > 0,
            "level": signal_strength,
            "indicators": indicators,
            "indicator_count": len(indicators)
        }
    
    def _generate_intervention(
        self,
        stress_level: float,
        indicators: List[str],
        user_goal: str
    ) -> Dict[str, str]:
        """Generate compassionate intervention."""
        
        if stress_level < 0.3:
            action = "Take a breath. You're doing your best."
            intervention_type = "gentle_reassurance"
        elif stress_level < 0.6:
            action = "Want to simplify your approach for a few days?"
            intervention_type = "mild_support"
        else:
            action = "You seem overwhelmed. Want to reset tomorrow with something simpler?"
            intervention_type = "significant_support"
        
        # Build message
        message = f"""I've noticed a few things:
{self._format_indicators(indicators)}

This doesn't mean anything is wrong. Sometimes life gets busy, energy fluctuates, or we need a break from tracking.

{action}

Remember: This is about *your* wellness, not perfection.
No judgment. Just support.

[Important: This is general wellness support, not medical advice. If you're concerned about your health, please consult a doctor.]"""
        
        return {
            "type": intervention_type,
            "action": action,
            "message": message
        }
    
    def _format_indicators(self, indicators: List[str]) -> str:
        """Format indicators as bullet points."""
        return "\n".join([f"• {ind}" for ind in indicators[:3]])  # Top 3 only
    
    def _check_tone(self, message: str) -> Dict[str, Any]:
        """Verify tone is compassionate, not judgmental."""
        
        harmful_words = [
            "bad", "failure", "wrong", "lazy", "undisciplined",
            "sick", "disease", "disorder", "dangerous", "urgent"
        ]
        
        message_lower = message.lower()
        harmful_found = [w for w in harmful_words if w in message_lower]
        
        compassionate_words = [
            "understand", "support", "care", "gentle", "rest",
            "break", "reset", "okay", "notice", "observed"
        ]
        
        compassionate_found = [w for w in compassionate_words if w in message_lower]
        
        compassion_score = len(compassionate_found) / (len(harmful_found) + len(compassionate_found) + 1)
        
        return {
            "compassionate": len(harmful_found) == 0 and len(compassionate_found) > 2,
            "compassion_score": compassion_score,
            "harmful_words_detected": harmful_found,
            "supportive_words_found": compassionate_found
        }
    
    def _calculate_compassion_score(self, intervention: Dict) -> float:
        """Calculate overall compassion score (0-1)."""
        
        message = intervention.get("message", "")
        
        # Check for key elements
        has_validation = any(w in message.lower() for w in ["understand", "noticed", "observed"])
        has_options = any(w in message.lower() for w in ["want", "would", "option"])
        has_no_judgment = "judgment" in message.lower() or "not wrong" in message.lower()
        has_disclaimer = "not medical" in message.lower() or "consult" in message.lower()
        
        score = 0.0
        score += 0.25 if has_validation else 0
        score += 0.25 if has_options else 0
        score += 0.25 if has_no_judgment else 0
        score += 0.25 if has_disclaimer else 0
        
        return score
    
    def _check_safety_flags(self, intervention: Dict) -> List[str]:
        """Check for safety/policy violations."""
        
        flags = []
        message = intervention.get("message", "").lower()
        
        # Check for medical overreach
        if any(w in message for w in ["diagnose", "treat", "cure", "disease"]):
            flags.append("Medical overreach detected")
        
        # Check for shame language
        if any(w in message for w in ["should", "must", "need to", "obligated"]):
            flags.append("Potential shame language")
        
        # Check for certainty where there shouldn't be
        if "100%" in message or "definitely" in message:
            flags.append("Over-confident language")
        
        # Check for eating disorder triggers
        if any(w in message for w in ["restrict", "calories", "limit", "cut back"]):
            flags.append("Potential ED trigger")
        
        return flags
    
    @staticmethod
    def _calculate_timing_variance(meals: List[Dict]) -> float:
        """Calculate variance in meal timing."""
        if len(meals) < 2:
            return 0.0
        
        times = []
        for m in meals:
            try:
                time_str = m.get("time", "12:00")
                hour = int(time_str.split(":")[0])
                times.append(hour)
            except:
                pass
        
        if len(times) < 2:
            return 0.0
        
        mean = sum(times) / len(times)
        variance = sum((t - mean) ** 2 for t in times) / len(times)
        return variance ** 0.5  # Standard deviation
    
    @staticmethod
    def _is_late_meal(time_str: str) -> bool:
        """Check if meal is late evening (after 8 PM)."""
        try:
            hour = int(time_str.split(":")[0])
            return hour >= 20
        except:
            return False
