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
    """Полить растение в слоте — игровая логика на сервере."""
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
    """Посадить растение в слот — игровая логика на сервере."""
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
    return jsonify({
        'success': True,
        'level': current_level,
        'quests': progress.get('quests', []),
        'allCompleted': progress.get('all_completed', False),
    })


@game_bp.route('/dev/level_up', methods=['POST'])
@login_required_api
def dev_level_up():
    """DEV: Повышение уровня с синхронизацией БД."""
    user_id = g.user_id

    from database_full.service.user_service import user_service
    from database_full.interface.level_quest_interface import level_quest_interface
    from database_full.interface.challenge_interface import challenge_interface

    profile = user_service.get_profile(user_id)
    if not profile:
        return jsonify({'success': False, 'error': 'Пользователь не найден'})

    current_level = profile.get('current_level', 1)

    if current_level >= 6:
        user_service.update_level(user_id, 1)
        from database_full.repository.level_quest_repository import level_quest_repo
        level_quest_repo.db.execute_update(
            "DELETE FROM user_level_progress WHERE user_id = ?",
            (user_id,)
        )
        level_quest_repo.init_user_progress(user_id, 1)
        new_level = 1
        is_reset = True
    else:
        new_level = current_level + 1
        user_service.update_level(user_id, new_level)
        is_reset = False

    # Проверяем достижения после изменения уровня
    new_achievements = challenge_interface.check_all_achievements(user_id)

    progress = level_quest_interface.get_current_level_progress(user_id)

    return jsonify({
        'success': True,
        'newLevel': new_level,
        'isReset': is_reset,
        'quests': progress.get('quests', []),
        'allCompleted': progress.get('all_completed', False),
        'newAchievements': new_achievements
    })


@game_bp.route('/dev/update_plant', methods=['POST'])
@login_required_api
def dev_update_plant():
    """DEV: Принудительное изменение состояния растения."""
    user_id = g.user_id
    data = request.get_json() or {}
    slot_name = data.get('slotName')
    update_data = data.get('updateData', {})

    if not slot_name:
        return jsonify({'success': False, 'error': 'Не указан slotName'}), 400

    # Загружаем текущее состояние
    bundle = game_interface._room._load_bundle(user_id)
    slot = bundle["slotData"].get(slot_name)

    if not slot or not slot.get('plant'):
        return jsonify({'success': False, 'error': 'Растение не найдено'}), 404

    # Применяем изменения
    if 'stage' in update_data:
        slot['stage'] = update_data['stage']

    if 'hasDisease' in update_data:
        slot['hasDisease'] = update_data['hasDisease']

    if 'disease' in update_data:
        slot['disease'] = update_data['disease']

    if 'diseaseType' in update_data:
        slot['diseaseType'] = update_data['diseaseType']

    if 'diseaseSource' in update_data:
        slot['diseaseSource'] = update_data['diseaseSource']

    if 'hadMistakes' in update_data:
        slot['hadMistakes'] = update_data['hadMistakes']

    # Сохраняем
    game_interface._room._save_bundle(user_id, bundle)

    return jsonify({'success': True, 'slotData': slot})


@game_bp.route('/dev/apply_state', methods=['POST'])
@login_required_api
def dev_apply_state():
    """DEV: Принудительно применить состояние к растению в слоте."""
    user_id = g.user_id
    data = request.get_json()
    slot_name = data.get('slotName')
    state = data.get('state')

    if not slot_name or not state:
        return jsonify({'success': False, 'error': 'Не указаны slotName или state'}), 400

    # Загружаем текущее состояние
    from database_full.service.room_game_service import room_game_service
    bundle = room_game_service._load_bundle(user_id)
    slot = bundle["slotData"].get(slot_name)

    if not slot or not slot.get('plant'):
        return jsonify({'success': False, 'error': 'Растение не найдено'}), 404

    species_id = room_game_service._resolve_species_id(slot.get('plant'))

    # Применяем состояние
    if state == 'sprout':
        slot['stage'] = 1
        slot['hasDisease'] = False
        slot['disease'] = None
        slot['diseaseType'] = None
        slot['diseaseSource'] = None
    elif state == 'healthy':
        slot['stage'] = 2
        slot['hasDisease'] = False
        slot['disease'] = None
        slot['diseaseType'] = None
        slot['diseaseSource'] = None
    elif state == 'dead':
        slot['stage'] = 2
        slot['hasDisease'] = True
        slot['disease'] = '__dead__'
        slot['diseaseType'] = 'dead'
        slot['diseaseSource'] = 'dev'
    elif state.startswith('disease:'):
        disease_type = state.split(':')[1]
        diseases = room_game_service.PLANT_DISEASES.get(species_id, {})
        disease_msg = diseases.get(disease_type)
        if disease_msg:
            slot['stage'] = max(slot.get('stage', 1), 1)
            slot['hasDisease'] = True
            slot['disease'] = disease_msg
            slot['diseaseType'] = disease_type
            slot['diseaseSource'] = 'dev'
            slot['diseaseStartTime'] = int(datetime.now().timestamp() * 1000)

    # Сохраняем
    room_game_service._save_bundle(user_id, bundle)

    return jsonify({
        'success': True,
        'slotName': slot_name,
        'slotData': slot
    })