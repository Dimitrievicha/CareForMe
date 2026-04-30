"""
Репозиторий для работы с пользователями и профилями.

Содержит методы для работы с таблицами:
    - users: учетные записи пользователей
    - sessions: сессии входа
    - player_profiles: игровые профили
"""

from typing import Optional, Dict, Any, List
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

    # ============================================================
    # ПОЛЬЗОВАТЕЛИ (таблица users)
    # ============================================================

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
            username: Имя пользователя (уникальное)

        Returns:
            Словарь с данными пользователя или None
        """
        return self.get_one_by_field("users", "username", username)

    def create_user(self, user_id: str, username: str, password_hash: str) -> bool:
        """
        Создает нового пользователя.

        Args:
            user_id: UUID нового пользователя (генерируется заранее)
            username: Имя пользователя (уникальное, мин. 3 символа)
            password_hash: Хэш пароля (SHA-256)

        Returns:
            True при успехе, False при ошибке (например, дубликат username)
        """
        return self.insert("users", {
            "id": user_id,
            "username": username,
            "password_hash": password_hash
        })

    def update_last_login(self, user_id: str) -> bool:
        """
        Обновляет время последнего входа и счетчик входов.
        
        Вызывается при каждом успешном входе.

        Args:
            user_id: ID пользователя

        Returns:
            True при успехе
        """
        return self.db.execute_update("""
            UPDATE users 
            SET last_login = CURRENT_TIMESTAMP, login_count = login_count + 1
            WHERE id = ?
        """, (user_id,))

    def user_exists(self, username: str) -> bool:
        """
        Проверяет существование пользователя с таким именем.

        Args:
            username: Имя пользователя

        Returns:
            True если пользователь существует, иначе False
        """
        return self.exists("users", "username = ?", (username,))

    # ============================================================
    # СЕССИИ (таблица sessions)
    # ============================================================

    def create_session(self, user_id: str, token: str, expires_at: str) -> bool:
        """
        Создает новую сессию для пользователя.

        Args:
            user_id: ID пользователя
            token: Уникальный токен сессии (генерируется через secrets.token_urlsafe)
            expires_at: Дата истечения в ISO формате

        Returns:
            True при успехе
        """
        return self.insert("sessions", {
            "user_id": user_id,
            "token": token,
            "expires_at": expires_at
        })

    def get_session_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Получает сессию по токену (только активные, не отозванные).

        Args:
            token: Токен сессии

        Returns:
            Данные сессии или None, если токен не найден или отозван
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
                UPDATE sessions SET is_revoked = 1 
                WHERE user_id = ? AND token != ?
            """, (user_id, keep_token))
        return self.db.execute_update(
            "UPDATE sessions SET is_revoked = 1 WHERE user_id = ?",
            (user_id,)
        )

    # ============================================================
    # ИГРОВЫЕ ПРОФИЛИ (таблица player_profiles)
    # ============================================================

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
                "unlocked_pots": '["standard", "design_pot_1"]',  # JSON строка
                "unlocked_watering_cans": '["standard"]',         # JSON строка
                "current_pot": "standard",
                "current_watering_can": "standard"
            }
        """
        return self.get_by_id("player_profiles", "user_id", user_id)

    def create_profile(self, user_id: str, display_name: str = None) -> bool:
        """
        Создает игровой профиль для нового пользователя.
        
        Вызывается сразу после регистрации.

        Args:
            user_id: ID пользователя
            display_name: Отображаемое имя (по умолчанию будет установлено позже)

        Returns:
            True при успехе
        """
        return self.insert("player_profiles", {
            "user_id": user_id,
            "display_name": display_name
        })

    def update_level(self, user_id: str, new_level: int) -> bool:
        """
        Обновляет уровень пользователя.
        
        Уровень повышается только после выполнения всех заданий текущего уровня.

        Args:
            user_id: ID пользователя
            new_level: Новый уровень (1-5)

        Returns:
            True при успехе
        """
        return self.update("player_profiles", "user_id", user_id, {
            "current_level": new_level
        })

    def update_streak(self, user_id: str, consecutive_days: int, best_streak: int) -> bool:
        """
        Обновляет серию дней подряд.
        
        Вызывается при ежедневном входе.

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
        
        Используется для выдачи награды за уровни.

        Args:
            user_id: ID пользователя
            delta: На сколько изменить (+1 = +1 слот, -1 = -1 слот)

        Returns:
            True при успехе
        """
        return self.db.execute_update("""
            UPDATE player_profiles SET max_plants_slots = max_plants_slots + ? 
            WHERE user_id = ?
        """, (delta, user_id))

    def update_current_plants_count(self, user_id: str, delta: int) -> bool:
        """
        Изменяет количество текущих растений.
        
        Вызывается при посадке (+1) и при смерти растения (-1).

        Args:
            user_id: ID пользователя
            delta: На сколько изменить (+1 или -1)

        Returns:
            True при успехе
        """
        return self.db.execute_update("""
            UPDATE player_profiles SET current_plants_count = current_plants_count + ? 
            WHERE user_id = ?
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
            UPDATE player_profiles SET {stat_name} = {stat_name} + ? 
            WHERE user_id = ?
        """, (delta, user_id))

    # ============================================================
    # ДИЗАЙНЫ (работа с JSON полями)
    # ============================================================

    def get_unlocked_pots(self, user_id: str) -> List[str]:
        """
        Получает список открытых горшков пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Список ID дизайнов горшков (например, ['standard', 'design_pot_1'])
        """
        profile = self.get_profile(user_id)
        if not profile:
            return ["standard"]
        
        unlocked = profile.get('unlocked_pots', '["standard"]')
        return json.loads(unlocked) if isinstance(unlocked, str) else unlocked

    def unlock_pot(self, user_id: str, pot_id: str) -> bool:
        """
        Открывает новый дизайн горшка для пользователя.
        
        Используется как награда за выполнение заданий уровня.

        Args:
            user_id: ID пользователя
            pot_id: ID дизайна горшка (из таблицы designs)

        Returns:
            True при успехе (даже если горшок уже открыт)
        """
        unlocked = self.get_unlocked_pots(user_id)
        
        if pot_id in unlocked:
            return True  # Уже открыт
        
        unlocked.append(pot_id)
        return self.db.execute_update("""
            UPDATE player_profiles SET unlocked_pots = ? WHERE user_id = ?
        """, (json.dumps(unlocked), user_id))

    def get_unlocked_watering_cans(self, user_id: str) -> List[str]:
        """
        Получает список открытых леек пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Список ID дизайнов леек
        """
        profile = self.get_profile(user_id)
        if not profile:
            return ["standard"]
        
        unlocked = profile.get('unlocked_watering_cans', '["standard"]')
        return json.loads(unlocked) if isinstance(unlocked, str) else unlocked

    def unlock_watering_can(self, user_id: str, can_id: str) -> bool:
        """
        Открывает новый дизайн лейки для пользователя.

        Args:
            user_id: ID пользователя
            can_id: ID дизайна лейки

        Returns:
            True при успехе
        """
        unlocked = self.get_unlocked_watering_cans(user_id)
        
        if can_id in unlocked:
            return True
        
        unlocked.append(can_id)
        return self.db.execute_update("""
            UPDATE player_profiles SET unlocked_watering_cans = ? WHERE user_id = ?
        """, (json.dumps(unlocked), user_id))

    def change_pot(self, user_id: str, pot_id: str) -> bool:
        """
        Сменить текущий горшок.

        Args:
            user_id: ID пользователя
            pot_id: ID дизайна горшка (должен быть в unlocked_pots)

        Returns:
            True при успехе
        """
        return self.update("player_profiles", "user_id", user_id, {
            "current_pot": pot_id
        })

    def change_watering_can(self, user_id: str, can_id: str) -> bool:
        """
        Сменить текущую лейку.

        Args:
            user_id: ID пользователя
            can_id: ID дизайна лейки

        Returns:
            True при успехе
        """
        return self.update("player_profiles", "user_id", user_id, {
            "current_watering_can": can_id
        })