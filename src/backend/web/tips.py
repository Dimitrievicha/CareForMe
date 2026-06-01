from flask import Blueprint, jsonify, session
from database_full.interface.tips_interface import tips_interface

tips_bp = Blueprint('tips', __name__)


@tips_bp.route('/', methods=['GET'])
def get_all_tips():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401

    tips = tips_interface.get_all_tips()
    return jsonify({'success': True, 'tips': tips})


@tips_bp.route('/positive', methods=['GET'])
def get_positive_tips():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401

    tips = tips_interface.get_positive_tips()
    return jsonify({'success': True, 'tips': tips})


@tips_bp.route('/by_type/<tip_type>', methods=['GET'])
def get_tip_by_type(tip_type):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401

    tip = tips_interface.get_tip_by_type(tip_type)
    return jsonify({'success': True, 'tip': tip})


@tips_bp.route('/for_plant/<int:species_id>', methods=['GET'])
def get_plant_tips(species_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401

    result = tips_interface.get_plant_tips(species_id)
    if not result:
        return jsonify({'success': False, 'error': f'Вид {species_id} не найден'}), 404

    return jsonify({'success': True, **result})