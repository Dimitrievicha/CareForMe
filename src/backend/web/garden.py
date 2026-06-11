"""
API маршруты для сада и растений
"""

from flask import Blueprint, request, jsonify, session
from database_full.interface.flower_interface import flower_interface
from database_full.interface.user_interface import user_interface
from database_full.interface.level_quest_interface import level_quest_interface
from datetime import datetime
from database_full.interface.challenge_interface import challenge_interface

garden_bp = Blueprint('garden', __name__)


@garden_bp.route('/', methods=['GET'])
def get_garden():
    """
    Получить все растения пользователя (сад)

    GET /api/garden/
    Query params: only_alive (true/false)

    Returns: {
        "success": bool,
        "garden": [
            {
                "id": str,
                "custom_name": str,
                "species_id": int,
                "species_name": str,
                "health_status": str,      # healthy/wilting/dying/dead
                "growth_stage": str,       # seed/seedling/growing/mature/flowering
                "growth_progress": float,  # 0-100
                "is_alive": bool,
                "last_watered": str,       # дата последнего полива
                "days_since_watered": int  # дней без полива
            }
        ]
    }
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401

    only_alive = request.args.get('only_alive', 'true').lower() == 'true'
    plants = flower_interface.get_my_garden(user_id, only_alive=only_alive)

    # Добавляем информацию о днях без полива
    today = datetime.now().date()
    for plant in plants:
        if plant.get('last_watered'):
            last_watered = datetime.fromisoformat(plant['last_watered']).date()
            plant['days_since_watered'] = (today - last_watered).days
        else:
            plant['days_since_watered'] = 0

    return jsonify({'success': True, 'garden': plants})


@garden_bp.route('/stats', methods=['GET'])
def get_stats():
    """
    Получить статистику пользователя для отображения на главном экране

    GET /api/garden/stats

    Returns: {
        "success": bool,
        "level": int,
        "streak": int,              # серия дней
        "best_streak": int,
        "current_plants": int,
        "max_slots": int,
        "total_waterings": int,
        "total_plants": int,
        "total_mistakes": int
    }
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401

    stats = user_interface.get_stats(user_id)
    slots = user_interface.get_plant_slots_info(user_id)
    streak = user_interface.get_streak_info(user_id)

    return jsonify({
        'success': True,
        'level': stats.get('level', 1),
        'streak': streak.get('consecutive_days', 0),
        'best_streak': streak.get('best_streak', 0),
        'current_plants': slots.get('current', 0),
        'max_slots': slots.get('max', 1),
        'total_waterings': stats.get('total_waterings', 0),
        'total_plants': stats.get('total_plants_grown', 0),
        'total_mistakes': stats.get('total_mistakes', 0)
    })


@garden_bp.route('/plant', methods=['POST'])
def plant():
    """
    Посадить новое растение

    POST /api/garden/plant
    Body: { "species_id": int, "custom_name": str (опционально) }

    Returns: {
        "success": bool,
        "plant": {
            "plant_id": str,
            "plant_name": str,
            "species_name": str
        },
        "quest_update": {           # обновление заданий (если есть)
            "quest_completed": int,   # номер выполненного задания
            "all_completed": bool
        },
        "error": str
    }
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401

    data = request.get_json()
    species_id = data.get('species_id')
    custom_name = data.get('custom_name')

    # Проверка наличия свободного слота
    if not user_interface.has_free_slot(user_id):
        return jsonify({'success': False, 'error': 'Нет свободных слотов'}), 400

    # Посадка
    result = flower_interface.plant_flower(user_id, species_id, custom_name)

    if not result['success']:
        return jsonify(result), 400

    # Проверка заданий после посадки
    quest_check = level_quest_interface.trigger_check(user_id, 'plant')

    response = {
        'success': True,
        'plant': {
            'plant_id': result['plant_id'],
            'plant_name': result['plant_name'],
            'species_name': result['species_name']
        }
    }

    # Добавляем информацию о выполнении заданий
    if quest_check.get('quests_completed'):
        response['quest_update'] = {
            'quest_completed': quest_check['quests_completed'],
            'all_completed': quest_check.get('leveled_up', False)
        }

    if quest_check.get('leveled_up'):
        response['level_up'] = {
            'new_level': quest_check['new_level'],
            'reward': quest_check.get('reward')
        }

    return jsonify(response)


@garden_bp.route('/water/<plant_id>', methods=['POST'])
def water(plant_id):
    """
    Полить растение

    POST /api/garden/water/{plant_id}

    Returns: {
        "success": bool,
        "message": str,
        "warning": str,              # предупреждение о переливе
        "plant_status": {           # обновленное состояние растения
            "health": str,
            "growth_progress": float
        },
        "achievement": {            # если получено новое достижение
            "name": str,
            "description": str
        },
        "quest_update": {           # обновление заданий
            "quest_completed": int,
            "all_completed": bool
        },
        "level_up": {               # если повышение уровня
            "new_level": int,
            "reward": dict
        },
        "error": str
    }
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401

    # Полив
    result = flower_interface.water_flower(plant_id, user_id)

    if not result['success']:
        return jsonify(result), 400

    response = {
        'success': True,
        'message': result.get('message', 'Растение полито!')
    }

    if result.get('warning'):
        response['warning'] = result['warning']

    # Получаем обновленное состояние растения
    plant = flower_interface.get_plant_details(plant_id, user_id)
    if plant:
        response['plant_status'] = {
            'health': plant.get('health_status'),
            'growth_stage': plant.get('growth_stage'),
            'growth_progress': plant.get('growth_progress', 0)
        }

    # Проверка заданий после полива
    quest_check = level_quest_interface.trigger_check(user_id, 'water')

    if quest_check.get('quests_completed'):
        response['quest_update'] = {
            'quest_completed': quest_check['quests_completed'],
            'all_completed': quest_check.get('leveled_up', False)
        }

    # Проверка достижений
    achievements = challenge_interface.check_all_achievements(user_id)
    if achievements:
        response['achievement'] = {
            'name': achievements[0].get('name'),
            'description': achievements[0].get('description')
        }

    if quest_check.get('leveled_up'):
        response['level_up'] = {
            'new_level': quest_check['new_level'],
            'reward': quest_check.get('reward')
        }

    return jsonify(response)


