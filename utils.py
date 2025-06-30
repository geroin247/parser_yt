import os
from database import db_manager

def ensure_users_file():
    """Создает файл users.txt если его нет (для совместимости)"""
    if not os.path.exists('users.txt'):
        with open('users.txt', 'w') as f:
            f.write('')

def in_base(user_id):
    """Проверяет есть ли пользователь в базе данных"""
    user_info = db_manager.get_user_info(user_id)
    return user_info is not None

def save_user(user_id):
    """Сохраняет пользователя в базу (базовая функция для совместимости)"""
    # Эта функция оставлена для совместимости
    # Реальное сохранение происходит через db_manager.save_user() с полными данными
    if not in_base(user_id):
        # Создаем минимальную запись пользователя
        user_data = {
            'user_id': user_id,
            'username': None,
            'first_name': None,
            'last_name': None,
            'language_code': None,
            'is_bot': False,
            'is_premium': False
        }
        db_manager.save_user(user_data)

def get_users():
    """Возвращает список ID всех пользователей"""
    all_users = db_manager.get_all_users()
    return [str(user['user_id']) for user in all_users]

def export_users_to_txt():
    """Экспортирует пользователей в текстовый файл (для совместимости)"""
    users = get_users()
    with open('users.txt', 'w', encoding='utf-8') as f:
        for user_id in users:
            f.write(f"{user_id}\n")
    return 'users.txt'