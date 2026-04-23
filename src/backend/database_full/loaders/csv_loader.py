import csv
import logging

logger = logging.getLogger(__name__)


def load_plants_from_csv(csv_path: str) -> list:
    """Простая загрузка растений из CSV без БД (возвращает список словарей)"""
    plants = []

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Парсинг JSON полей
            tips = row.get('tips', '[]')
            if tips and not tips.startswith('['):
                tips = [t.strip() for t in tips.split('|') if t.strip()]
            else:
                tips = []

            symptoms = row.get('symptoms', '[]')
            if symptoms and not symptoms.startswith('['):
                symptoms = [s.strip() for s in symptoms.split('|') if s.strip()]
            else:
                symptoms = []

            plants.append({
                'species_id': int(row.get('species_id', 0)),
                'species_name': row.get('species_name', '').strip(),
                'nickname': row.get('nickname', '').strip(),
                'description': row.get('description', ''),
                'character_trait': row.get('character_trait', ''),
                'water_interval_min': int(row.get('water_interval_min', 0)),
                'water_interval_max': int(row.get('water_interval_max', 0)),
                'light_requirement': row.get('light_requirement', 'medium').lower(),
                'humidity_preference': row.get('humidity_preference', 'medium'),
                'watering_advice': row.get('watering_advice', ''),
                'light_advice': row.get('light_advice', ''),
                'flowering_conditions': row.get('flowering_conditions', ''),
                'temp_advice': row.get('temp_advice', ''),
                'tips': tips,
                'symptoms': symptoms,
                'sort_order': int(row.get('sort_order', 0))
            })

    return plants


def load_achievements_from_csv(csv_path: str) -> list:
    """Простая загрузка достижений из CSV без БД"""
    achievements = []

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            achievements.append({
                'name': row.get('name', '').strip(),
                'description': row.get('description', ''),
                'requirement_type': row.get('requirement_type', '').strip(),
                'target_value': int(row.get('target_value', 0)),
                'reward_coins': int(row.get('reward_coins', 50)),
                'reward_xp': int(row.get('reward_xp', 25)),
                'is_active': row.get('is_active', 'true').lower() in ['true', '1', 'yes', 'on'],
                'sort_order': int(row.get('sort_order', 0))
            })

    return achievements