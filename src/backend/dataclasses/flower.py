from dataclasses import dataclass
from datetime import date 

@dataclass
class Flower:
    name_flower: str # наименование цветка
    description: str # описание по цветку
    water_interval_days: int # через сколько дней нужен полив
    light_requirement: str # уровень света для цветка low, medium, hight
    last_watered_day: date  # когда последний раз поливали
    wilting: str # состояние здоровья
    growth_stage: str # стадия роста 

