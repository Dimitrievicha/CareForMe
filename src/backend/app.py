"""
Flask приложение для игры Care For Me
Обычный пользователь, только игровые действия
"""

from flask import Flask, render_template, session, redirect, url_for, request, jsonify
from functools import wraps
import os

from config import Config
from src.backend.database_full.interface.user_interface import user_interface
from src.backend.database_full.interface.level_quest_interface import level_quest_interface
from src.backend.database_full.interface.challenge_interface import challenge_interface
from src.backend.database_full.interface.flower_interface import flower_interface

app = Flask(__name__)
app.config.from_object(Config)


# =====================================================
# Декоратор для проверки авторизации
# =====================================================

def login_required(f):
    """Декоратор для страниц, требующих авторизации"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function


# =====================================================
# API маршруты (для AJAX запросов)
# =====================================================

@app.route('/api/garden', methods=['GET'])
@login_required
def api_get_garden():
    """Получить сад пользователя"""
    user_id = session['user_id']
    plants = flower_interface.get_my_garden(user_id, only_alive=True)
    return jsonify({'success': True, 'garden': plants})


@app.route('/api/garden/stats', methods=['GET'])
@login_required
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
@login_required
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
        # Проверяем задания после посадки
        level_quest_interface.trigger_check(user_id, 'plant')

    return jsonify(result)


@app.route('/api/water/<plant_id>', methods=['POST'])
@login_required
def api_water(plant_id):
    """Полить растение"""
    user_id = session['user_id']
    result = flower_interface.water_flower(plant_id, user_id)

    if result['success']:
        # Проверяем задания после полива
        check_result = level_quest_interface.trigger_check(user_id, 'water')
        result['level_check'] = check_result

    return jsonify(result)


@app.route('/api/check/<plant_id>', methods=['GET'])
@login_required
def api_check(plant_id):
    """Проверить здоровье растения"""
    user_id = session['user_id']
    result = flower_interface.check_health(plant_id, user_id)
    return jsonify(result)


@app.route('/api/quests/progress', methods=['GET'])
@login_required
def api_quest_progress():
    """Получить прогресс заданий"""
    user_id = session['user_id']
    progress = level_quest_interface.get_current_level_progress(user_id)
    return jsonify({'success': True, 'progress': progress})


@app.route('/api/achievements', methods=['GET'])
@login_required
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
@login_required
def api_set_volume():
    """Сохранить настройки громкости"""
    user_id = session['user_id']
    data = request.get_json()
    volume = data.get('volume', 50)

    # Можно сохранить в профиле или в отдельной таблице настроек
    # Пока просто возвращаем успех
    return jsonify({'success': True, 'volume': volume})


# =====================================================
# Страницы (обычные HTML, не SPA)
# =====================================================

@app.route('/')
@login_required
def index():
    """Главная страница - сад"""
    user_id = session['user_id']

    # Получаем данные для отображения
    plants = flower_interface.get_my_garden(user_id, only_alive=True)
    stats = user_interface.get_stats(user_id)
    slots = user_interface.get_plant_slots_info(user_id)
    designs = user_interface.get_current_designs(user_id)
    quest_progress = level_quest_interface.get_current_level_progress(user_id)

    # Доступные растения для посадки
    available_plants = [
        {'id': 1, 'name': 'Спатифиллюм', 'icon': '🌸', 'description': 'Нежный и честный'},
        {'id': 2, 'name': 'Кактус', 'icon': '🌵', 'description': 'Выносливый отшельник'},
        {'id': 3, 'name': 'Фикус', 'icon': '🌿', 'description': 'Спокойный стратег'}
    ]

    return render_template('index.html',
                         plants=plants,
                         stats=stats,
                         slots=slots,
                         designs=designs,
                         quest_progress=quest_progress,
                         available_plants=available_plants)


@app.route('/achievements')
@login_required
def achievements_page():
    """Страница достижений"""
    user_id = session['user_id']

    achievements = challenge_interface.get_all_achievements(user_id)
    stats = challenge_interface.get_statistics(user_id)

    return render_template('achievements.html',
                         achievements=achievements,
                         stats=stats)


@app.route('/settings')
@login_required
def settings_page():
    """Страница настроек"""
    return render_template('settings.html')


@app.route('/login')
def login_page():
    """Страница входа"""
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template('login.html')


@app.route('/login', methods=['POST'])
def login():
    """Обработка входа"""
    username = request.form.get('username')
    password = request.form.get('password')
    remember_me = request.form.get('remember_me') == 'on'

    result = user_interface.login(username, password, remember_me)

    if result['success']:
        session['user_id'] = result['user_id']
        session['username'] = result['username']
        session['session_token'] = result['session_token']

        # Обновляем ежедневную серию
        user_interface.update_daily_streak(result['user_id'])

        return redirect(url_for('index'))
    else:
        return render_template('login.html', error=result.get('error'))


@app.route('/register')
def register_page():
    """Страница регистрации"""
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template('register.html')


@app.route('/register', methods=['POST'])
def register():
    """Обработка регистрации"""
    username = request.form.get('username')
    password = request.form.get('password')

    result = user_interface.register(username, password)

    if result['success']:
        return redirect(url_for('login_page'))
    else:
        return render_template('register.html', error=result.get('error'))


@app.route('/logout')
def logout():
    """Выход из системы"""
    if 'session_token' in session:
        user_interface.logout(session['session_token'])
    session.clear()
    return redirect(url_for('login_page'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)