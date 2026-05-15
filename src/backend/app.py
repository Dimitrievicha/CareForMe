"""
Flask приложение для игры Care For Me
Только API, фронтенд отдельно в папке frontend/
"""

from flask import Flask, session, request, jsonify
from flask_cors import CORS
from functools import wraps
import os
from pathlib import Path

from config import Config

# ── ВАЖНО: инициализируем синглтон БД ДО любых импортов репозиториев ──────────
# Без этого get_db_manager(None) в репозиториях → ошибка NoneType
from database_full.database.db_manager import get_db_manager as _init_db
_DB_PATH = str(Path(__file__).parent / 'careforme.db')
_init_db(_DB_PATH)  # синглтон с правильным путём создаётся один раз
# ─────────────────────────────────────────────────────────────────────────────

from database_full.interface.user_interface import user_interface
from database_full.interface.level_quest_interface import level_quest_interface
from database_full.interface.challenge_interface import challenge_interface
from database_full.interface.flower_interface import flower_interface

app = Flask(__name__)
app.config.from_object(Config)

# Сессии Flask требуют SECRET_KEY — без него session не работает
app.secret_key = app.config.get('SECRET_KEY', 'careforme-dev-key-2024')

# Для работы с фронтом на другом порту (localhost:5500) нужен SameSite=None
# В режиме разработки без HTTPS используем Lax
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_HTTPONLY'] = True

# Настройка CORS для работы с отдельным фронтендом
CORS(app, origins=[
    'http://localhost:5500',
    'http://127.0.0.1:5500',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost:8080',
    'http://127.0.0.1:8080'
], supports_credentials=True)


# =====================================================
# Декоратор для проверки авторизации API
# =====================================================

