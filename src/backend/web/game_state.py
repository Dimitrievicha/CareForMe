"""
API для синхронизации состояния игры между браузерами
Префикс: /api/game
"""

from flask import Blueprint, request, jsonify, g
from database_full.repository.user_repository import UserRepository
from web.auth import login_required_api
import json
from datetime import datetime

game_bp = Blueprint('game', __name__)


@game_bp.route('/save', methods=['POST'])
@login_required_api
def save_game_state():
    """
    Сохранить состояние сада на сервер

    POST /api/game/save
    Body: { "slotData": {...}, "currentLevel": int, "achievements": {...}, ... }
    """
    user_id = g.user_id
    data = request.get_json()

    if not data:
        return jsonify({'success': False, 'error': 'Нет данных'}), 400

    repo = UserRepository()

    # Сохраняем состояние в JSON поле (нужно добавить колонку в таблицу users или создать новую)
    success = repo.db.execute_update("""
        INSERT OR REPLACE INTO game_states (user_id, slot_data, current_level, achievements, updated_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        user_id,
        json.dumps(data.get('slotData', {})),
        data.get('currentLevel', 1),
        json.dumps(data.get('achievements', {})),
        datetime.now().isoformat()
    ))

    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Ошибка сохранения'}), 500


@game_bp.route('/load', methods=['GET'])
@login_required_api
def load_game_state():
    """
    Загрузить состояние сада с сервера

    GET /api/game/load
    """
    user_id = g.user_id

    repo = UserRepository()
    result = repo.db.execute_query("""
        SELECT slot_data, current_level, achievements FROM game_states 
        WHERE user_id = ?
    """, (user_id,))

    if result and len(result) > 0:
        return jsonify({
            'success': True,
            'slotData': json.loads(result[0]['slot_data']) if result[0]['slot_data'] else {},
            'currentLevel': result[0]['current_level'],
            'achievements': json.loads(result[0]['achievements']) if result[0]['achievements'] else {}
        })
    else:
        return jsonify({
            'success': True,
            'slotData': {},
            'currentLevel': 1,
            'achievements': {}
        })