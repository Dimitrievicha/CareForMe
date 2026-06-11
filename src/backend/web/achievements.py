"""
API маршруты для достижений
Префикс: /api/achievements
"""

from flask import Blueprint, jsonify, request, session
from database_full.interface.challenge_interface import challenge_interface

achievements_bp = Blueprint('achievements', __name__)


@achievements_bp.route('/', methods=['GET'])
def get_achievements():
    """
    Получить все достижения с прогрессом пользователя

    GET /api/achievements/

    Returns: {
        "success": bool,
        "achievements": [
            {
                "id": str,
                "name": str,
                "description": str,
                "current_progress": int,
                "target_value": int,
                "is_completed": bool,
                "completed_at": str    # дата выполнения (если есть)
            }
        ],
        "stats": {
            "total_achievements": int,      # сколько получено
            "plants_perfect": int,          # идеальных растений
            "species_collected": int,       # видов собрано (0-3)
            "mistakes_count": int,          # всего ошибок
            "deaths_count": int             # всего смертей
        }
    }
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401

    achievements = challenge_interface.get_all_achievements(user_id)
    stats = challenge_interface.get_statistics(user_id)

    # Подсчитываем количество выполненных
    completed_count = sum(1 for a in achievements if a.get('is_completed'))

    return jsonify({
        'success': True,
        'achievements': achievements,
        'stats': {
            'total_achievements': completed_count,
            'plants_perfect': stats.get('plants_grown_to_maturity_perfect', 0),
            'species_collected': stats.get('species_collected', 0),
            'mistakes_count': stats.get('mistake_count', 0),
            'deaths_count': stats.get('death_count', 0),
            'level': stats.get('level', 1)
        }
    })


@achievements_bp.route('/check', methods=['POST'])
def check_achievements():
    """
    Принудительно проверить все достижения
    (вызывается после действий, которые могут дать ачивку)

    POST /api/achievements/check

    Returns: {
        "success": bool,
        "new_achievements": [
            {
                "name": str,
                "description": str,
                "icon": str
            }
        ]
    }
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401

    new_achievements = challenge_interface.check_all_achievements(user_id)

    # Обогащаем иконками
    achievement_icons = {
        'Заботливый родитель': '🌱',
        'Ой, всё пропало': '💀',
        'Упс..ошибка': '⚠️',
        'Коллекционер': '🌸',
        'Терпеливый садовод': '🔥',
        'Страж флоры': '🛡️'
    }

    result = []
    for ach in new_achievements:
        result.append({
            'name': ach.get('name'),
            'description': ach.get('description'),
            'icon': achievement_icons.get(ach.get('name'), '🏆')
        })

    return jsonify({
        'success': True,
        'new_achievements': result
    })


@achievements_bp.route('/event', methods=['POST'])
def record_event():
    """
    Записать игровое событие и проверить достижения.

    POST /api/achievements/event
    Body: {
        "event": "perfect_growth" | "death" | "mistake" | "species_collected",
        "plant_id": str   (опционально, для perfect_growth / death / mistake)
    }

    Returns: {
        "success": bool,
        "new_achievements": [ { "name": str, "id": str } ]
    }
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401

    data = request.get_json() or {}
    event = data.get('event')
    plant_id = data.get('plant_id', 'unknown')

    if event == 'perfect_growth':
        result = challenge_interface.record_perfect_growth(user_id, plant_id)
    elif event == 'death':
        result = challenge_interface.record_plant_death(user_id, plant_id)
    elif event == 'mistake':
        result = challenge_interface.record_mistake(user_id, plant_id, data.get('mistake_type', 'unknown'))
    elif event == 'species_collected':
        result = challenge_interface.record_species_collected(user_id)
    else:
        # Просто проверяем достижения без записи нового события
        result = {'new_achievements': challenge_interface.check_all_achievements(user_id)}

    new_achievements = result.get('new_achievements', [])
    return jsonify({'success': True, 'new_achievements': new_achievements})


@achievements_bp.route('/recent', methods=['GET'])
def get_recent_achievements():
    """
    Получить последние полученные достижения
    (для показа уведомления при входе)

    GET /api/achievements/recent

    Returns: {
        "success": bool,
        "recent": [
            {
                "name": str,
                "description": str,
                "completed_at": str
            }
        ]
    }
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401

    completed = challenge_interface.get_completed(user_id)

    # Последние 3 достижения
    recent = completed[-3:] if completed else []

    return jsonify({
        'success': True,
        'recent': recent
    })