def login_required_api(f):
    """Декоратор для API, требующих авторизации"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Не авторизован'}), 401
        return f(*args, **kwargs)
    return decorated_function


# =====================================================
# API маршруты (для AJAX запросов)
# =====================================================

@app.route('/api/garden', methods=['GET'])
@login_required_api
def api_get_garden():
    """Получить сад пользователя"""
    user_id = session['user_id']
    plants = flower_interface.get_my_garden(user_id, only_alive=True)
    return jsonify({'success': True, 'garden': plants})


@app.route('/api/garden/stats', methods=['GET'])
@login_required_api
def api_get_stats():
    """Получить статистику"""
    user_id = session['user_id']
    stats = user_interface.get_stats(user_id)
    slots = user_interface.get_plant_slots_info(user_id)
    return jsonify({
        'success': True,
        'level': stats.get('level', 1),
        'max_slots': slots.get('max', 1),
        'current_plants': slots.get('current', 0),
        'total_waterings': stats.get('total_waterings', 0),
        'total_plants': stats.get('total_plants_grown', 0),
        'streak': stats.get('consecutive_days', 0)
    })


@app.route('/api/plant', methods=['POST'])
@login_required_api
def api_plant():
    """Посадить растение"""
    user_id = session['user_id']
    data = request.get_json()
    species_id = data.get('species_id')
    name = data.get('name')

    if not user_interface.has_free_slot(user_id):
        return jsonify({'success': False, 'error': 'Нет свободных слотов'})

    result = flower_interface.plant_flower(user_id, species_id, name)

    if result['success']:
        level_quest_interface.trigger_check(user_id, 'plant')

    return jsonify(result)


@app.route('/api/water/<plant_id>', methods=['POST'])
@login_required_api
def api_water(plant_id):
    """Полить растение"""
    user_id = session['user_id']
    result = flower_interface.water_flower(plant_id, user_id)

    if result['success']:
        check_result = level_quest_interface.trigger_check(user_id, 'water')
        result['level_check'] = check_result

    return jsonify(result)


@app.route('/api/check/<plant_id>', methods=['GET'])
@login_required_api
def api_check(plant_id):
    """Проверить здоровье растения"""
    user_id = session['user_id']
    result = flower_interface.check_health(plant_id, user_id)
    return jsonify(result)


@app.route('/api/quests/progress', methods=['GET'])
@login_required_api
def api_quest_progress():
    """Получить прогресс заданий"""
    user_id = session['user_id']
    progress = level_quest_interface.get_current_level_progress(user_id)
    return jsonify({'success': True, 'progress': progress})


@app.route('/api/achievements', methods=['GET'])
@login_required_api
def api_achievements():
    """Получить все достижения"""
    user_id = session['user_id']
    achievements = challenge_interface.get_all_achievements(user_id)
    stats = challenge_interface.get_statistics(user_id)
    return jsonify({
        'success': True,
        'achievements': achievements,
        'stats': stats
    })


@app.route('/api/settings/volume', methods=['POST'])
@login_required_api
def api_set_volume():
    """Сохранить настройки громкости"""
    data = request.get_json()
    volume = data.get('volume', 50)
    return jsonify({'success': True, 'volume': volume})


# =====================================================
# API маршруты для авторизации (без авторизации)
# =====================================================

@app.route('/api/auth/register', methods=['POST'])
def api_register():
    """API регистрации для фронтенда"""
    data = request.get_json(silent=True) or {}  # silent=True — не падает если тело пустое
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if len(username) < 3:
        return jsonify({'success': False, 'error': 'Имя пользователя не менее 3 символов'}), 400

    if len(password) < 4:
        return jsonify({'success': False, 'error': 'Пароль не менее 4 символов'}), 400

    result = user_interface.register(username, password)

    if result['success']:
        return jsonify({
            'success': True,
            'user_id': result['user_id'],
            'username': result['username']
        })
    else:
        return jsonify({'success': False, 'error': result.get('error', 'Ошибка регистрации')}), 400


@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """API входа для фронтенда"""
    data = request.get_json(silent=True) or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    remember_me = data.get('remember_me', False)

    result = user_interface.login(username, password, remember_me)

    if result['success']:
        session['user_id'] = result['user_id']
        session['username'] = result['username']
        session['session_token'] = result['session_token']

        streak_result = user_interface.update_daily_streak(result['user_id'])
        profile = user_interface.get_profile(result['user_id'])

        return jsonify({
            'success': True,
            'user_id': result['user_id'],
            'username': result['username'],
            'session_token': result['session_token'],
            'last_login': profile.get('last_entry') if profile else None,
            'consecutive_days': streak_result.get('consecutive_days', 1),
            'need_tutorial': not profile.get('tutorial_completed', False)
        })
    else:
        return jsonify({'success': False, 'error': 'Неверный логин или пароль'}), 401


@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    """API выхода"""
    session_token = session.get('session_token')
    if session_token:
        user_interface.logout(session_token)

    session.clear()
    return jsonify({'success': True})


@app.route('/api/auth/verify', methods=['GET'])
def api_verify():
    """API проверки сессии"""
    session_token = session.get('session_token')

    if not session_token:
        return jsonify({'success': False, 'error': 'Нет сессии'}), 401

    user = user_interface.verify_session(session_token)

    if user:
        session['user_id'] = user['user_id']
        session['username'] = user['username']

        return jsonify({
            'success': True,
            'user_id': user['user_id'],
            'username': user['username']
        })
    else:
        session.clear()
        return jsonify({'success': False, 'error': 'Сессия истекла'}), 401


# =====================================================
# Корневой маршрут (просто для проверки)
# =====================================================

@app.route('/')
def index():
    """Проверка работы API"""
    return jsonify({
        'name': 'Care For Me API',
        'version': '1.0',
        'status': 'running',
        'message': 'Фронтенд находится в папке frontend/'
    })


@app.route('/api/test', methods=['GET'])
def test():
    """Тестовый маршрут"""
    return jsonify({'success': True, 'message': 'Сервер работает!'})


# =====================================================
# Запуск приложения
# =====================================================

if __name__ == '__main__':
    print("=" * 60)
    print("Care For Me Backend Server (API Only)")
    print("=" * 60)
    print("Сервер запущен на http://localhost:5000")
    print("Фронтенд запускайте отдельно через Live Server")
    print("=" * 60)

    app.run(host='0.0.0.0', port=5000, debug=True)