@garden_bp.route('/check_all', methods=['POST'])
def check_all():
    """
    Проверить все растения (рост, здоровье, смерть)
    Вызывается периодически из фронтенда

    POST /api/garden/check_all

    Returns: {
        "success": bool,
        "updates": [                # список изменений
            {
                "plant_id": str,
                "plant_name": str,
                "health_status": str,
                "growth_stage": str,
                "is_dead": bool,
                "warning": str       # совет от игры
            }
        ],
        "new_achievements": [...],  # новые достижения
        "quest_updates": {...}      # обновления заданий
    }
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401

    plants = flower_interface.get_my_garden(user_id, only_alive=True)
    updates = []

    for plant in plants:
        plant_id = plant['id']

        # Проверка здоровья
        health = flower_interface.check_health(plant_id, user_id)

        # Обновление роста
        growth = flower_interface.update_growth(plant_id, user_id)

        # Проверка смерти
        death = flower_interface.check_death(plant_id, user_id)

        if health.get('warning') or growth.get('stage_changed') or death.get('is_dead'):
            updates.append({
                'plant_id': plant_id,
                'plant_name': plant.get('custom_name'),
                'health_status': health.get('health_status'),
                'growth_stage': growth.get('new_stage') if growth.get('stage_changed') else plant.get('growth_stage'),
                'growth_progress': growth.get('new_progress'),
                'is_dead': death.get('is_dead', False),
                'warning': health.get('warning')
            })

    # Проверка достижений
    new_achievements = challenge_interface.check_all_achievements(user_id)

    # Проверка заданий (например, вылечить растение)
    quest_check = level_quest_interface.trigger_check(user_id, 'heal')

    return jsonify({
        'success': True,
        'updates': updates,
        'new_achievements': new_achievements,
        'quest_update': {
            'quest_completed': quest_check.get('quests_completed'),
            'all_completed': quest_check.get('leveled_up', False)
        } if quest_check.get('quests_completed') else None
    })


@garden_bp.route('/available_plants', methods=['GET'])
def get_available_plants():
    """
    Получить список доступных для посадки растений (для окна выбора)

    GET /api/garden/available_plants

    Returns: {
        "success": bool,
        "plants": [
            {
                "id": int,
                "name": str,
                "icon": str,
                "description": str,
                "care_tips": str
            }
        ]
    }
    """
    # Статический список, но можно загружать из БД
    plants = [
        {
            'id': 1,
            'name': 'Спатифиллум',
            'icon': '🌸',
            'description': 'Нежный и честный. Сразу скажет, если голоден.',
            'care_tips': 'Полив раз в 1-2 дня, любит рассеянный свет'
        },
        {
            'id': 2,
            'name': 'Кактус',
            'icon': '🌵',
            'description': 'Выносливый отшельник. Простит, если забудешь полить.',
            'care_tips': 'Полив раз в 7-10 дней, любит яркое солнце'
        },
        {
            'id': 3,
            'name': 'Фикус',
            'icon': '🌿',
            'description': 'Спокойный стратег. Любит стабильность.',
            'care_tips': 'Полив раз в 3-4 дня, любит яркий рассеянный свет'
        }
    ]

    return jsonify({'success': True, 'plants': plants})


@garden_bp.route('/change_pot', methods=['POST'])
def change_pot():
    """
    Сменить текущий горшок

    POST /api/garden/change_pot
    Body: { "pot_id": str }

    Returns: { "success": bool, "error": str }
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401

    data = request.get_json()
    pot_id = data.get('pot_id')

    result = user_interface.change_pot(user_id, pot_id)
    return jsonify(result)


@garden_bp.route('/change_can', methods=['POST'])
def change_can():
    """
    Сменить текущую лейку

    POST /api/garden/change_can
    Body: { "can_id": str }

    Returns: { "success": bool, "error": str }
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401

    data = request.get_json()
    can_id = data.get('can_id')

    result = user_interface.change_watering_can(user_id, can_id)
    return jsonify(result)
