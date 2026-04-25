"""
Репозиторий для работы с уровневыми заданиями.

Содержит методы для работы с таблицами:
    - level_requirements: определения заданий для уровней (справочник)
    - user_level_progress: прогресс пользователя по заданиям

"""

from typing import Optional, List, Dict, Any
from .base_repository import BaseRepository


class LevelQuestRepository(BaseRepository):
    """
    Репозиторий для таблиц level_requirements и user_level_progress.

    Обрабатывает все операции с уровневыми заданиями:
        - Получение заданий для уровней
        - Отслеживание прогресса пользователя
        - Обновление выполнения заданий
        - Выдача наград
    """

    def get_level_quests(self, level: int) -> Optional[Dict[str, Any]]:
        """
        Получает задания для указанного уровня.

        Args:
            level: Номер уровня (1-5)

        Returns:
            Словарь с данными заданий уровня или None

        Returns структура:
            {
                "level": 1,
                "quest1_type": "plant_first",
                "quest1_target": 1,
                "quest1_description": "Посадить первое растение",
                "quest2_type": "water_count",
                "quest2_target": 1,
                "quest2_description": "Полить растение 1 раз",
                "quest3_type": "read_tip",
                "quest3_target": 1,
                "quest3_description": "Прочитать 1 совет",
                "reward_type": "new_pot",
                "reward_value": "design_pot_1",
                "reward_description": "1 новый дизайнерский горшок"
            }

        """
        result = self.db.execute_query(
            "SELECT * FROM level_requirements WHERE level = ?",
            (level,)
        )
        return result[0] if result else None

    def get_all_level_quests(self) -> List[Dict[str, Any]]:
        """
        Получает задания для всех уровней.

        Returns:
            Список заданий для уровней 1-5

        """
        return self.db.execute_query("""
            SELECT * FROM level_requirements 
            ORDER BY level
        """)

    def get_max_level(self) -> int:
        """
        Получает максимальный уровень в системе.

        Returns:
            Максимальный уровень (5)
        """
        result = self.db.execute_query("SELECT MAX(level) as max_level FROM level_requirements")
        return result[0]['max_level'] if result else 5

    def get_reward_by_level(self, level: int) -> Optional[Dict[str, Any]]:
        """
        Получает награду за завершение уровня.

        Args:
            level: Номер уровня

        Returns:
            Словарь с информацией о награде

        Returns структура:
            {
                "reward_type": "new_pot",
                "reward_value": "design_pot_1",
                "reward_description": "1 новый дизайнерский горшок"
            }
        """
        result = self.db.execute_query("""
            SELECT reward_type, reward_value, reward_description
            FROM level_requirements 
            WHERE level = ?
        """, (level,))
        return result[0] if result else None

    def get_user_progress(self, user_id: str, level: int) -> Optional[Dict[str, Any]]:
        """
        Получает прогресс пользователя по заданиям уровня.

        Args:
            user_id: ID пользователя
            level: Номер уровня

        Returns:
            Словарь с прогрессом или None если нет записи

        Returns структура:
            {
                "user_id": "uuid",
                "level": 1,
                "quest1_progress": 1,
                "quest1_completed": 1,
                "quest2_progress": 3,
                "quest2_completed": 1,
                "quest3_progress": 0,
                "quest3_completed": 0,
                "level_completed": 0,
                "reward_claimed": 0,
                "completed_at": None
            }
        """
        result = self.db.execute_query("""
            SELECT * FROM user_level_progress 
            WHERE user_id = ? AND level = ?
        """, (user_id, level))
        return result[0] if result else None

    def get_all_user_progress(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Получает прогресс пользователя по всем уровням.

        Args:
            user_id: ID пользователя

        Returns:
            Список прогресса по всем уровням

        """
        return self.db.execute_query("""
            SELECT * FROM user_level_progress 
            WHERE user_id = ? 
            ORDER BY level
        """, (user_id,))

    def init_user_progress(self, user_id: str, level: int) -> bool:
        """
        Инициализирует прогресс для нового уровня.

        Args:
            user_id: ID пользователя
            level: Номер уровня

        Returns:
            True при успехе

        """
        return self.db.execute_update("""
            INSERT INTO user_level_progress (user_id, level, quest1_progress, quest2_progress, quest3_progress)
            VALUES (?, ?, 0, 0, 0)
        """, (user_id, level))

    def update_quest_progress(self, user_id: str, level: int,
                              quest_number: int, progress: int) -> bool:
        """
        Обновляет прогресс конкретного задания.

        Args:
            user_id: ID пользователя
            level: Номер уровня
            quest_number: Номер задания (1, 2, 3)
            progress: Новое значение прогресса

        Returns:
            True при успехе

        """
        col_name = f"quest{quest_number}_progress"
        return self.db.execute_update(f"""
            UPDATE user_level_progress 
            SET {col_name} = ? 
            WHERE user_id = ? AND level = ?
        """, (progress, user_id, level))

    def complete_quest(self, user_id: str, level: int, quest_number: int) -> bool:
        """
        Отмечает задание как выполненное.

        Args:
            user_id: ID пользователя
            level: Номер уровня
            quest_number: Номер задания (1, 2, 3)

        Returns:
            True при успехе
        """
        col_name = f"quest{quest_number}_completed"
        return self.db.execute_update(f"""
            UPDATE user_level_progress 
            SET {col_name} = 1 
            WHERE user_id = ? AND level = ?
        """, (user_id, level))

    def complete_level(self, user_id: str, level: int) -> bool:
        """
        Отмечает уровень как полностью выполненный.

        Args:
            user_id: ID пользователя
            level: Номер уровня

        Returns:
            True при успехе
        """
        return self.db.execute_update("""
            UPDATE user_level_progress 
            SET level_completed = 1, completed_at = CURRENT_DATE
            WHERE user_id = ? AND level = ?
        """, (user_id, level))

    def claim_reward(self, user_id: str, level: int) -> bool:
        """
        Отмечает, что награда за уровень получена.

        Args:
            user_id: ID пользователя
            level: Номер уровня

        Returns:
            True при успехе
        """
        return self.db.execute_update("""
            UPDATE user_level_progress 
            SET reward_claimed = 1 
            WHERE user_id = ? AND level = ?
        """, (user_id, level))

    def is_level_completed(self, user_id: str, level: int) -> bool:
        """
        Проверяет, выполнен ли уровень пользователем.

        Args:
            user_id: ID пользователя
            level: Номер уровня

        Returns:
            True если уровень выполнен
        """
        result = self.db.execute_query("""
            SELECT level_completed FROM user_level_progress 
            WHERE user_id = ? AND level = ?
        """, (user_id, level))
        return result[0]['level_completed'] == 1 if result else False

    def get_current_level_progress(self, user_id: str, current_level: int) -> Dict[str, Any]:
        """
        Получает прогресс по текущему уровню пользователя.

        Args:
            user_id: ID пользователя
            current_level: Текущий уровень пользователя

        Returns:
            Словарь с прогрессом всех заданий текущего уровня

        Returns структура:
            {
                "level": 2,
                "quests": [
                    {"number": 1, "progress": 1, "completed": True, "target": 1, "description": "..."},
                    {"number": 2, "progress": 3, "completed": True, "target": 3, "description": "..."},
                    {"number": 3, "progress": 0, "completed": False, "target": 5, "description": "..."}
                ],
                "all_completed": False
            }
        """
        quests_def = self.get_level_quests(current_level)
        if not quests_def:
            return {"error": f"Задания для уровня {current_level} не найдены"}

        progress = self.get_user_progress(user_id, current_level)
        if not progress:
            self.init_user_progress(user_id, current_level)
            progress = self.get_user_progress(user_id, current_level)

        result_quests = []
        all_completed = True

        for i in range(1, 4):
            quest_type = quests_def.get(f'quest{i}_type')
            if quest_type is None:
                continue

            target = quests_def.get(f'quest{i}_target')
            description = quests_def.get(f'quest{i}_description')
            prog = progress.get(f'quest{i}_progress', 0)
            completed = progress.get(f'quest{i}_completed', False)

            result_quests.append({
                "number": i,
                "type": quest_type,
                "progress": prog,
                "target": target,
                "completed": completed,
                "description": description
            })

            if not completed:
                all_completed = False

        return {
            "level": current_level,
            "quests": result_quests,
            "all_completed": all_completed,
            "reward_claimed": progress.get('reward_claimed', False)
        }


# Глобальный экземпляр
level_quest_repo = LevelQuestRepository()