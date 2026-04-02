from dataclasses import dataclass
from datetime import date 

@dataclass
class Challenge:
    name: str # наименование очивки
    description: str # описание очивки 
    score_challenge: bool = False # есть ли это достижение
    when_received: date # дата получения очивки