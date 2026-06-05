"""
Валидаторы для входных данных
"""

import re


def validate_username(username):
    """
    Валидация имени пользователя

    Args:
        username: str - имя пользователя

    Returns:
        (bool, str) - (валидно, сообщение об ошибке)
    """
    if not username:
        return False, "Имя пользователя обязательно"

    if len(username) < 3:
        return False, "Имя пользователя должно содержать минимум 3 символа"

    if len(username) > 50:
        return False, "Имя пользователя не должно превышать 50 символов"

    # Разрешаем буквы (русские и английские), цифры, дефис, подчеркивание
    if not re.match(r'^[a-zA-Z0-9а-яА-Я_-]+$', username):
        return False, "Имя пользователя может содержать только буквы, цифры, дефис и подчеркивание"

    return True, ""


def validate_password(password):
    """
    Валидация пароля

    Args:
        password: str - пароль

    Returns:
        (bool, str) - (валидно, сообщение об ошибке)
    """
    if not password:
        return False, "Пароль обязателен"

    if len(password) < 4:
        return False, "Пароль должен содержать минимум 4 символа"

    if len(password) > 100:
        return False, "Пароль слишком длинный"

    return True, ""


def validate_plant_data(species_id, custom_name=None):
    """
    Валидация данных для посадки растения

    Args:
        species_id: int - ID вида растения
        custom_name: str (опционально) - пользовательское имя

    Returns:
        (bool, str) - (валидно, сообщение об ошибке)
    """
    # Проверка вида растения
    if not species_id:
        return False, "Не указан вид растения"

    if species_id not in [1, 2, 3]:
        return False, "Неверный ID вида растения. Доступны: 1 (Спатифиллум), 2 (Кактус), 3 (Фикус)"

    # Проверка пользовательского имени
    if custom_name:
        if len(custom_name) < 1:
            return False, "Имя растения не может быть пустым"

        if len(custom_name) > 50:
            return False, "Имя растения не должно превышать 50 символов"

        # Запрещаем специальные символы
        if re.search(r'[<>{}[\]\\]', custom_name):
            return False, "Имя растения содержит недопустимые символы"

    return True, ""


def validate_quest_action(action):
    """
    Валидация действия для триггера заданий

    Args:
        action: str - тип действия

    Returns:
        bool - валидно ли действие
    """
    valid_actions = ['water', 'plant', 'mistake', 'read_tip', 'grow_to_mature', 'heal', 'death']
    return action in valid_actions


def validate_mistake_type(mistake_type):
    """
    Валидация типа ошибки

    Args:
        mistake_type: str - тип ошибки

    Returns:
        bool - валиден ли тип
    """
    valid_types = ['overwater', 'drought', 'light', 'cold']
    return mistake_type in valid_types