"""
Репозиторий для работы с пользователями и профилями.

Содержит методы для работы с таблицами:
    - users: учетные записи пользователей
    - sessions: сессии входа
    - player_profiles: игровые профили
"""

from typing import Optional, Dict, Any
from .base_repository import BaseRepository
import json

class UserRepository(BaseRepository):
    """
    Репозиторий для таблиц users, sessions и player_profiles.

    Обрабатывает все операции, связанные с пользователями:
        - CRUD для учетных записей
        - Управление сессиями
        - Игровые профили и статистика
    """

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает пользователя по ID.

        Args:
            user_id: UUID пользователя

        Returns:
            Словарь с данными пользователя или None

        Returns структура:
            {
                "id": "uuid-...",
                "username": "john",
                "password_hash": "sha256...",
                "created_at": "2024-01-01 12:00:00",
                "last_login": "2024-01-02 15:30:00",
                "login_count": 5
            }
        """
        return self.get_by_id("users", "id", user_id)

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Получает пользователя по имени.

        Args:
            username: Имя пользователя

        Returns:
            Словарь с данными пользователя или None
        """
        result = self.db.execute_query(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        )
        return result[0] if result else None

    def create_user(self, user_id: str, username: str, password_hash: str) -> bool:
        """
        Создает нового пользователя.

        Args:
            user_id: UUID пользователя
            username: Имя пользователя
            password_hash: Хэш пароля

        Returns:
            True при успехе, False при ошибке
        """
        return self.db.execute_update("""
            INSERT INTO users (id, username, password_hash)
            VALUES (?, ?, ?)
        """, (user_id, username, password_hash))

    def update_last_login(self, user_id: str) -> bool:
        """
        Обновляет время последнего входа и счетчик входов.

        Args:
            user_id: ID пользователя

        Returns:
            True при успехе
        """
        return self.db.execute_update("""
            UPDATE users SET last_login = CURRENT_TIMESTAMP, login_count = login_count + 1
            WHERE id = ?
        """, (user_id,))

    def user_exists(self, username: str) -> bool:
        """
        Проверяет существование пользователя с таким именем.

        Args:
            username: Имя пользователя

        Returns:
            True если пользователь существует
        """
        return self.count("users", "username = ?", (username,)) > 0

    def create_session(self, user_id: str, token: str, expires_at: str) -> bool:
        """
        Создает новую сессию для пользователя.

        Args:
            user_id: ID пользователя
            token: Уникальный токен сессии
            expires_at: Дата истечения в ISO формате

        Returns:
            True при успехе
        """
        return self.db.execute_update("""
            INSERT INTO sessions (user_id, token, expires_at)
            VALUES (?, ?, ?)
        """, (user_id, token, expires_at))

    def get_session_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Получает сессию по токену (только активные).

        Args:
            token: Токен сессии

        Returns:
            Данные сессии или None
        """
        result = self.db.execute_query(
            "SELECT * FROM sessions WHERE token = ? AND is_revoked = 0",
            (token,)
        )
        return result[0] if result else None

    def revoke_session(self, token: str) -> bool:
        """
        Отзывает (завершает) сессию при выходе.

        Args:
            token: Токен сессии

        Returns:
            True при успехе
        """
        return self.db.execute_update(
            "UPDATE sessions SET is_revoked = 1 WHERE token = ?",
            (token,)
        )

    def revoke_all_user_sessions(self, user_id: str, keep_token: str = None) -> bool:
        """
        Отзывает все сессии пользователя (выход со всех устройств).

        Args:
            user_id: ID пользователя
            keep_token: Токен, который нужно сохранить (опционально)

        Returns:
            True при успехе

        """
        if keep_token:
            return self.db.execute_update("""
                UPDATE sessions SET is_revoked = 1 WHERE user_id = ? AND token != ?
            """, (user_id, keep_token))
        return self.db.execute_update(
            "UPDATE sessions SET is_revoked = 1 WHERE user_id = ?",
            (user_id,)
        )

    def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает игровой профиль пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Данные профиля или None

        Returns структура:
            {
                "user_id": "uuid-...",
                "display_name": "john",
                "current_level": 2,           # Текущий уровень (1-5)
                "max_plants_slots": 2,        # Максимум слотов
                "total_plants_grown": 3,      # Всего выращено
                "total_waterings": 15,        # Всего поливов
                "total_mistakes": 2,          # Всего ошибок
                "total_deaths": 1,            # Всего смертей
                "current_plants_count": 2,    # Текущих растений
                "consecutive_days": 5,        # Серия дней
                "best_streak": 5,             # Лучшая серия
                "unlocked_pots": '["standard", "design_pot_1"]',  # JSON
                "unlocked_watering_cans": '["standard"]',         # JSON
                "current_pot": "standard",
                "current_watering_can": "standard"
            }
        """
        result = self.db.execute_query(
            "SELECT * FROM player_profiles WHERE user_id = ?",
            (user_id,)
        )
        return result[0] if result else None

    def create_profile(self, user_id: str, display_name: str = None) -> bool:
        """
        Создает игровой профиль для нового пользователя.

        Args:
            user_id: ID пользователя
            display_name: Отображаемое имя (по умолчанию = username)

        Returns:
            True при успехе
        """
        return self.db.execute_update("""
            INSERT INTO player_profiles (user_id, display_name)
            VALUES (?, ?)
        """, (user_id, display_name))

    def update_level(self, user_id: str, new_level: int) -> bool:
        """
        Обновляет уровень пользователя.

        Args:
            user_id: ID пользователя
            new_level: Новый уровень (1-5)

        Returns:
            True при успехе
        """
        return self.db.execute_update("""
            UPDATE player_profiles SET current_level = ? WHERE user_id = ?
        """, (new_level, user_id))

    def update_streak(self, user_id: str, consecutive_days: int, best_streak: int) -> bool:
        """
        Обновляет серию дней подряд.

        Args:
            user_id: ID пользователя
            consecutive_days: Текущая серия дней
            best_streak: Лучшая серия за все время

        Returns:
            True при успехе
        """
        return self.db.execute_update("""
            UPDATE player_profiles 
            SET last_entry = CURRENT_DATE, consecutive_days = ?, best_streak = ?
            WHERE user_id = ?
        """, (consecutive_days, best_streak, user_id))

    def update_plant_slots(self, user_id: str, delta: int) -> bool:
        """
        Изменяет количество слотов для растений.

        Args:
            user_id: ID пользователя
            delta: На сколько изменить (+1 = +1 слот, -1 = -1 слот)

        Returns:
            True при успехе
        """
        return self.db.execute_update("""
            UPDATE player_profiles SET max_plants_slots = max_plants_slots + ? WHERE user_id = ?
        """, (delta, user_id))

    def update_current_plants_count(self, user_id: str, delta: int) -> bool:
        """
        Изменяет количество текущих растений.

        Args:
            user_id: ID пользователя
            delta: На сколько изменить (+1 при посадке, -1 при смерти)

        Returns:
            True при успехе
        """
        return self.db.execute_update("""
            UPDATE player_profiles SET current_plants_count = current_plants_count + ? WHERE user_id = ?
        """, (delta, user_id))

    def increment_stat(self, user_id: str, stat_name: str, delta: int = 1) -> bool:
        """
        Увеличивает статистику пользователя.

        Args:
            user_id: ID пользователя
            stat_name: Название статистики
                - total_plants_grown: выращено растений
                - total_waterings: поливов
                - total_mistakes: ошибок
                - total_deaths: смертей
            delta: На сколько увеличить (по умолчанию 1)

        Returns:
            True при успехе, False если stat_name некорректен

        """
        allowed_stats = ['total_plants_grown', 'total_waterings', 'total_mistakes', 'total_deaths']
        if stat_name not in allowed_stats:
            return False
        return self.db.execute_update(f"""
            UPDATE player_profiles SET {stat_name} = {stat_name} + ? WHERE user_id = ?
        """, (delta, user_id))

    def unlock_pot(self, user_id: str, pot_id: str) -> bool:
        """
        Открывает новый дизайн горшка для пользователя.

        Args:
            user_id: ID пользователя
            pot_id: ID дизайна горшка (из таблицы designs)

        Returns:
            True при успехе

        """
        profile = self.get_profile(user_id)
        if not profile:
            return False

        import json
        unlocked = json.loads(profile['unlocked_pots'])
        if pot_id not in unlocked:
            unlocked.append(pot_id)
            return self.db.execute_update("""
                UPDATE player_profiles SET unlocked_pots = ? WHERE user_id = ?
            """, (json.dumps(unlocked), user_id))
        return True

    def unlock_watering_can(self, user_id: str, can_id: str) -> bool:
        """
        Открывает новый дизайн лейки для пользователя.

        Args:
            user_id: ID пользователя
            can_id: ID дизайна лейки (из таблицы designs)

        Returns:
            True при успехе
        """
        profile = self.get_profile(user_id)
        if not profile:
            return False

        unlocked = json.loads(profile['unlocked_watering_cans'])
        if can_id not in unlocked:
            unlocked.append(can_id)
            return self.db.execute_update("""
                UPDATE player_profiles SET unlocked_watering_cans = ? WHERE user_id = ?
            """, (json.dumps(unlocked), user_id))
        return True