"""
API для синхронизации состояния игры между браузерами
Префикс: /api/game
"""

from flask import Blueprint, request, jsonify, g
from web.auth import login_required_api
from database_full.interface.game_interface import game_interface
from database_full.interface.level_quest_interface import level_quest_interface
from database_full.interface.user_interface import user_interface
from datetime import datetime

game_bp = Blueprint('game', __name__)


@game_bp.route('/save', methods=['POST'])
@login_required_api
def save_game_state():
    """Сохранить состояние сада на сервер."""
    user_id = g.user_id
    data = request.get_json()

    if not data:
        return jsonify({'success': False, 'error': 'Нет данных'}), 400

    success = game_interface.save_state(
        user_id,
        data.get('slotData', {}),
        data.get('currentLevel', 1),
        data.get('achievements', {})
    )

    if success:
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Ошибка сохранения'}), 500


@game_bp.route('/load', methods=['GET'])
@login_required_api
def load_game_state():
    """Загрузить состояние сада с сервера."""
    user_id = g.user_id
    state = game_interface.load_state(user_id)
    return jsonify({'success': True, **state})


@game_bp.route('/water', methods=['POST'])
@login_required_api
def water_slot():
    """Полить растение DB_TESTING_REPORT.md слоте — игровая логика на сервере."""
    user_id = g.user_id
    data = request.get_json() or {}
    slot_name = data.get('slotName')

    if not slot_name:
        return jsonify({'success': False, 'error': 'Не указан slotName'}), 400

    result = game_interface.water_slot(user_id, slot_name)
    status = 200 if result.get('success') else 400
    return jsonify(result), status


@game_bp.route('/plant', methods=['POST'])
@login_required_api
def plant_in_slot():
    """Посадить растение DB_TESTING_REPORT.md слот — игровая логика на сервере."""
    user_id = g.user_id
    data = request.get_json() or {}
    slot_name = data.get('slotName')
    species_id = data.get('speciesId')

    if not slot_name or species_id is None:
        return jsonify({'success': False, 'error': 'Нужны slotName и speciesId'}), 400

    result = game_interface.plant_in_slot(user_id, slot_name, int(species_id))
    status = 200 if result.get('success') else 400
    return jsonify(result), status


@game_bp.route('/tick', methods=['POST'])
@login_required_api
def tick_game():
    """Периодическая проверка здоровья, болезней и роста на сервере."""
    user_id = g.user_id
    data = request.get_json() or {}
    slot_names = data.get('slotNames')
    result = game_interface.tick(user_id, slot_names)
    return jsonify(result)


@game_bp.route('/move', methods=['POST'])
@login_required_api
def move_slot():
    """Переместить растение между слотами с серверной проверкой локации."""
    user_id = g.user_id
    data = request.get_json() or {}
    from_slot = data.get('fromSlot')
    to_slot = data.get('toSlot')

    if not from_slot or not to_slot:
        return jsonify({'success': False, 'error': 'Нужны fromSlot и toSlot'}), 400

    result = game_interface.move_slot(user_id, from_slot, to_slot)
    status = 200 if result.get('success') else 400
    return jsonify(result), status


@game_bp.route('/read_description', methods=['POST'])
@login_required_api
def read_description():
    """Отметить прочтение описания растения для квестов."""
    user_id = g.user_id
    result = game_interface.mark_read_description(user_id)
    return jsonify(result)


@game_bp.route('/quests/progress', methods=['GET'])
@login_required_api
def get_room_quest_progress():
    """Прогресс заданий текущего уровня для экрана комнаты."""
    user_id = g.user_id
    current_level = user_interface.get_current_level(user_id)
    progress = level_quest_interface.get_current_level_progress(user_id)

    quests = []
    for q in progress.get('quests', []):
        quests.append({
            'number': q.get('number'),
            'description': q.get('description'),
            'progress': q.get('progress', 0),
            'target': q.get('target', 1),
            'completed': q.get('completed', False),  # ← ключевое поле
            'type': q.get('type')
        })

    return jsonify({
        'success': True,
        'level': current_level,
        'quests': quests,
        'allCompleted': progress.get('all_completed', False),
    })

