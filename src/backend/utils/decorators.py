"""
Декораторы для Flask маршрутов
"""

from functools import wraps
from flask import jsonify, session, request


def login_required_api(f):
    """
    Декоратор для проверки авторизации в API маршрутах

    Проверяет наличие user_id в сессии.
    Если пользователь не авторизован - возвращает 401.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')

        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Необходима авторизация'
            }), 401

        return f(*args, **kwargs)

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
            # Проверяем, что тело запроса - JSON
            if not request.is_json:
                return jsonify({
                    'success': False,
                    'error': 'Content-Type должен быть application/json'
                }), 400

            data = request.get_json()

            # Проверяем обязательные поля
            if required_fields:
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    return jsonify({
                        'success': False,
                        'error': f'Отсутствуют обязательные поля: {", ".join(missing_fields)}'
                    }), 400

            # Добавляем данные в request для использования в функции
            request.validated_json = data

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def rate_limit(limit_per_minute=60):
    """
    Декоратор для ограничения частоты запросов (опционально)

    Args:
        limit_per_minute: максимальное количество запросов в минуту
    """
    from time import time
    from collections import defaultdict

    requests_log = defaultdict(list)

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Простая реализация rate limiting
            now = time()
            minute_ago = now - 60
            user_id = session.get('user_id', request.remote_addr)

            # Очищаем старые записи
            requests_log[user_id] = [t for t in requests_log[user_id] if t > minute_ago]

            # Проверяем лимит
            if len(requests_log[user_id]) >= limit_per_minute:
                return jsonify({
                    'success': False,
                    'error': 'Слишком много запросов. Подождите немного.'
                }), 429

            # Добавляем текущий запрос
            requests_log[user_id].append(now)

            return f(*args, **kwargs)

        return decorated_function

    return decorator