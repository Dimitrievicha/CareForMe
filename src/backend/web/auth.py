"""
API маршруты для авторизации
"""

from flask import Blueprint, request, jsonify, session, g
from database_full.interface.user_interface import user_interface
from database_full.repository.user_repository import UserRepository
from functools import wraps

auth_bp = Blueprint('auth', __name__)


def login_required_api(f):
    """
    Декоратор для проверки авторизации DB_TESTING_REPORT.md API маршрутах

    Проверяет:
    1. Наличие user_id DB_TESTING_REPORT.md сессии (cookie)
    2. ИЛИ наличие session_token DB_TESTING_REPORT.md заголовке Authorization
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')

        # Если есть DB_TESTING_REPORT.md сессии — используем
        if user_id:
            g.user_id = user_id
            return f(*args, **kwargs)

        # Если нет — проверяем заголовок Authorization
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            session_token = auth_header[7:]  # Убираем 'Bearer '

            if session_token:
                # Проверяем токен DB_TESTING_REPORT.md БД
                user = user_interface.verify_session(session_token)
                if user:
                    g.user_id = user['user_id']
                    # Опционально: восстанавливаем сессию Flask
                    session['user_id'] = user['user_id']
                    session['username'] = user['username']
                    session['session_token'] = session_token
                    return f(*args, **kwargs)

        return jsonify({
            'success': False,
            'error': 'Необходима авторизация'
        }), 401

    return decorated_function


@auth_bp.route('/check_user', methods=['POST'])
def check_user():
    """
    Проверить существует ли пользователь DB_TESTING_REPORT.md БД.

    POST /api/auth/check_user
    Body: { "username": "string" }

    Returns: { "exists": bool }
    """
    data = request.get_json()
    if not data:
        return jsonify({'exists': False}), 400

    username = data.get('username', '').strip()
    if not username:
        return jsonify({'exists': False}), 400

    repo = UserRepository()
    exists = repo.user_exists(username)
    return jsonify({'exists': bool(exists)})


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
        "session_token": str,
        "last_login": str,
        "consecutive_days": int,
        "need_tutorial": bool
    }
    """
    data = request.get_json()
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


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """
    Выход пользователя

    POST /api/auth/logout

    Поддерживает:
    1. session_token из Flask-сессии
    2. session_token из заголовка Authorization
    """
    # Пытаемся получить токен из сессии
    session_token = session.get('session_token')

    # Если нет DB_TESTING_REPORT.md сессии — пробуем из заголовка
    if not session_token:
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            session_token = auth_header[7:]

    # Удаляем сессию из БД
    if session_token:
        user_interface.logout(session_token)

    # Очищаем Flask-сессию
    session.clear()
    return jsonify({'success': True})


@auth_bp.route('/verify', methods=['GET'])
def verify():
    """
    Проверка авторизации

    GET /api/auth/verify

    Поддерживает:
    1. session_token из Flask-сессии
    2. session_token из заголовка Authorization
    """
    # Пытаемся получить токен из сессии
    session_token = session.get('session_token')

    # Если нет DB_TESTING_REPORT.md сессии — пробуем из заголовка
    if not session_token:
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            session_token = auth_header[7:]

    if not session_token:
        return jsonify({'success': False, 'error': 'Нет сессии'}), 401

    # Проверяем токен DB_TESTING_REPORT.md БД
    user = user_interface.verify_session(session_token)
    if user:
        # Восстанавливаем сессию
        session['user_id'] = user['user_id']
        session['username'] = user['username']
        session['session_token'] = session_token
        profile = user_interface.get_profile(user['user_id'])
        return jsonify({
            'success': True,
            'user_id': user['user_id'],
            'username': user['username'],
            'need_tutorial': not profile.get('tutorial_completed', False) if profile else True
        })
    else:
        session.clear()
        return jsonify({'success': False, 'error': 'Сессия истекла'}), 401


@auth_bp.route('/complete_tutorial', methods=['POST'])
@login_required_api
def complete_tutorial():
    """Отметить обучение пройденным."""
    user_id = g.user_id
    success = user_interface.complete_tutorial(user_id)
    return jsonify({'success': success})


@auth_bp.route('/check_streak', methods=['GET'])
@login_required_api
def check_streak():
    """
    Получить информацию о серии дней

    GET /api/auth/check_streak
    """
    user_id = g.user_id

    streak_info = user_interface.get_streak_info(user_id)
    profile = user_interface.get_profile(user_id)

    return jsonify({
        'success': True,
        'consecutive_days': streak_info.get('consecutive_days', 0),
        'best_streak': streak_info.get('best_streak', 0),
        'last_entry': profile.get('last_entry') if profile else None
    })