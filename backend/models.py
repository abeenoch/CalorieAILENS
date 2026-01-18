from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class User(Base):
    """User model with lightweight profile information."""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Lightweight profile - all ranges, not exact numbers (safety win)
    age_range: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # "18-25", "26-35", etc.
    height_range: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # "150-160cm", etc.
    weight_range: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # "50-60kg", etc.
    activity_level: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # "low", "medium", "high"
    goal: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)  # "maintain", "gain_energy", "reduce_excess"
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    meals: Mapped[list["Meal"]] = relationship("Meal", back_populates="user", cascade="all, delete-orphan")


class Meal(Base):
    """Meal record with analysis results."""
    __tablename__ = "meals"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Image data
    image_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Base64 encoded
    image_mime_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # User-provided context
    context: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # "homemade", "restaurant", "snack", "meal"
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Agent analysis results (stored as JSON)
    vision_result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    nutrition_result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    personalization_result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    wellness_result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Metadata
    confidence_score: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # "low", "medium", "high"
    image_ambiguity: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="meals")
    feedbacks: Mapped[list["Feedback"]] = relationship("Feedback", back_populates="meal", cascade="all, delete-orphan")


class Feedback(Base):
    """User feedback for model correction and Opik observability."""
    __tablename__ = "feedbacks"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meal_id: Mapped[int] = mapped_column(Integer, ForeignKey("meals.id"), nullable=False, index=True)
    
    # Feedback type
    feedback_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "accurate", "portion_bigger", "portion_smaller", "wrong_food"
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    meal: Mapped["Meal"] = relationship("Meal", back_populates="feedbacks")


class DailyBalance(Base):
    """Daily energy balance tracking."""
    __tablename__ = "daily_balances"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    
    # Balance calculations
    total_calories_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_calories_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    balance_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)  # "under_fueled", "roughly_aligned", "slightly_over"
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
