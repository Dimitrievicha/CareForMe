"""Репозиторий для работы с пользователями и профилями"""
from typing import Optional, List, Dict, Any
from .base_repository import BaseRepository


class UserRepository(BaseRepository):
    """Репозиторий для таблиц users и player_profiles"""

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Получить пользователя по ID"""
        return self.get_by_id("users", "id", user_id)

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Получить пользователя по имени"""
        result = self.db.execute_query(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        )
        return result[0] if result else None

    def create_user(self, user_id: str, username: str, password_hash: str) -> bool:
        """Создать нового пользователя"""
        return self.db.execute_update("""
            INSERT INTO users (id, username, password_hash)
            VALUES (?, ?, ?)
        """, (user_id, username, password_hash))

    def update_last_login(self, user_id: str) -> bool:
        """Обновить время последнего входа"""
        return self.db.execute_update("""
            UPDATE users SET last_login = CURRENT_TIMESTAMP, login_count = login_count + 1
            WHERE id = ?
        """, (user_id,))

    def user_exists(self, username: str) -> bool:
        """Проверить существование пользователя"""
        return self.count("users", "username = ?", (username,)) > 0

    def create_session(self, user_id: str, token: str, expires_at: str) -> bool:
        """Создать сессию"""
        return self.db.execute_update("""
            INSERT INTO sessions (user_id, token, expires_at)
            VALUES (?, ?, ?)
        """, (user_id, token, expires_at))

    def get_session_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Получить сессию по токену"""
        result = self.db.execute_query(
            "SELECT * FROM sessions WHERE token = ? AND is_revoked = 0",
            (token,)
        )
        return result[0] if result else None

    def revoke_session(self, token: str) -> bool:
        """Отозвать сессию"""
        return self.db.execute_update(
            "UPDATE sessions SET is_revoked = 1 WHERE token = ?",
            (token,)
        )

    def revoke_all_user_sessions(self, user_id: str, keep_token: str = None) -> bool:
        """Отозвать все сессии пользователя"""
        if keep_token:
            return self.db.execute_update("""
                UPDATE sessions SET is_revoked = 1 WHERE user_id = ? AND token != ?
            """, (user_id, keep_token))
        return self.db.execute_update(
            "UPDATE sessions SET is_revoked = 1 WHERE user_id = ?",
            (user_id,)
        )

    def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Получить игровой профиль"""
        result = self.db.execute_query(
            "SELECT * FROM player_profiles WHERE user_id = ?",
            (user_id,)
        )
        return result[0] if result else None

    def create_profile(self, user_id: str, display_name: str = None) -> bool:
        """Создать игровой профиль"""
        return self.db.execute_update("""
            INSERT INTO player_profiles (user_id, display_name)
            VALUES (?, ?)
        """, (user_id, display_name))

    def update_xp(self, user_id: str, new_xp: int, new_level: int) -> bool:
        """Обновить опыт и уровень"""
        return self.db.execute_update("""
            UPDATE player_profiles SET xp = ?, level = ? WHERE user_id = ?
        """, (new_xp, new_level, user_id))

    def add_coins(self, user_id: str, amount: int) -> bool:
        """Добавить монеты"""
        return self.db.execute_update("""
            UPDATE player_profiles SET coins = coins + ? WHERE user_id = ?
        """, (amount, user_id))

    def remove_coins(self, user_id: str, amount: int) -> bool:
        """Списать монеты"""
        return self.db.execute_update("""
            UPDATE player_profiles SET coins = coins - ? WHERE user_id = ? AND coins >= ?
        """, (amount, user_id, amount))

    def update_streak(self, user_id: str, consecutive_days: int, best_streak: int) -> bool:
        """Обновить серию дней"""
        return self.db.execute_update("""
            UPDATE player_profiles 
            SET last_entry = CURRENT_DATE, consecutive_days = ?, best_streak = ?
            WHERE user_id = ?
        """, (consecutive_days, best_streak, user_id))

    def update_plant_slots(self, user_id: str, delta: int) -> bool:
        """Изменить количество слотов для растений"""
        return self.db.execute_update("""
            UPDATE player_profiles SET max_plants_slots = max_plants_slots + ? WHERE user_id = ?
        """, (delta, user_id))

    def update_current_plants_count(self, user_id: str, delta: int) -> bool:
        """Изменить количество текущих растений"""
        return self.db.execute_update("""
            UPDATE player_profiles SET current_plants_count = current_plants_count + ? WHERE user_id = ?
        """, (delta, user_id))

    def increment_stat(self, user_id: str, stat_name: str, delta: int = 1) -> bool:
        """Увеличить статистику (total_plants_grown, total_waterings и т.д.)"""
        allowed_stats = ['total_plants_grown', 'total_waterings', 'total_mistakes', 'total_deaths']
        if stat_name not in allowed_stats:
            return False
        return self.db.execute_update(f"""
            UPDATE player_profiles SET {stat_name} = {stat_name} + ? WHERE user_id = ?
        """, (delta, user_id))

    def get_leaderboard(self, sort_by: str = "level", limit: int = 10) -> List[Dict[str, Any]]:
        """Получить таблицу лидеров"""
        valid_sort = ["level", "coins", "total_plants_grown", "consecutive_days"]
        if sort_by not in valid_sort:
            sort_by = "level"

        return self.db.execute_query(f"""
            SELECT u.username, p.level, p.xp, p.coins, p.total_plants_grown, 
                   p.consecutive_days, p.best_streak
            FROM player_profiles p
            JOIN users u ON p.user_id = u.id
            ORDER BY p.{sort_by} DESC
            LIMIT ?
        """, (limit,))

    def complete_tutorial(self, user_id: str) -> bool:
        """Отметить завершение туториала"""
        return self.db.execute_update("""
            UPDATE player_profiles SET tutorial_completed = 1 WHERE user_id = ?
        """, (user_id,))

