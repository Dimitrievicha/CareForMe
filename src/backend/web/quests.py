"""
API маршруты для заданий и уровней
Префикс: /api/quests
"""

from flask import Blueprint, jsonify, session
from src.backend.database_full.interface.level_quest_interface import level_quest_interface
from src.backend.database_full.interface.user_interface import user_interface

quests_bp = Blueprint('quests', __name__)


@quests_bp.route('/', methods=['GET'])
def get_all_quests():
    """
    Получить все задания для всех уровней (справочник)

    GET /api/quests/

    Returns: {
        "success": bool,
        "levels": [
            {
                "level": int,
                "quests": [
                    {
                        "number": int,
                        "type": str,
                        "description": str,
                        "target": int
                    }
                ],
                "reward": {
                    "type": str,
                    "description": str
                }
            }
        ]
    }
    """
    all_quests = level_quest_interface.get_all_levels_quests()
    return jsonify({'success': True, 'levels': all_quests})


@quests_bp.route('/progress', methods=['GET'])
def get_progress():
    """
    Получить прогресс пользователя по заданиям ТЕКУЩЕГО уровня
    (для отображения на главном экране)

    GET /api/quests/progress

    Returns: {
        "success": bool,
        "level": int,
        "quests": [
            {
                "number": int,
                "type": str,
                "description": str,
                "progress": int,
                "target": int,
                "completed": bool
            }
        ],
        "all_completed": bool,
        "next_reward": {            # награда за следующий уровень
            "type": str,
            "description": str
        }
    }
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401

    current_level = user_interface.get_current_level(user_id)
    progress = level_quest_interface.get_current_level_progress(user_id)

    # Получаем информацию о следующей награде
    next_reward = None
    if current_level < 5:
        reward_info = level_quest_interface.get_reward_info(current_level + 1)
        if reward_info:
            next_reward = {
                'type': reward_info.get('reward_type'),
                'description': reward_info.get('reward_description')
            }

    return jsonify({
        'success': True,
        'level': current_level,
        'quests': progress.get('quests', []),
        'all_completed': progress.get('all_completed', False),
        'next_reward': next_reward
    })


@quests_bp.route('/level/<int:level>', methods=['GET'])
def get_level_quests(level):
    """
    Получить задания для конкретного уровня

    GET /api/quests/level/{level}

    Returns: {
        "success": bool,
        "level": int,
        "quests": [...],
        "reward": {...},
        "is_completed": bool       # выполнен ли уровень пользователем
    }
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401

    if level < 1 or level > 5:
        return jsonify({'success': False, 'error': 'Уровень должен быть от 1 до 5'}), 400

    quests_data = level_quest_interface.get_level_quests(level)
    is_completed = level_quest_interface.get_user_progress(user_id, level)

    if not quests_data:
        return jsonify({'success': False, 'error': f'Задания для уровня {level} не найдены'}), 404

    quests = []
    for i in range(1, 4):
        quest_type = quests_data.get(f'quest{i}_type')
        if quest_type:
            quests.append({
                'number': i,
                'type': quest_type,
                'description': quests_data.get(f'quest{i}_description'),
                'target': quests_data.get(f'quest{i}_target')
            })

    return jsonify({
        'success': True,
        'level': level,
        'quests': quests,
        'reward': {
            'type': quests_data.get('reward_type'),
            'value': quests_data.get('reward_value'),
            'description': quests_data.get('reward_description')
        },
        'is_completed': bool(is_completed and is_completed.get('level_completed'))
    })


@quests_bp.route('/check', methods=['POST'])
def check_quests():
    """
    Принудительно проверить выполнение заданий
    (вызывается после любых действий)

    POST /api/quests/check

    Returns: {
        "success": bool,
        "leveled_up": bool,
        "new_level": int,          # если leveled_up
        "reward": dict,            # если leveled_up
        "completed_quests": [int]  # номера только что выполненных заданий
    }
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401

    result = level_quest_interface.check_quests(user_id)

    response = {
        'success': True,
        'leveled_up': result.get('leveled_up', False),
        'completed_quests': []
    }

    if result.get('quests_completed'):
        response['completed_quests'] = [result['quests_completed']]

    if result.get('leveled_up'):
        response['new_level'] = result['new_level']
        response['reward'] = result.get('reward')

    return jsonify(response)


@quests_bp.route('/reward/<int:level>', methods=['GET'])
def get_reward(level):
    """
    Получить информацию о награде за уровень

    GET /api/quests/reward/{level}

    Returns: {
        "success": bool,
        "reward": {
            "type": str,
            "value": str,
            "description": str
        }
    }
    """
    reward = level_quest_interface.get_reward_info(level)

    if reward:
        return jsonify({
            'success': True,
            'reward': reward
        })
    else:
        return jsonify({'success': False, 'error': 'Награда не найдена'}), 404