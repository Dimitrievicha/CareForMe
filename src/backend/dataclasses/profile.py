from dataclasses import dataclass, field
from datetime import date, datetime
import uuid

@dataclass
class Profile:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    username: str
    password_hash: str  #  хеш пароля (bcrypt/argon2)
    last_entry: date = field(default_factory=date.today)
    created_at: datetime = field(default_factory=datetime.now)
    coins: int = 0      # Валюта игры
    level: int = 1      # Уровень игрока