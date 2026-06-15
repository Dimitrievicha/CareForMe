"""
Декораторы для Flask маршрутов
"""

from functools import wraps
from flask import jsonify, session, request, g
from database_full.interface.user_interface import user_interface


def login_required_api(f):
    """
    Декоратор для проверки авторизации в API маршрутах.
 
    Проверяет (в порядке приоритета):
    1. user_id в Flask-сессии (cookie)
    2. Bearer-токен в заголовке Authorization
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Способ 1: Flask-сессия
        user_id = session.get('user_id')
        if user_id:
            g.user_id = user_id
            return f(*args, **kwargs)
 
        # Способ 2: Bearer-токен
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            if token:
                user = user_interface.verify_session(token)
                if user:
                    g.user_id = user['user_id']
                    # Восстанавливаем сессию чтобы следующие запросы шли по способу 1
                    session['user_id'] = user['user_id']
                    session['session_token'] = token
                    return f(*args, **kwargs)
 
        return jsonify({'success': False, 'error': 'Необходима авторизация'}), 401
 
    return decorated_function



