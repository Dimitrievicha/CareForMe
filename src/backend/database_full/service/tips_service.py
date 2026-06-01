"""
Сервис для работы с советами
"""

from typing import List, Dict, Any, Optional
from ..repository.tips_repository import TipsRepository
import json


class TipsService:
    """Сервис для бизнес-логики советов."""

    def __init__(self):
        self._repo = TipsRepository()

    def get_all_tips(self) -> List[Dict[str, Any]]:
        """Получить все советы с форматированием."""
        rows = self._repo.get_all_tips()
        return [
            {
                'id': r['id'],
                'tip_type': r['tip_type'],
                'title': r['title'],
                'message': r['message'],
                'is_positive': bool(r['is_positive'])
            }
            for r in rows
        ] if rows else []

    def get_positive_tips(self) -> List[Dict[str, Any]]:
        """Получить позитивные советы."""
        rows = self._repo.get_positive_tips()
        return [
            {
                'id': r['id'],
                'tip_type': r['tip_type'],
                'title': r['title'],
                'message': r['message']
            }
            for r in rows
        ] if rows else []

    def get_tip_by_type(self, tip_type: str) -> Dict[str, Any]:
        """Получить совет по типу."""
        rows = self._repo.get_tip_by_type(tip_type)
        if not rows:
            return {
                'id': None,
                'title': 'Совет',
                'message': 'Присматривай за цветком — он тебя порадует! 🌿',
                'is_positive': True
            }
        r = rows[0]
        return {
            'id': r['id'],
            'title': r['title'],
            'message': r['message'],
            'is_positive': bool(r['is_positive'])
        }

    def get_plant_tips(self, species_id: int) -> Optional[Dict[str, Any]]:
        """Получить советы для конкретного вида растения."""
        rows = self._repo.get_plant_template(species_id)
        if not rows:
            return None

        r = rows[0]
        species_name = r['species_name']
        raw_tips = r['tips'] or '[]'
        raw_symptoms = r['symptoms'] or ''

        # Парсинг советов
        try:
            tips = json.loads(raw_tips)
        except (json.JSONDecodeError, TypeError):
            tips = [t.strip() for t in str(raw_tips).split('|') if t.strip()]

        # Парсинг симптомов
        symptoms = []
        for entry in str(raw_symptoms).split('|'):
            entry = entry.strip()
            if not entry:
                continue
            if '->' in entry:
                left, advice = entry.split('->', 1)
                if ':' in left:
                    symptom, cause = left.split(':', 1)
                else:
                    symptom, cause = left, ''
                symptoms.append({
                    'symptom': symptom.strip(),
                    'cause': cause.strip(),
                    'advice': advice.strip()
                })
            else:
                symptoms.append({'symptom': entry, 'cause': '', 'advice': ''})

        return {
            'species_name': species_name,
            'tips': tips,
            'symptoms': symptoms
        }


# Глобальный экземпляр
tips_service = TipsService()