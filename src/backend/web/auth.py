"""
API маршруты для авторизации
"""

from flask import Blueprint, request, jsonify, session, g
from database_full.interface.user_interface import user_interface
from utils.decorators import login_required_api

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/check_user', methods=['POST'])
def check_user():
    """
    Проверить существует ли пользователь.
 
    POST /api/auth/check_user
    Body: { "username": str }
    Returns: { "exists": bool }
    """
    data = request.get_json()
    if not data:
        return jsonify({'exists': False}), 400
 
    username = data.get('username', '').strip()
    if not username:
        return jsonify({'exists': False}), 400
 
    user = user_interface.get_user_info_by_username(username) if hasattr(user_interface, 'get_user_info_by_username') else None
    from database_full.repository.user_repository import UserRepository
    exists = UserRepository().user_exists(username)
    return jsonify({'exists': bool(exists)})


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Регистрация нового пользователя.
 
    POST /api/auth/register
    Body: { "username": str, "password": str }
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
            'username': result['username'],
        })
    return jsonify({'success': False, 'error': result.get('error', 'Ошибка регистрации')}), 400

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Вход пользователя.
 
    POST /api/auth/login
    Body: { "username": str, "password": str, "remember_me": bool }
    Returns: { "success": bool, "user_id": str, "username": str,
               "session_token": str, "last_login": str,
               "consecutive_days": int, "need_tutorial": bool }
    """
    data = request.get_json()
    username    = data.get('username', '').strip()
    password    = data.get('password', '')
    remember_me = data.get('remember_me', False)
 
    result = user_interface.login(username, password, remember_me)
 
    if result['success']:
        session['user_id']       = result['user_id']
        session['username']      = result['username']
        session['session_token'] = result['session_token']
 
        streak_result = user_interface.update_daily_streak(result['user_id'])
        profile       = user_interface.get_profile(result['user_id'])
 
        return jsonify({
            'success':          True,
            'user_id':          result['user_id'],
            'username':         result['username'],
            'session_token':    result['session_token'],
            'last_login':       profile.get('last_entry') if profile else None,
            'consecutive_days': streak_result.get('consecutive_days', 1),
            'need_tutorial':    not profile.get('tutorial_completed', False),
        })
 
    return jsonify({'success': False, 'error': 'Неверный логин или пароль'}), 401

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """
    Выход пользователя.
 
    POST /api/auth/logout
    Поддерживает: session_token из Flask-сессии или заголовка Authorization.
    """
    session_token = session.get('session_token')
 
    if not session_token:
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            session_token = auth_header[7:]
 
    if session_token:
        user_interface.logout(session_token)
 
    session.clear()
    return jsonify({'success': True})
 

@auth_bp.route('/verify', methods=['GET'])
def verify():
    """
    Проверка авторизации.
 
    GET /api/auth/verify
    Поддерживает: session_token из Flask-сессии или заголовка Authorization.
    """
    session_token = session.get('session_token')
 
    if not session_token:
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            session_token = auth_header[7:]
 
    if not session_token:
        return jsonify({'success': False, 'error': 'Нет сессии'}), 401
 
    user = user_interface.verify_session(session_token)
    if user:
        session['user_id']       = user['user_id']
        session['username']      = user['username']
        session['session_token'] = session_token
 
        profile = user_interface.get_profile(user['user_id'])
        return jsonify({
            'success':       True,
            'user_id':       user['user_id'],
            'username':      user['username'],
            'need_tutorial': not profile.get('tutorial_completed', False) if profile else True,
        })
 
    session.clear()
    return jsonify({'success': False, 'error': 'Сессия истекла'}), 401

@auth_bp.route('/complete_tutorial', methods=['POST'])
@login_required_api
def complete_tutorial():
    """Отметить обучение пройденным."""
    success = user_interface.complete_tutorial(g.user_id)
    return jsonify({'success': success})
 
 
@auth_bp.route('/check_streak', methods=['GET'])
@login_required_api
def check_streak():
    """
    Получить информацию о серии дней.
 
    GET /api/auth/check_streak
    """
    user_id      = g.user_id
    streak_info  = user_interface.get_streak_info(user_id)
    profile      = user_interface.get_profile(user_id)
 
    return jsonify({
        'success':          True,
        'consecutive_days': streak_info.get('consecutive_days', 0),
        'best_streak':      streak_info.get('best_streak', 0),
        'last_entry':       profile.get('last_entry') if profile else None,
    })