from dataclasses import dataclass, field
from datetime import date, datetime
import uuid

@dataclass
class UserPlant:
    """Конкретное растение у пользователя"""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    user_id: uuid.UUID
    template_id: uuid.UUID   # Ссылка на PlantTemplate
    custom_name: str = ""
    last_watered: date = field(default_factory=date.today)
    health_status: str = "healthy"  # "healthy", "thirsty", "overwatered", "burned", "dying"
    growth_stage: str = "seedling"  # "seedling", "vegetative", "mature", "flowering"
    growth_progress: float = 0.0    # 0.0 - 100.0%
    current_light_level: str = "medium" # Текущее освещение в комнате игрока
    acquired_at: datetime = field(default_factory=datetime.now)
    is_alive: bool = True