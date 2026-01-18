from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import Counter

from opik import track

from agents.base import BaseAgent
from config import get_settings

settings = get_settings()


class DriftDetectionAgent(BaseAgent):
    """Detects behavioral drift patterns over time."""
    
    @property
    def name(self) -> str:
        return "DriftDetectionAgent"
    
    @property
    def system_prompt(self) -> str:
        return """You are a behavioral pattern analyst. Your job is to:
1. Identify patterns in user behavior (meals, timing, energy)
2. Detect drift from established patterns
3. Quantify severity on 0-1 scale
4. Suggest interventions based on patterns

Be specific with observations. Quote actual data.
Show your confidence level.
Focus on user wellbeing, not judgment."""
    
    @track(name="drift_detector", project_name=settings.opik_project_name)
    async def process(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze user behavior for drift signals.
        
        Args:
            user_data: {
                "user_id": int,
                "meals": [{date, time, foods, energy_tag}],
                "days_tracked": int,
                "user_goal": str,
                "user_profile": {age, height, weight, ...}
            }
        
        Returns:
            {
                "drift_detected": bool,
                "drift_type": str,
                "severity": float (0-1),
                "confidence": float,
                "pattern": str,
                "suggestion": str,
                "intervention_offered": bool,
                "opik_metadata": {...}
            }
        """
        
        meals = user_data.get("meals", [])
        days_tracked = user_data.get("days_tracked", 7)
        
        if len(meals) < 5:
            # Not enough data
            return {
                "drift_detected": False,
                "reason": "Insufficient data (< 5 meals)",
                "confidence": 0.0,
                "recommendation": "Continue logging to establish patterns"
            }
        
        # Analyze patterns
        patterns = self._analyze_patterns(meals, days_tracked)
        drift = self._detect_drift(patterns)
        
        # Generate agent reasoning
        reasoning = self._generate_reasoning(drift, patterns)
        
        return {
            "drift_detected": drift["detected"],
            "drift_type": drift.get("type", "none"),
            "severity": drift.get("severity", 0.0),
            "days_observed": drift.get("days_observed", 0),
            "pattern": drift.get("pattern", ""),
            "confidence": drift.get("confidence", 0.0),
            "suggestion": drift.get("suggestion", ""),
            "intervention_offered": drift.get("detected", False),
            "patterns_found": patterns,
            "reasoning": reasoning,
            "opik_metadata": {
                "agent": self.name,
                "analysis_type": "behavioral_drift",
                "data_points": len(meals),
                "period_days": days_tracked,
                "patterns_detected": len(patterns)
            }
        }
    
    def _analyze_patterns(self, meals: List[Dict], days: int) -> Dict[str, Any]:
        """Analyze meal patterns from historical data."""
        patterns = {}
        
        if not meals:
            return patterns
        
        # Extract unique dates from meals to calculate actual days tracked
        meal_dates = set()
        for m in meals:
            try:
                created_at = m.get("created_at", "")
                if created_at:
                    meal_date = created_at.split("T")[0]
                    meal_dates.add(meal_date)
            except:
                pass
        
        actual_days_tracked = len(meal_dates) if meal_dates else 1
        
        # Meal frequency by meal type
        meal_times = []
        for m in meals:
            time_str = m.get("time") or m.get("created_at", "")
            if time_str:
                meal_times.append(self._extract_meal_time(time_str))
        
        meal_counts = Counter(meal_times)
        patterns["meal_frequency"] = dict(meal_counts)
        
        # Meal skipping - only calculate if we have enough data (at least 5 days)
        if actual_days_tracked >= 5:
            expected_meals_per_day = 3
            meals_logged_per_day = len(meals) / max(actual_days_tracked, 1)
            skipped_meals = max(0, (expected_meals_per_day * actual_days_tracked) - len(meals))
            patterns["skipped_meals_estimate"] = skipped_meals
            patterns["logging_frequency"] = meals_logged_per_day
        else:
            # Not enough data for skipping analysis
            patterns["skipped_meals_estimate"] = 0
            patterns["logging_frequency"] = len(meals) / max(actual_days_tracked, 1)
        
        patterns["actual_days_tracked"] = actual_days_tracked
        
        # Energy tag analysis
        energy_tags = [m.get("energy_tag") for m in meals if m.get("energy_tag")]
        if energy_tags:
            energy_counts = Counter(energy_tags)
            patterns["energy_distribution"] = dict(energy_counts)
            patterns["low_energy_frequency"] = energy_counts.get("low", 0) / len(energy_tags)
        
        # Meal timing variance
        times = [self._time_to_hours(m["time"]) for m in meals if "time" in m]
        if len(times) > 1:
            avg_time = sum(times) / len(times)
            variance = sum((t - avg_time) ** 2 for t in times) / len(times)
            patterns["timing_variance"] = variance
            patterns["timing_stability"] = 1.0 - min(variance / 4, 1.0)
        
        return patterns
    
    def _detect_drift(self, patterns: Dict[str, Any]) -> Dict[str, Any]:
        """Detect specific drift signals and quantify."""
        
        drift_signals = []
        
        # Only analyze drift if user has been tracking for at least 5 days
        actual_days = patterns.get("actual_days_tracked", 0)
        if actual_days < 5:
            return {
                "detected": False,
                "reason": f"Insufficient tracking history ({actual_days} days). Need at least 5 days to detect patterns."
            }
        
        # Signal 1: Meal skipping pattern
        skipped = patterns.get("skipped_meals_estimate", 0)
        if skipped > 3:
            drift_signals.append({
                "type": "meal_skipping",
                "severity": min(skipped / 7, 1.0),
                "pattern": f"Approximately {int(skipped)} meals skipped in {actual_days} days"
            })
        
        # Signal 2: Logging frequency decline
        log_freq = patterns.get("logging_frequency", 0)
        if log_freq < 1.5:  # Less than 1.5 meals/day is low
            drift_signals.append({
                "type": "logging_decline",
                "severity": max(0, 1.0 - log_freq),
                "pattern": f"Logging only {log_freq:.1f} meals/day (expected 3)"
            })
        
        # Signal 3: Energy irregularity
        low_energy_freq = patterns.get("low_energy_frequency", 0)
        if low_energy_freq > 0.4:  # More than 40% low energy is concerning
            drift_signals.append({
                "type": "energy_irregularity",
                "severity": min((low_energy_freq - 0.3) / 0.4, 1.0),
                "pattern": f"{int(low_energy_freq * 100)}% of logged meals had low energy"
            })
        
        # Signal 4: Meal timing instability
        stability = patterns.get("timing_stability", 1.0)
        if stability < 0.6:  # Timing all over the place
            drift_signals.append({
                "type": "timing_instability",
                "severity": 1.0 - stability,
                "pattern": f"Meal timing highly variable (consistency: {stability:.0%})"
            })
        
        if not drift_signals:
            return {"detected": False}
        
        # Take most severe signal
        most_severe = max(drift_signals, key=lambda x: x["severity"])
        
        return {
            "detected": True,
            "type": most_severe["type"],
            "severity": most_severe["severity"],
            "pattern": most_severe["pattern"],
            "confidence": min(0.95, 0.6 + (most_severe["severity"] * 0.3)),
            "days_observed": actual_days,
            "suggestion": self._suggest_intervention(most_severe["type"])
        }
    
    def _suggest_intervention(self, drift_type: str) -> str:
        """Generate intervention suggestion based on drift type."""
        suggestions = {
            "meal_skipping": "A lightweight strategy for consistently skipped meals",
            "logging_decline": "Try a simpler logging approach to reduce friction",
            "energy_irregularity": "Focus on meal regularity to stabilize your energy",
            "timing_instability": "Set one anchor meal to build consistency around"
        }
        return suggestions.get(drift_type, "Let's refocus on your core goal")
    
    def _generate_reasoning(self, drift: Dict, patterns: Dict) -> str:
        """Generate human-readable reasoning."""
        if not drift.get("detected"):
            return "No significant drift patterns detected. Keep up the consistency!"
        
        return f"""Pattern Analysis:
- Type: {drift.get("type", "unknown").replace("_", " ").title()}
- Severity: {drift.get("severity", 0):.0%}
- Confidence: {drift.get("confidence", 0):.0%}
- Observation: {drift.get("pattern", "")}

This suggests you might benefit from: {drift.get("suggestion", "gentle refocus")}"""
    
    @staticmethod
    def _extract_meal_time(time_str: str) -> str:
        """Categorize time into breakfast/lunch/dinner."""
        try:
            hour = int(time_str.split(":")[0])
            if 6 <= hour < 12:
                return "breakfast"
            elif 12 <= hour < 17:
                return "lunch"
            elif 17 <= hour < 21:
                return "dinner"
            else:
                return "snack"
        except:
            return "unknown"
    
    @staticmethod
    def _time_to_hours(time_str: str) -> float:
        """Convert time string to hours (0-24)."""
        try:
            parts = time_str.split(":")
            return int(parts[0]) + int(parts[1]) / 60
        except:
            return 12.0
