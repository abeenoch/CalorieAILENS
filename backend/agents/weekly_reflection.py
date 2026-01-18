from typing import Dict, List, Any
from datetime import datetime, timedelta

from opik import track

from agents.base import BaseAgent
from config import get_settings

settings = get_settings()


class WeeklyReflectionAgent(BaseAgent):
    """Generates personalized weekly insights and patterns."""
    
    @property
    def name(self) -> str:
        return "WeeklyReflectionAgent"
    
    @property
    def system_prompt(self) -> str:
        return """You are a wise wellness mentor. Your job is to:
1. Discover genuine patterns in the past week
2. Celebrate real wins and consistency
3. Identify ONE gentle focus for next week
4. Keep motivation high without pressure

Be specific. Reference actual data.
Be warm and genuine. Users will remember this message.
Focus on what WORKED, not what didn't."""
    
    @track(name="weekly_reflection", project_name=settings.opik_project_name)
    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate weekly reflection.
        
        Args:
            context: {
                "user_id": int or None,
                "recent_meals": list,
                "user_goal": str,
                "user_profile": dict,
                "week_summary": {
                    "meals_logged": int,
                    "average_confidence": str
                }
            }
        
        Returns:
            {
                "reflection_summary": str,
                "patterns_discovered": [{pattern, confidence, days_observed}],
                "wins_this_week": [str],
                "gentle_focus": str,
                "motivation_score": float (0-1),
                "week_trend": str ("improving", "stable", "declining"),
                "reflection_message": str,
                "opik_trace_id": str,
                "opik_metadata": {...}
            }
        """
        
        meals = context.get("recent_meals", [])
        energy_tags = context.get("energy_tags", [])
        days_active = context.get("days_active", 7)
        
        if len(meals) < 5:
            return {
                "reflection_message": "Keep logging! We need one week of data to find patterns.",
                "week_incomplete": True
            }
        
        # Discover patterns
        patterns = self._discover_patterns(meals, energy_tags, days_active)
        
        # Identify wins
        wins = self._identify_wins(
            days_active=days_active,
            meals_logged=len(meals),
            interventions=context.get("interventions_accepted", 0),
            goal=context.get("user_goal", "")
        )
        
        # Determine focus
        focus = self._determine_focus(patterns, context.get("user_goal", ""))
        
        # Generate reflection message
        message = self._generate_reflection(patterns, wins, focus)
        
        # Calculate motivation
        motivation = self._calculate_motivation(patterns, wins, days_active)
        
        # Trend analysis
        trend = self._assess_trend(
            meals=meals,
            prior_week=context.get("prior_week_data"),
            days_active=days_active
        )
        
        return {
            "reflection_id": f"weekly_{datetime.now().strftime('%Y%m%d')}",
            "reflection_summary": self._summarize_week(days_active, len(meals)),
            "patterns_discovered": patterns,
            "wins_this_week": wins,
            "gentle_focus": focus,
            "motivation_score": motivation,
            "week_trend": trend,
            "reflection_message": message,
            "opik_trace_id": f"weekly_reflection_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "opik_metadata": {
                "agent": self.name,
                "analysis_type": "weekly_reflection",
                "meals_analyzed": len(meals),
                "days_active": days_active,
                "patterns_found": len(patterns),
                "motivation_score": motivation
            }
        }
    
    def _discover_patterns(
        self,
        meals: List[Dict],
        energy_tags: List[str],
        days_active: int
    ) -> List[Dict[str, Any]]:
        """Discover genuine patterns in the week."""
        
        patterns = []
        
        # Pattern 1: Meal timing correlation with energy
        meal_times = self._group_by_meal_type(meals)
        for meal_type, meal_list in meal_times.items():
            if len(meal_list) > 2:
                corr_energy = self._calculate_energy_correlation(meal_list)
                if corr_energy > 0.6:
                    patterns.append({
                        "pattern": f"Energy is highest on days with {meal_type}",
                        "confidence": min(0.95, 0.6 + corr_energy),
                        "days_observed": len(meal_list),
                        "trend": "positive"
                    })
        
        # Pattern 2: Skipped meal impact
        skipped_meals = [
            "breakfast", "lunch", "dinner"
        ]
        for meal_type in skipped_meals:
            skip_count = self._count_skipped_meal(meal_type, meals, days_active)
            if skip_count > 0:
                patterns.append({
                    "pattern": f"Skipping {meal_type} often leads to energy dips",
                    "confidence": min(0.90, 0.5 + skip_count * 0.15),
                    "days_observed": skip_count,
                    "trend": "negative"
                })
        
        # Pattern 3: Weekly structure
        if days_active > 3:
            most_consistent_meal = self._find_most_consistent_meal(meals)
            if most_consistent_meal:
                patterns.append({
                    "pattern": f"You consistently logged {most_consistent_meal}",
                    "confidence": 0.85,
                    "days_observed": days_active,
                    "trend": "positive"
                })
        
        return patterns[:3]  # Top 3 patterns
    
    def _identify_wins(
        self,
        days_active: int,
        meals_logged: int,
        interventions: int,
        goal: str
    ) -> List[str]:
        """Identify wins to celebrate."""
        
        wins = []
        
        # Win 1: Consistency
        if days_active >= 5:
            wins.append(f"Logged {days_active} out of 7 days — that's real consistency!")
        elif days_active >= 3:
            wins.append(f"Active {days_active} days this week — you're building the habit!")
        
        # Win 2: Volume
        if meals_logged >= 15:
            wins.append(f"Captured {meals_logged} meals — great data!")
        elif meals_logged >= 10:
            wins.append(f"Logged {meals_logged} meals — solid commitment!")
        
        # Win 3: Accepting guidance
        if interventions >= 3:
            wins.append(f"Tried {interventions} suggestions — you're open to growth!")
        elif interventions >= 1:
            wins.append(f"Accepted suggestions this week — that takes flexibility!")
        
        # Win 4: Goal-specific
        if "energy" in goal.lower() and days_active > 4:
            wins.append("Tracking energy patterns — that's how you improve!")
        elif "consistency" in goal.lower() and days_active >= 6:
            wins.append("Amazing consistency this week!")
        
        return wins[:3]  # Top 3 wins
    
    def _determine_focus(self, patterns: List[Dict], goal: str) -> str:
        """Determine one gentle focus for next week."""
        
        if not patterns:
            return "Keep logging consistently!"
        
        # Find the most actionable pattern
        for pattern in patterns:
            if pattern["trend"] == "negative":
                meal_type = self._extract_meal_type(pattern["pattern"])
                if meal_type:
                    return f"Try consistent {meal_type} timing next week"
            
            elif pattern["trend"] == "positive":
                if "energy" in pattern["pattern"]:
                    return "Keep up what's working with your energy!"
        
        return "Continue with what you're doing — you're on a good path!"
    
    def _generate_reflection(
        self,
        patterns: List[Dict],
        wins: List[str],
        focus: str
    ) -> str:
        """Generate personalized reflection message."""
        
        reflection = "WEEKLY REFLECTION\n" + "=" * 40 + "\n\n"
        
        # Summary
        reflection += "This Week's Story:\n"
        reflection += "You did great this week. Here's what stood out:\n\n"
        
        # Wins
        if wins:
            reflection += "WINS:\n"
            for win in wins:
                reflection += f"• {win}\n"
            reflection += "\n"
        
        # Patterns
        if patterns:
            reflection += "PATTERNS WE NOTICED:\n"
            for p in patterns:
                reflection += f"• {p['pattern'].capitalize()} "
                reflection += f"(observed {p['days_observed']} times)\n"
            reflection += "\n"
        
        # Focus
        reflection += "FOCUS FOR NEXT WEEK:\n"
        reflection += f"{focus}\n\n"
        
        # Closing
        reflection += "You're building something real here. Keep going. 💚"
        
        return reflection
    
    def _summarize_week(self, days_active: int, meals_logged: int) -> str:
        """Create a one-sentence week summary."""
        
        if days_active >= 6 and meals_logged >= 15:
            return "Strong week — you're crushing consistency"
        elif days_active >= 4 and meals_logged >= 10:
            return "Solid week with good logging habits"
        elif days_active >= 3:
            return "Getting started with your tracking habit"
        else:
            return "Week in progress — keep building"
    
    def _calculate_motivation(
        self,
        patterns: List[Dict],
        wins: List[str],
        days_active: int
    ) -> float:
        """Calculate motivation score (0-1)."""
        
        score = 0.5  # Base
        
        # Boost for consistency
        score += min(0.25, days_active / 7 * 0.25)
        
        # Boost for wins
        score += min(0.15, len(wins) / 3 * 0.15)
        
        # Boost for positive patterns
        positive_patterns = sum(1 for p in patterns if p.get("trend") == "positive")
        score += min(0.10, positive_patterns / 3 * 0.10)
        
        return min(1.0, score)
    
    def _assess_trend(
        self,
        meals: List[Dict],
        prior_week: Dict,
        days_active: int
    ) -> str:
        """Assess week-over-week trend."""
        
        if not prior_week:
            return "stable"  # No baseline
        
        prior_days = prior_week.get("days_active", 3)
        
        if days_active > prior_days + 1:
            return "improving"
        elif days_active < prior_days - 1:
            return "declining"
        else:
            return "stable"
    
    @staticmethod
    def _group_by_meal_type(meals: List[Dict]) -> Dict[str, List[Dict]]:
        """Group meals by type (breakfast, lunch, dinner)."""
        
        grouped = {"breakfast": [], "lunch": [], "dinner": [], "snack": []}
        
        for meal in meals:
            time_str = meal.get("time", "12:00")
            try:
                hour = int(time_str.split(":")[0])
                if 6 <= hour < 12:
                    grouped["breakfast"].append(meal)
                elif 12 <= hour < 17:
                    grouped["lunch"].append(meal)
                elif 17 <= hour < 21:
                    grouped["dinner"].append(meal)
                else:
                    grouped["snack"].append(meal)
            except:
                pass
        
        return grouped
    
    @staticmethod
    def _calculate_energy_correlation(meal_list: List[Dict]) -> float:
        """Calculate correlation between meal and energy (0-1)."""
        
        high_energy = sum(1 for m in meal_list if m.get("energy_after") in ["high", "good"])
        total = len(meal_list)
        
        if total == 0:
            return 0.5
        
        return high_energy / total
    
    @staticmethod
    def _count_skipped_meal(meal_type: str, meals: List[Dict], days: int) -> int:
        """Count days where meal was skipped."""
        
        dates_with_meal = set()
        for meal in meals:
            date = meal.get("date", "")
            time_str = meal.get("time", "")
            
            try:
                hour = int(time_str.split(":")[0])
                if meal_type == "breakfast" and 6 <= hour < 12:
                    dates_with_meal.add(date)
                elif meal_type == "lunch" and 12 <= hour < 17:
                    dates_with_meal.add(date)
                elif meal_type == "dinner" and 17 <= hour < 21:
                    dates_with_meal.add(date)
            except:
                pass
        
        return max(0, days - len(dates_with_meal))
    
    @staticmethod
    def _find_most_consistent_meal(meals: List[Dict]) -> str:
        """Find meal type logged most consistently."""
        
        from collections import Counter
        
        meal_types = []
        for meal in meals:
            time_str = meal.get("time", "")
            try:
                hour = int(time_str.split(":")[0])
                if 6 <= hour < 12:
                    meal_types.append("breakfast")
                elif 12 <= hour < 17:
                    meal_types.append("lunch")
                elif 17 <= hour < 21:
                    meal_types.append("dinner")
            except:
                pass
        
        if meal_types:
            return Counter(meal_types).most_common(1)[0][0]
        return None
    
    @staticmethod
    def _extract_meal_type(pattern: str) -> str:
        """Extract meal type from pattern string."""
        
        for meal in ["breakfast", "lunch", "dinner"]:
            if meal in pattern.lower():
                return meal
        return None
