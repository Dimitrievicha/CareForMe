"""
API для синхронизации состояния игры между браузерами
Префикс: /api/game
"""

from flask import Blueprint, request, jsonify, g
from web.auth import login_required_api
from database_full.interface.game_interface import game_interface

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
    """Загрузить состояние сада TESTING_REPORT.md сервера."""
    user_id = g.user_id
    state = game_interface.load_state(user_id)
    return jsonify({'success': True, **state})