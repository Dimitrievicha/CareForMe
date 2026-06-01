"""
API маршруты для профиля пользователя
Префикс: /api/user

Маршруты:
    GET  /api/user/profile           — полный профиль
    POST /api/user/tutorial_done     — отметить обучение пройденным
    GET  /api/user/streak            — серия дней входа
    POST /api/user/settings/volume   — сохранить громкость
    POST /api/user/settings/design   — сменить горшок / лейку
    GET  /api/user/designs           — доступные дизайны
"""

from flask import Blueprint, request, jsonify, session
from database_full.interface.user_interface import user_interface
from database_full.repository.user_repository import UserRepository

user_bp = Blueprint('user', __name__)


def _get_user_id():
    user_id = session.get('user_id')
    if not user_id:
        return None, jsonify({'success': False, 'error': 'Не авторизован'}), 401
    return user_id, None, None


# ── Профиль ───────────────────────────────────────────────────────────────────

@user_bp.route('/profile', methods=['GET'])
def get_profile():
    """
    Получить полный профиль текущего пользователя.

    GET /api/user/profile

    Returns: {
        "success": bool,
        "profile": {
            "username": str,
            "display_name": str,
            "current_level": int,
            "max_plants_slots": int,
            "current_plants_count": int,
            "total_plants_grown": int,
            "total_waterings": int,
            "total_mistakes": int,
            "total_deaths": int,
            "consecutive_days": int,
            "best_streak": int,
            "tutorial_completed": bool,
            "current_pot": str,
            "current_watering_can": str,
            "unlocked_pots": [str],
            "unlocked_watering_cans": [str]
        }
    }
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401

    profile = user_interface.get_profile(user_id)
    if not profile:
        return jsonify({'success': False, 'error': 'Профиль не найден'}), 404

    # Дополняем именем пользователя
    user_info = user_interface.get_user_info(user_id)
    if user_info:
        profile['username'] = user_info.get('username')

    profile['unlocked_pots'] = user_interface.get_unlocked_pots(user_id)
    profile['unlocked_watering_cans'] = user_interface.get_unlocked_watering_cans(user_id)

    return jsonify({'success': True, 'profile': profile})


# ── Обучение ──────────────────────────────────────────────────────────────────

@user_bp.route('/tutorial_done', methods=['POST'])
def tutorial_done():
    """Отметить, что пользователь прошёл обучение."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401

    success = user_interface.complete_tutorial(user_id)
    return jsonify({'success': success})

# ── Серия дней ────────────────────────────────────────────────────────────────

@user_bp.route('/streak', methods=['GET'])
def get_streak():
    """
    Получить текущую серию ежедневных входов.

    GET /api/user/streak

    Returns: {
        "success": bool,
        "consecutive_days": int,
        "best_streak": int,
        "last_entry": str    # дата в ISO-формате
    }
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401

    streak = user_interface.get_streak_info(user_id)
    profile = user_interface.get_profile(user_id)

    return jsonify({
        'success': True,
        'consecutive_days': streak.get('consecutive_days', 0),
        'best_streak': streak.get('best_streak', 0),
        'last_entry': profile.get('last_entry') if profile else None
    })


# ── Настройки: громкость ──────────────────────────────────────────────────────

@user_bp.route('/settings/volume', methods=['POST'])
def set_volume():
    """
    Сохранить настройку громкости (хранится на фронте, сервер только принимает).

    POST /api/user/settings/volume
    Body: { "volume": int }   # 0–100

    Returns: { "success": bool, "volume": int }
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401

    data = request.get_json() or {}
    volume = data.get('volume', 50)

    try:
        volume = max(0, min(100, int(volume)))
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'volume должен быть числом 0–100'}), 400

    # При необходимости можно сохранять в отдельную таблицу settings
    return jsonify({'success': True, 'volume': volume})


# ── Настройки: смена дизайна ──────────────────────────────────────────────────

@user_bp.route('/settings/design', methods=['POST'])
def set_design():
    """
    Сменить горшок или лейку.

    POST /api/user/settings/design
    Body: {
        "type": "pot" | "watering_can",
        "design_id": str
    }

    Returns: {
        "success": bool,
        "current_pot": str,
        "current_watering_can": str,
        "error": str
    }
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401

    data = request.get_json() or {}
    design_type = data.get('type')
    design_id = data.get('design_id', '').strip()

    if design_type not in ('pot', 'watering_can'):
        return jsonify({'success': False, 'error': 'type должен быть pot или watering_can'}), 400

    if not design_id:
        return jsonify({'success': False, 'error': 'Укажите design_id'}), 400

    if design_type == 'pot':
        result = user_interface.change_pot(user_id, design_id)
    else:
        result = user_interface.change_watering_can(user_id, design_id)

    if not result.get('success'):
        return jsonify(result), 400

    # Возвращаем актуальные дизайны
    designs = user_interface.get_current_designs(user_id)
    return jsonify({
        'success': True,
        'current_pot': designs.get('pot'),
        'current_watering_can': designs.get('watering_can')
    })


# ── Доступные дизайны ─────────────────────────────────────────────────────────
@user_bp.route('/designs', methods=['GET'])
def get_designs():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401

    designs = user_interface.get_current_designs(user_id)
    unlocked_pots = user_interface.get_unlocked_pots(user_id)
    unlocked_cans = user_interface.get_unlocked_watering_cans(user_id)

    profile = user_interface.get_profile(user_id)
    user_level = profile.get('current_level', 1) if profile else 1

    # Горшок 2 разблокируется на 2 уровне, Горшок 3 на 5 уровне
    all_pots = [
        {'id': '1', 'name': 'Горшок 1', 'image': '/images/pot/горшок1.png', 'unlock_level': 1},
        {'id': '2', 'name': 'Горшок 2', 'image': '/images/pot/горшок2.png', 'unlock_level': 2},
        {'id': '3', 'name': 'Горшок 3', 'image': '/images/pot/горшок3.png', 'unlock_level': 5},
    ]

    # Кактус должен разблокироваться на 2 уровне
    all_cans = [
        {'id': '1', 'name': 'Лейка', 'image': '/images/water can/лейка.png', 'unlock_level': 1},
        {'id': '2', 'name': 'Лейка 2', 'image': '/images/water can/лейка2.png', 'unlock_level': 3},
    ]

    return jsonify({
        'success': True,
        'current': designs,
        'unlocked_pots': unlocked_pots,
        'unlocked_cans': unlocked_cans,
        'user_level': user_level,
        'all_pots': all_pots,
        'all_cans': all_cans
    })
