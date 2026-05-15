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
from src.backend.database_full.interface.user_interface import user_interface
from src.backend.database_full.repository.user_repository import UserRepository

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
    """
    Отметить, что пользователь прошёл обучение (шаги 1–5).

    POST /api/user/tutorial_done

    Returns: { "success": bool }
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401

    repo = UserRepository()
    success = repo.db.execute_update(
        "UPDATE player_profiles SET tutorial_completed = 1 WHERE user_id = ?",
        (user_id,)
    )
    return jsonify({'success': bool(success)})


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
    """
    Получить все доступные и разблокированные дизайны.

    GET /api/user/designs

    Returns: {
        "success": bool,
        "current": { "pot": str, "watering_can": str },
        "unlocked_pots": [str],
        "unlocked_cans": [str],
        "all_pots": [{ "id": str, "name": str, "image": str }],
        "all_cans": [{ "id": str, "name": str, "image": str }]
    }
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401

    designs = user_interface.get_current_designs(user_id)
    unlocked_pots = user_interface.get_unlocked_pots(user_id)
    unlocked_cans = user_interface.get_unlocked_watering_cans(user_id)

    # Полный справочник дизайнов (можно перенести в БД позже)
    all_pots = [
        {'id': 'standard',     'name': 'Стандартный',   'image': '/assets/pots/standard.png'},
        {'id': 'ceramic',      'name': 'Керамический',  'image': '/assets/pots/ceramic.png'},
        {'id': 'wooden',       'name': 'Деревянный',    'image': '/assets/pots/wooden.png'},
        {'id': 'golden',       'name': 'Золотой',       'image': '/assets/pots/golden.png'},
        {'id': 'design_pot_1', 'name': 'Дизайнерский 1','image': '/assets/pots/design_pot_1.png'},
        {'id': 'design_pot_2', 'name': 'Дизайнерский 2','image': '/assets/pots/design_pot_2.png'},
    ]
    all_cans = [
        {'id': 'standard',    'name': 'Стандартная',   'image': '/assets/cans/standard.png'},
        {'id': 'wooden',      'name': 'Деревянная',    'image': '/assets/cans/wooden.png'},
        {'id': 'golden',      'name': 'Золотая',       'image': '/assets/cans/golden.png'},
        {'id': 'design_can_1','name': 'Дизайнерская',  'image': '/assets/cans/design_can_1.png'},
    ]

    return jsonify({
        'success': True,
        'current': designs,
        'unlocked_pots': unlocked_pots,
        'unlocked_cans': unlocked_cans,
        'all_pots': all_pots,
        'all_cans': all_cans
    })
