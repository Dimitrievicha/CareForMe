"""
API маршруты для советов (tips)
Префикс: /api/tips

Маршруты:
    GET  /api/tips/                      — все советы
    GET  /api/tips/positive              — только позитивные (для ежедневного показа)
    GET  /api/tips/by_type/<tip_type>    — совет по типу ошибки
    GET  /api/tips/for_plant/<species_id>— советы для конкретного вида
"""

from flask import Blueprint, jsonify, session
from database_full.database.db_manager import get_db_manager

tips_bp = Blueprint('tips', __name__)


def _get_db():
    return get_db_manager()


# ── Все советы ────────────────────────────────────────────────────────────────

@tips_bp.route('/', methods=['GET'])
def get_all_tips():
    """
    Все советы из таблицы tips.

    GET /api/tips/

    Returns: {
        "success": bool,
        "tips": [
            {
                "id": int,
                "tip_type": str,
                "title": str,
                "message": str,
                "is_positive": bool
            }
        ]
    }
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401

    db = _get_db()
    rows = db.execute_query("SELECT id, tip_type, title, message, is_positive FROM tips ORDER BY id")

    tips = [
        {
            'id': r[0],
            'tip_type': r[1],
            'title': r[2],
            'message': r[3],
            'is_positive': bool(r[4])
        }
        for r in (rows or [])
    ]

    return jsonify({'success': True, 'tips': tips})


# ── Только позитивные ─────────────────────────────────────────────────────────

@tips_bp.route('/positive', methods=['GET'])
def get_positive_tips():
    """
    Позитивные советы — показываются 1-2 раза в день (согласно гейм-дизайну).

    GET /api/tips/positive

    Returns: {
        "success": bool,
        "tips": [...]
    }
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401

    db = _get_db()
    rows = db.execute_query(
        "SELECT id, tip_type, title, message FROM tips WHERE is_positive = 1 ORDER BY id"
    )

    tips = [{'id': r[0], 'tip_type': r[1], 'title': r[2], 'message': r[3]} for r in (rows or [])]
    return jsonify({'success': True, 'tips': tips})


# ── Совет по типу ошибки ──────────────────────────────────────────────────────

@tips_bp.route('/by_type/<tip_type>', methods=['GET'])
def get_tip_by_type(tip_type):
    """
    Получить совет по типу события.

    Типы ошибок: overwater, drought, light, cold,
                 death_first, death_overwater, death_drought, death_light, death_complex
    Позитивные:  perfect_water, healed, flowered

    GET /api/tips/by_type/{tip_type}

    Returns: {
        "success": bool,
        "tip": { "id": int, "title": str, "message": str, "is_positive": bool }
    }
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401

    db = _get_db()
    rows = db.execute_query(
        "SELECT id, title, message, is_positive FROM tips WHERE tip_type = ? LIMIT 1",
        (tip_type,)
    )

    if not rows:
        # Возвращаем дефолтный совет вместо 404, чтобы фронт не падал
        return jsonify({
            'success': True,
            'tip': {
                'id': None,
                'title': 'Совет',
                'message': 'Присматривай за цветком — он тебя порадует! 🌿',
                'is_positive': True
            }
        })

    r = rows[0]
    return jsonify({
        'success': True,
        'tip': {'id': r[0], 'title': r[1], 'message': r[2], 'is_positive': bool(r[3])}
    })


# ── Советы для вида растения (из plant_templates) ─────────────────────────────

@tips_bp.route('/for_plant/<int:species_id>', methods=['GET'])
def get_plant_tips(species_id):
    """
    Советы из карточки конкретного вида (поле tips в plant_templates).
    Пользователь видит их в карточке растения.

    GET /api/tips/for_plant/{species_id}

    Returns: {
        "success": bool,
        "species_name": str,
        "tips": [str],
        "symptoms": [{ "symptom": str, "cause": str, "advice": str }]
    }
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401

    db = _get_db()
    rows = db.execute_query(
        "SELECT species_name, tips, symptoms FROM plant_templates WHERE species_id = ?",
        (species_id,)
    )

    if not rows:
        return jsonify({'success': False, 'error': f'Вид {species_id} не найден'}), 404

    r = rows[0]
    species_name = r[0]

    # tips — строка с разделителем " | " или JSON-массив
    import json
    raw_tips = r[1] or '[]'
    try:
        tips = json.loads(raw_tips)
    except (json.JSONDecodeError, TypeError):
        tips = [t.strip() for t in str(raw_tips).split('|') if t.strip()]

    # symptoms — строка вида "Симптом: причина -> совет | ..."
    raw_symptoms = r[2] or ''
    symptoms = []
    for entry in str(raw_symptoms).split('|'):
        entry = entry.strip()
        if not entry:
            continue
        # Формат: "Симптом: причина -> совет"
        if '->' in entry:
            left, advice = entry.split('->', 1)
            if ':' in left:
                symptom, cause = left.split(':', 1)
            else:
                symptom, cause = left, ''
            symptoms.append({
                'symptom': symptom.strip(),
                'cause': cause.strip(),
                'advice': advice.strip()
            })
        else:
            symptoms.append({'symptom': entry, 'cause': '', 'advice': ''})

    return jsonify({
        'success': True,
        'species_name': species_name,
        'tips': tips,
        'symptoms': symptoms
    })
