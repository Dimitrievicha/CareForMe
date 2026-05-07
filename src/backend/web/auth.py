"""
API маршруты для авторизации
"""

from flask import Blueprint, request, jsonify, session
from src.backend.database_full.interface.user_interface import user_interface
from src.backend.database_full.repository.user_repository import UserRepository

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Регистрация нового пользователя

    POST /api/auth/register
    Body: { "username": "string", "password": "string" }

    Returns: { "success": bool, "user_id": str, "username": str, "error": str }
    """
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')

    # Валидация
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


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Вход пользователя

    POST /api/auth/login
    Body: { "username": "string", "password": "string", "remember_me": bool }

    Returns: {
        "success": bool,
        "user_id": str,
        "username": str,
        "last_login": str,        # Дата последнего входа
        "consecutive_days": int,  # Текущая серия дней
        "error": str
    }
    """
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    remember_me = data.get('remember_me', False)

    result = user_interface.login(username, password, remember_me)

    if result['success']:
        # Сохраняем в сессию Flask
        session['user_id'] = result['user_id']
        session['username'] = result['username']
        session['session_token'] = result['session_token']

        # Обновляем ежедневную серию (проверка когда заходил в последний раз)
        streak_result = user_interface.update_daily_streak(result['user_id'])

        # Получаем профиль для информации о последнем входе
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


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """
    Выход из системы

    POST /api/auth/logout
    Returns: { "success": bool }
    """
    session_token = session.get('session_token')
    if session_token:
        user_interface.logout(session_token)

    session.clear()
    return jsonify({'success': True})


@auth_bp.route('/verify', methods=['GET'])
def verify():
    """
    Проверка валидности сессии (при загрузке страницы)

    GET /api/auth/verify
    Returns: { "success": bool, "user_id": str, "username": str }
    """
    session_token = session.get('session_token')

    if not session_token:
        return jsonify({'success': False, 'error': 'Нет сессии'}), 401

    user = user_interface.verify_session(session_token)

    if user:
        # Обновляем сессию
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


@auth_bp.route('/complete_tutorial', methods=['POST'])
def complete_tutorial():
    """
    Отметить, что обучение пройдено

    POST /api/auth/complete_tutorial
    Returns: { "success": bool }
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401

    # Обновляем профиль - отмечаем обучение пройденным
    repo = UserRepository()

    success = repo.db.execute_update("""
        UPDATE player_profiles SET tutorial_completed = 1 WHERE user_id = ?
    """, (user_id,))

    return jsonify({'success': success})


@auth_bp.route('/check_streak', methods=['GET'])
def check_streak():
    """
    Проверить текущую серию дней (для отображения)

    GET /api/auth/check_streak
    Returns: {
        "success": bool,
        "consecutive_days": int,
        "best_streak": int,
        "last_entry": str
    }
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401

    streak_info = user_interface.get_streak_info(user_id)
    profile = user_interface.get_profile(user_id)

    return jsonify({
        'success': True,
        'consecutive_days': streak_info.get('consecutive_days', 0),
        'best_streak': streak_info.get('best_streak', 0),
        'last_entry': profile.get('last_entry') if profile else None
    })