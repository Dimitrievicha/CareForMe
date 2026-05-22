"""
API маршруты для работы с отдельным растением
Префикс: /api/plants

Маршруты:
    GET  /api/plants/<plant_id>          — детали растения
    POST /api/plants/<plant_id>/light    — сменить уровень освещения
    POST /api/plants/<plant_id>/location — сменить место (комната/балкон/…)
    POST /api/plants/<plant_id>/revive   — посадить новое после гибели
    GET  /api/plants/catalog             — справочник всех видов
"""

from flask import Blueprint, request, jsonify, session
from database_full.interface.flower_interface import flower_interface
from database_full.interface.level_quest_interface import level_quest_interface

plants_bp = Blueprint('plants', __name__)


def _get_user_id():
    """Вспомогательная: вернуть user_id из сессии или None."""
    return session.get('user_id')


# ── Детали растения ───────────────────────────────────────────────────────────

@plants_bp.route('/<plant_id>', methods=['GET'])
def get_plant(plant_id):
    """
    Получить подробную информацию об одном растении.

    GET /api/plants/{plant_id}

    Returns: {
        "success": bool,
        "plant": {
            "id": str,
            "custom_name": str,
            "species_id": int,
            "species_name": str,
            "nickname": str,
            "description": str,
            "character_trait": str,
            "health_status": str,        # healthy/wilting/overwatered/dying/dead
            "growth_stage": str,         # seed/seedling/growing/mature/flowering
            "growth_progress": float,    # 0–100
            "current_light_level": str,  # low/medium/high
            "location": str,
            "last_watered": str,
            "days_since_watered": int,
            "is_alive": bool,
            "times_flowered": int,
            "water_interval_min": int,
            "water_interval_max": int,
            "tips": [str],
            "symptoms": [{
                "symptom": str,
                "cause": str,
                "advice": str
            }]
        }
    }
    """
    user_id = _get_user_id()
    if not user_id:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401

    plant = flower_interface.get_plant_details(plant_id, user_id)

    if not plant:
        return jsonify({'success': False, 'error': 'Растение не найдено'}), 404

    # Считаем дни без полива
    from datetime import datetime
    if plant.get('last_watered'):
        try:
            last_watered = datetime.fromisoformat(plant['last_watered']).date()
            plant['days_since_watered'] = (datetime.now().date() - last_watered).days
        except (ValueError, TypeError):
            plant['days_since_watered'] = 0
    else:
        plant['days_since_watered'] = 0

    return jsonify({'success': True, 'plant': plant})


# ── Справочник видов ──────────────────────────────────────────────────────────

@plants_bp.route('/catalog', methods=['GET'])
def get_catalog():
    """
    Получить справочник всех видов растений из БД (plant_templates).
    Используется для экрана выбора растения в обучении и при посадке.

    GET /api/plants/catalog

    Returns: {
        "success": bool,
        "plants": [
            {
                "species_id": int,
                "species_name": str,
                "nickname": str,
                "description": str,
                "character_trait": str,
                "water_interval_min": int,
                "water_interval_max": int,
                "light_requirement": str,
                "watering_advice": str,
                "light_advice": str,
                "flowering_conditions": str,
                "tips": [str],
                "symptoms": [{"symptom": str, "cause": str, "advice": str}]
            }
        ]
    }
    """
    plants = flower_interface.get_available_plants()
    return jsonify({'success': True, 'plants': plants})


# ── Смена уровня освещения ────────────────────────────────────────────────────

