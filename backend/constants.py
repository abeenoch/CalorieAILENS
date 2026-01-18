# User Profile Validation
VALID_AGE_RANGES = ["12-17", "18-25", "26-35", "36-45", "46-55", "55+"]
VALID_HEIGHT_RANGES = ["150-160cm", "160-170cm", "170-180cm", "180-190cm", "190-200cm", "200+cm"]
VALID_WEIGHT_RANGES = ["40-50kg", "50-60kg", "60-70kg", "70-80kg", "80-90kg", "90-100kg", "100+kg"]
VALID_ACTIVITY_LEVELS = ["low", "medium", "high"]
VALID_GOALS = ["maintain", "gain_energy", "reduce_excess"]

# Feedback Validation
VALID_FEEDBACK_TYPES = ["accurate", "portion_bigger", "portion_smaller", "wrong_food"]

# Meal Context
VALID_MEAL_CONTEXTS = ["homemade", "restaurant", "snack", "meal"]

# Balance Status
BALANCE_STATUS_EMOJI = {
    "under_fueled": "🔵",
    "roughly_aligned": "🟢",
    "slightly_over": "🟠"
}

# Confidence Levels
CONFIDENCE_LEVELS = ["low", "medium", "high"]

# Activity Multipliers for Daily Calorie Estimation
ACTIVITY_MULTIPLIERS = {
    "low": 1800,
    "medium": 2200,
    "high": 2600
}

# Default Values
DEFAULT_ACTIVITY_LEVEL = "medium"
DEFAULT_DAILY_CALORIE_NEED = 2000
DEFAULT_CONFIDENCE = "medium"
DEFAULT_BALANCE_STATUS = "roughly_aligned"

# Meal Analysis
MIN_MEALS_FOR_DRIFT_DETECTION = 5
DAYS_TRACKED_DEFAULT = 7
