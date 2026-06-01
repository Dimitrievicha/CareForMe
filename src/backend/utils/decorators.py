"""
Декораторы для Flask маршрутов
"""

from functools import wraps
from flask import jsonify, session, request, g
from database_full.repository.user_repository import UserRepository


def login_required_api(f):
    """
    Декоратор для проверки авторизации в API маршрутах

    Проверяет:
    1. Наличие user_id в сессии (cookie)
    2. ИЛИ наличие session_token в заголовке Authorization
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')

        # Если есть в сессии — используем
        if user_id:
            g.user_id = user_id
            return f(*args, **kwargs)

        # Если нет — проверяем заголовок Authorization
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            session_token = auth_header[7:]  # Убираем 'Bearer '

            if session_token:
                repo = UserRepository()
                result = repo.db.execute_query(
                    "SELECT user_id FROM user_sessions WHERE session_token = ? AND expires_at > datetime('now')",
                    (session_token,)
                )
                if result and len(result) > 0:
                    user_id = result[0]['user_id']
                    g.user_id = user_id
                    return f(*args, **kwargs)

        return jsonify({
            'success': False,
            'error': 'Необходима авторизация'
        }), 401

    return decorated_function


def validate_json(required_fields=None):
    """
    Декоратор для валидации JSON тела запроса

    Args:
        required_fields: список обязательных полей

    Returns:
        Если валидация не пройдена - возвращает ошибку 400
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return jsonify({
                    'success': False,
                    'error': 'Content-Type должен быть application/json'
                }), 400

            data = request.get_json()

            if required_fields:
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    return jsonify({
                        'success': False,
                        'error': f'Отсутствуют обязательные поля: {", ".join(missing_fields)}'
                    }), 400

            request.validated_json = data
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def rate_limit(limit_per_minute=60):
    """
    Декоратор для ограничения частоты запросов
    """
    from time import time
    from collections import defaultdict

    requests_log = defaultdict(list)

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            now = time()
            minute_ago = now - 60
            user_id = session.get('user_id', request.remote_addr)

            requests_log[user_id] = [t for t in requests_log[user_id] if t > minute_ago]

            if len(requests_log[user_id]) >= limit_per_minute:
                return jsonify({
                    'success': False,
                    'error': 'Слишком много запросов. Подождите немного.'
                }), 429

            requests_log[user_id].append(now)
            return f(*args, **kwargs)
        return decorated_function
    return decorator