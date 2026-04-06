import uuid
from datetime import date, datetime
from sqlalchemy import Column, String, Integer, Date, DateTime, Boolean, Float, JSON, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

def generate_uuid() -> str:
    return str(uuid.uuid4())

class Profile(Base):
    __tablename__ = "profiles"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)  # ⚠️ Только хеш!
    last_entry = Column(Date, nullable=False, default=date.today)
    created_at = Column(DateTime, default=datetime.utcnow)
    coins = Column(Integer, default=0)
    level = Column(Integer, default=1)
    plants = relationship("UserPlant", back_populates="owner", cascade="all, delete-orphan")

class PlantTemplate(Base):
    __tablename__ = "plant_templates"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    species_name = Column(String(100), unique=True, nullable=False)
    nickname = Column(String(100))
    description = Column(String)
    character_trait = Column(String(100))
    water_interval_min = Column(Integer)
    water_interval_max = Column(Integer)
    light_requirement = Column(String(20))
    watering_advice = Column(String)
    light_advice = Column(String)
    flowering_conditions = Column(String)
    tips = Column(JSON, default=list)
    symptoms = Column(JSON, default=list)

class UserPlant(Base):
    __tablename__ = "user_plants"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    template_id = Column(String(36), ForeignKey("plant_templates.id"), nullable=False)
    custom_name = Column(String(100), default="")
    last_watered = Column(Date, default=date.today)
    health_status = Column(String(20), default="healthy")
    growth_stage = Column(String(20), default="seedling")
    growth_progress = Column(Float, default=0.0)
    current_light_level = Column(String(20), default="medium")
    acquired_at = Column(DateTime, default=datetime.utcnow)
    is_alive = Column(Boolean, default=True)
    owner = relationship("Profile", back_populates="plants")
    template = relationship("PlantTemplate")

class Challenge(Base):
    __tablename__ = "challenges"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String)
    requirement_type = Column(String(50))
    target_value = Column(Integer)
    reward_coins = Column(Integer, default=50)
    is_active = Column(Boolean, default=True)

class UserChallenge(Base):
    __tablename__ = "user_challenges"
    user_id = Column(String(36), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True)
    challenge_id = Column(String(36), ForeignKey("challenges.id", ondelete="CASCADE"), primary_key=True)
    current_progress = Column(Integer, default=0)
    is_completed = Column(Boolean, default=False)
    completed_at = Column(Date, nullable=True)