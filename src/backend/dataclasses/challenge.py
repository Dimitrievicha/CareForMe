from dataclasses import dataclass, field
import uuid

@dataclass
class Challenge:
    """Определение достижения"""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str
    description: str
    requirement_type: str   # "water_streak", "grow_to_mature", "keep_alive_days"
    target_value: int
    reward_coins: int = 50
    is_active: bool = True