@plants_bp.route('/<plant_id>/light', methods=['POST'])
def set_light(plant_id):
    """
    Сменить уровень освещения для растения.

    POST /api/plants/{plant_id}/light
    Body: { "light_level": "low" | "medium" | "high" }

    Returns: {
        "success": bool,
        "health_status": str,   # новый статус после смены света
        "warning": str          # совет, если свет неподходящий
    }
    """
    user_id = _get_user_id()
    if not user_id:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401

    data = request.get_json()
    light_level = data.get('light_level')

    if light_level not in ('low', 'medium', 'high'):
        return jsonify({'success': False, 'error': 'Допустимые значения: low, medium, high'}), 400

    # Проверяем права на растение
    plant = flower_interface.get_plant_details(plant_id, user_id)
    if not plant:
        return jsonify({'success': False, 'error': 'Растение не найдено'}), 404

    # Обновляем уровень света через БД напрямую (нет отдельного метода в интерфейсе)
    from database_full.database.db_manager import get_db_manager
    db = get_db_manager()
    db.execute_update(
        "UPDATE user_plants SET current_light_level = ? WHERE id = ? AND user_id = ?",
        (light_level, plant_id, user_id)
    )

    # Перепроверяем здоровье с новым светом
    health = flower_interface.check_health(plant_id, user_id)

    return jsonify({
        'success': True,
        'health_status': health.get('health_status'),
        'warning': health.get('warning')
    })


# ── Смена локации ─────────────────────────────────────────────────────────────

@plants_bp.route('/<plant_id>/location', methods=['POST'])
def set_location(plant_id):
    """
    Переставить растение в другое место (вызывает стресс у фикуса).

    POST /api/plants/{plant_id}/location
    Body: { "location": str }   # например "windowsill", "balcony", "room", "bathroom"

    Returns: {
        "success": bool,
        "stress_warning": str | null   # предупреждение о стрессе (ficus)
    }
    """
    user_id = _get_user_id()
    if not user_id:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401

    data = request.get_json()
    location = data.get('location', '').strip()

    if not location:
        return jsonify({'success': False, 'error': 'Укажите location'}), 400

    plant = flower_interface.get_plant_details(plant_id, user_id)
    if not plant:
        return jsonify({'success': False, 'error': 'Растение не найдено'}), 404

    from database_full.database.db_manager import get_db_manager
    db = get_db_manager()
    db.execute_update(
        "UPDATE user_plants SET location = ? WHERE id = ? AND user_id = ?",
        (location, plant_id, user_id)
    )

    # Фикус (species_id=3) реагирует на переезд стрессом
    stress_warning = None
    if plant.get('species_id') == 3 and plant.get('location') != location:
        stress_warning = (
            "Фикус не любит переезды. Ближайшие 1-2 дня он может сбрасывать "
            "листья — это нормально, просто не трогай его больше."
        )

    return jsonify({'success': True, 'stress_warning': stress_warning})


# ── Возрождение (посадить новый после гибели) ─────────────────────────────────

@plants_bp.route('/<plant_id>/revive', methods=['POST'])
def revive(plant_id):
    """
    После гибели растения — посадить новый того же вида.
    Ачивки и уровень пользователя сохраняются.

    POST /api/plants/{plant_id}/revive
    Body: { "custom_name": str (опционально) }

    Returns: {
        "success": bool,
        "new_plant_id": str,
        "message": str
    }
    """
    user_id = _get_user_id()
    if not user_id:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401

    # Берём вид погибшего растения
    plant = flower_interface.get_plant_details(plant_id, user_id)
    if not plant:
        return jsonify({'success': False, 'error': 'Растение не найдено'}), 404

    if plant.get('is_alive'):
        return jsonify({'success': False, 'error': 'Растение живо — возрождение не нужно'}), 400

    data = request.get_json() or {}
    custom_name = data.get('custom_name')
    species_id = plant.get('species_id')

    # Проверяем свободный слот
    from database_full.interface.user_interface import user_interface
    if not user_interface.has_free_slot(user_id):
        return jsonify({'success': False, 'error': 'Нет свободных слотов'}), 400

    result = flower_interface.plant_flower(user_id, species_id, custom_name)
    if not result['success']:
        return jsonify(result), 400

    # Проверяем задания после посадки
    level_quest_interface.trigger_check(user_id, 'plant')

    return jsonify({
        'success': True,
        'new_plant_id': result['plant_id'],
        'message': 'Новый цветок посажен! Твои достижения и уровень никуда не делись. 🌱'
    })
