from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field



class UserCreate(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token payload data."""
    user_id: Optional[int] = None



class ProfileUpdate(BaseModel):
    """Schema for updating user profile - all ranges, not exact numbers."""
    gender: Optional[str] = Field(None, description="Gender: 'male', 'female', 'other'")
    age_range: Optional[str] = Field(None, description="Age range: '18-25', '26-35', '36-45', '46-55', '55+'")
    height_range: Optional[str] = Field(None, description="Height range: '150-160cm', '160-170cm', etc.")
    weight_range: Optional[str] = Field(None, description="Weight range: '50-60kg', '60-70kg', etc.")
    activity_level: Optional[str] = Field(None, description="Activity level: 'low', 'medium', 'high'")
    goal: Optional[str] = Field(None, description="Goal: 'maintain', 'gain_energy', 'reduce_excess', or custom goal text")


class ProfileResponse(BaseModel):
    """Schema for profile response."""
    id: int
    email: str
    gender: Optional[str] = None
    age_range: Optional[str] = None
    height_range: Optional[str] = None
    weight_range: Optional[str] = None
    activity_level: Optional[str] = None
    goal: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True



class MealAnalysisRequest(BaseModel):
    """Schema for meal analysis request."""
    image_data: str = Field(..., description="Base64 encoded image data")
    image_mime_type: str = Field(default="image/jpeg", description="MIME type of the image")
    context: Optional[str] = Field(None, description="Context: 'homemade', 'restaurant', 'snack', 'meal'")
    notes: Optional[str] = Field(None, description="Additional notes about the meal")


class FoodItem(BaseModel):
    """Individual food item identified."""
    name: str
    portion: str
    confidence: str


class VisionResult(BaseModel):
    """Vision interpreter agent output."""
    foods: List[FoodItem]
    image_ambiguity: str
    context_applied: Optional[str] = None
    barcode_detected: Optional[str] = None


class NutritionResult(BaseModel):
    """Nutrition reasoner agent output."""
    total_calories: dict  # {"min": int, "max": int}
    macros: dict  # {"protein": str, "carbs": str, "fat": str}
    uncertainty: str


class PersonalizationResult(BaseModel):
    """Personalization agent output."""
    balance_status: str  # "under_fueled", "roughly_aligned", "slightly_over"
    daily_context: str
    remaining_estimate: Optional[dict] = None  # {"min": int, "max": int}


class WellnessResult(BaseModel):
    """Wellness coach agent output."""
    message: str
    emoji_indicator: str  # "🔵", "🟢", "🟠"
    suggestions: List[str]
    disclaimer_shown: bool = True


class MealAnalysisResponse(BaseModel):
    """Complete meal analysis response."""
    meal_id: int
    vision: VisionResult
    nutrition: NutritionResult
    personalization: PersonalizationResult
    wellness: WellnessResult
    confidence_score: str
    created_at: datetime


class MealHistoryItem(BaseModel):
    """Schema for meal history item."""
    id: int
    context: Optional[str]
    vision_result: Optional[dict]
    nutrition_result: Optional[dict]
    wellness_result: Optional[dict]
    confidence_score: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True



class FeedbackCreate(BaseModel):
    """Schema for creating feedback."""
    meal_id: int
    feedback_type: str = Field(..., description="Type: 'accurate', 'portion_bigger', 'portion_smaller', 'wrong_food'")
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    """Schema for feedback response."""
    id: int
    meal_id: int
    feedback_type: str
    comment: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True



class DailyBalanceResponse(BaseModel):
    """Schema for daily energy balance response."""
    date: datetime
    total_calories_min: Optional[int]
    total_calories_max: Optional[int]
    balance_status: Optional[str]
    reasoning: Optional[str]
    meals_count: int
    emoji_indicator: str



class HealthCheck(BaseModel):
    """Health check response."""
    status: str = "healthy"
    version: str = "1.0.0"
    timestamp: datetime


class NotificationPreferenceUpdate(BaseModel):
    """Schema for updating notification preferences."""
    meal_reminders_enabled: Optional[bool] = None
    meal_reminder_time: Optional[str] = Field(None, description="Time in HH:MM format, e.g., '12:00'")
    weekly_summary_enabled: Optional[bool] = None
    weekly_summary_day: Optional[str] = Field(None, description="Day of week: 'monday', 'sunday', etc.")
    weekly_summary_time: Optional[str] = Field(None, description="Time in HH:MM format, e.g., '19:00'")


class NotificationPreferenceResponse(BaseModel):
    """Schema for notification preferences response."""
    meal_reminders_enabled: bool
    meal_reminder_time: Optional[str]
    weekly_summary_enabled: bool
    weekly_summary_day: Optional[str]
    weekly_summary_time: Optional[str]


class WeeklyExportResponse(BaseModel):
    """Schema for weekly export response."""
    share_token: str
    share_url: str
    summary: dict
