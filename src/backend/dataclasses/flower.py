from dataclasses import dataclass, field
import uuid
from typing import List, Dict

@dataclass
class PlantTemplate:
    """Справочник видов растений (заполняется один раз разработчиком)"""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    species_name: str          # Научное название: "Спатифиллюм"
    nickname: str              # Игровое название: "Женское счастье"
    description: str
    character_trait: str       # "Чуткий перфекционист"
    water_interval_min: int    # Мин. дней между поливом
    water_interval_max: int    # Макс. дней между поливом
    light_requirement: str     # "low", "medium", "high"
    watering_advice: str
    light_advice: str
    flowering_conditions: str
    tips: List[str] = field(default_factory=list)
    symptoms: List[Dict[str, str]] = field(default_factory=list) # [{"symptom": "...", "cause": "..."}]