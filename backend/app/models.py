from datetime import datetime, date, timezone
from sqlalchemy import String, Integer, Float, Boolean, DateTime, Date, ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------- reference data (filled by scripts/ingest.py) ----------
class Food(Base):
    """USDA FoodData Central Foundation Foods, values per 100 g."""
    __tablename__ = "foods"
    fdc_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    description: Mapped[str] = mapped_column(String(300), index=True)
    category: Mapped[str | None] = mapped_column(String(120), index=True)
    kcal: Mapped[float] = mapped_column(Float)
    protein_g: Mapped[float | None] = mapped_column(Float)
    fat_g: Mapped[float | None] = mapped_column(Float)
    carb_g: Mapped[float | None] = mapped_column(Float)
    fiber_g: Mapped[float | None] = mapped_column(Float)
    sugar_g: Mapped[float | None] = mapped_column(Float)
    sodium_mg: Mapped[float | None] = mapped_column(Float)
    sat_fat_g: Mapped[float | None] = mapped_column(Float)
    cholesterol_mg: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(80), default="USDA FDC Foundation Foods 2026-04-30")


class FoodPortion(Base):
    __tablename__ = "food_portions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fdc_id: Mapped[int] = mapped_column(ForeignKey("foods.fdc_id"), index=True)
    amount: Mapped[float] = mapped_column(Float)
    unit_label: Mapped[str] = mapped_column(String(200))
    gram_weight: Mapped[float] = mapped_column(Float)


class NutrientRef(Base):
    __tablename__ = "nutrient_ref"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    unit_name: Mapped[str] = mapped_column(String(20))


class MetActivity(Base):
    """Compendium of Physical Activities MET values."""
    __tablename__ = "met_activities"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(60))
    name: Mapped[str] = mapped_column(String(200))
    met: Mapped[float] = mapped_column(Float)
    compendium_code: Mapped[str | None] = mapped_column(String(20))
    source: Mapped[str] = mapped_column(String(120), default="seed")


# ---------- application data ----------
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="user")
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    google_sub: Mapped[str | None] = mapped_column(String(64), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    profile: Mapped["Profile"] = relationship(back_populates="user", uselist=False, cascade="all,delete")


class Profile(Base):
    __tablename__ = "profiles"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(120))
    age: Mapped[int | None] = mapped_column(Integer)
    sex: Mapped[str | None] = mapped_column(String(10))
    height_cm: Mapped[float | None] = mapped_column(Float)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    activity_level: Mapped[str] = mapped_column(String(20), default="light")
    goal_type: Mapped[str] = mapped_column(String(20), default="maintain")
    target_weight_kg: Mapped[float | None] = mapped_column(Float)
    target_date: Mapped[date | None] = mapped_column(Date)
    experience: Mapped[str] = mapped_column(String(20), default="beginner")
    diet_preferences: Mapped[list] = mapped_column(JSON, default=list)
    allergies: Mapped[list] = mapped_column(JSON, default=list)
    equipment: Mapped[list] = mapped_column(JSON, default=list)
    workout_preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    conditions: Mapped[list] = mapped_column(JSON, default=list)
    user: Mapped[User] = relationship(back_populates="profile")


class _Log:
    id: Mapped[int] = mapped_column(Integer, primary_key=True)


class FoodLog(Base):
    __tablename__ = "food_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    meal: Mapped[str] = mapped_column(String(12))
    fdc_id: Mapped[int] = mapped_column(ForeignKey("foods.fdc_id"))
    description: Mapped[str] = mapped_column(String(300))
    grams: Mapped[float] = mapped_column(Float)
    kcal: Mapped[float] = mapped_column(Float)
    protein_g: Mapped[float] = mapped_column(Float, default=0)
    carb_g: Mapped[float] = mapped_column(Float, default=0)
    fat_g: Mapped[float] = mapped_column(Float, default=0)
    fiber_g: Mapped[float] = mapped_column(Float, default=0)


class WorkoutLog(Base):
    __tablename__ = "workout_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    activity_key: Mapped[str] = mapped_column(String(80))
    minutes: Mapped[float] = mapped_column(Float)
    intensity: Mapped[int | None] = mapped_column(Integer)
    sets: Mapped[int | None] = mapped_column(Integer)
    reps: Mapped[int | None] = mapped_column(Integer)
    kcal_burned: Mapped[float] = mapped_column(Float)
    method: Mapped[str] = mapped_column(String(40), default="MET")


class SleepLog(Base):
    __tablename__ = "sleep_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    bedtime: Mapped[str] = mapped_column(String(5))
    wake_time: Mapped[str] = mapped_column(String(5))
    hours: Mapped[float] = mapped_column(Float)
    quality: Mapped[int] = mapped_column(Integer)


class WaterLog(Base):
    __tablename__ = "water_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    ml: Mapped[float] = mapped_column(Float)


class WeightLog(Base):
    __tablename__ = "weight_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    weight_kg: Mapped[float] = mapped_column(Float)
    waist_cm: Mapped[float | None] = mapped_column(Float)


class Achievement(Base):
    __tablename__ = "achievements"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    key: Mapped[str] = mapped_column(String(40))
    earned_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class AuthToken(Base):
    """Single-use tokens for email verification and password reset."""
    __tablename__ = "auth_tokens"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    purpose: Mapped[str] = mapped_column(String(20))
    token_hash: Mapped[str] = mapped_column(String(64), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
