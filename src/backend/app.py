"""
Flask приложение для игры Care For Me
"""

from flask import Flask, send_from_directory, session, jsonify
from flask_cors import CORS
import os
from pathlib import Path

from config import Config

# ─────────────────────────────────────────────────────────
# Инициализация БД — ДО импорта репозиториев и Blueprint'ов
# ─────────────────────────────────────────────────────────
from database_full.database.db_manager import get_db_manager as _init_db

_DB_PATH  = str(Path(__file__).parent / 'careforme.db')
_SQL_PATH = Path(__file__).parent / 'database_full' / 'database' / 'init_db.sql'
_CSV_DIR  = Path(__file__).parent / 'database_full' / 'csv'

_db = _init_db(_DB_PATH)

# Создаём таблицы (CREATE TABLE IF NOT EXISTS — безопасно при каждом старте)
if _SQL_PATH.exists():
    with open(_SQL_PATH, 'r', encoding='utf-8') as _f:
        _db.connect().executescript(_f.read())
else:
    print(f"⚠️  SQL файл не найден: {_SQL_PATH}")

# Загружаем CSV-данные если таблица пустая
_count = _db.execute_query("SELECT COUNT(*) as c FROM plant_templates")
if not _count or _count[0]['c'] == 0:
    print(" Загрузка данных из CSV...")
    from database_full.database.raw_sql_loader import (
        load_plants_from_csv_raw,
        load_achievements_from_csv_raw,
        load_tips_from_csv_raw,
        load_level_requirements_from_csv_raw,
    )
    _files = {
        'plant_catalog.csv': load_plants_from_csv_raw,
        'achievements_catalog.csv':load_achievements_from_csv_raw,
        'tips.csv': load_tips_from_csv_raw,
        'level_requirements.csv': load_level_requirements_from_csv_raw,
    }
    for _fname, _loader in _files.items():
        _path = _CSV_DIR / _fname
        if _path.exists():
            _loader(str(_path))
        else:
            print(f"  Файл не найден: {_path}")
    print(" Данные загружены")

# ─────────────────────────────────────────────────────────
# Blueprint'ы
# ─────────────────────────────────────────────────────────
from web.auth import auth_bp
from web.garden import garden_bp
from web.plants import plants_bp
from web.user import user_bp
from web.quests import quests_bp
from web.achievements import achievements_bp
from web.tips import tips_bp
from web.game_state import game_bp

app = Flask(__name__)
app.config.from_object(Config)

app.secret_key = app.config.get('SECRET_KEY', 'careforme-dev-key-2024')

# Настройки сессии
app.config['SESSION_COOKIE_NAME'] = 'careforme_session'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 30 * 24 * 60 * 60

# CORS - для разработки
CORS(app, origins=[
    'http://localhost:5000',
    'http://127.0.0.1:5000',
    'http://localhost:5500',
    'http://127.0.0.1:5500'
], supports_credentials=True)

app.register_blueprint(auth_bp,         url_prefix='/api/auth')
app.register_blueprint(garden_bp,       url_prefix='/api/garden')
app.register_blueprint(plants_bp,       url_prefix='/api/plants')
app.register_blueprint(user_bp,         url_prefix='/api/user')
app.register_blueprint(quests_bp,       url_prefix='/api/quests')
app.register_blueprint(achievements_bp, url_prefix='/api/achievements')
app.register_blueprint(tips_bp,         url_prefix='/api/tips')
app.register_blueprint(game_bp,         url_prefix='/api/game')

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend')

with open(os.path.join(FRONTEND_DIR, '404.html'), 'r', encoding='utf-8') as f:
    CUSTOM_404_HTML = f.read()


@app.route('/')
def index():
    return send_from_directory(FRONTEND_DIR, 'register.html')

@app.route('/register.html')
def register_page():
    return send_from_directory(FRONTEND_DIR, 'register.html')

@app.route('/room.html')
def room_page():
    if 'user_id' not in session:
        return send_from_directory(FRONTEND_DIR, 'unauthorized.html'), 403
    return send_from_directory(FRONTEND_DIR, 'room.html')

@app.route('/welcome.html')
def welcome_page():
    if 'user_id' not in session:
        return send_from_directory(FRONTEND_DIR, 'unauthorized.html'), 403
    return send_from_directory(FRONTEND_DIR, 'welcome.html')

@app.route('/unauthorized.html')
def unauthorized_page():
    return send_from_directory(FRONTEND_DIR, 'unauthorized.html')

# СТАТИЧЕСКИЕ ФАЙЛЫ

@app.route('/css/<path:filename>')
def serve_css(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, 'css'), filename)

@app.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, 'js'), filename)

@app.route('/images/<path:filename>')
def serve_images(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, 'images'), filename)

@app.route('/music/<path:filename>')
def serve_music(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, 'music'), filename)

@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, 'assets'), filename)

# КАСТОМНАЯ СТРАНИЦА 404

@app.errorhandler(404)
def not_found_error(e):
    return CUSTOM_404_HTML, 404

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    full_path = os.path.join(FRONTEND_DIR, path)
    if os.path.exists(full_path) and os.path.isfile(full_path):
        return send_from_directory(FRONTEND_DIR, path)
    return CUSTOM_404_HTML, 404

if __name__ == '__main__':
    print(f"Сервер запущен на http://localhost:5000")
    print("Доступные страницы:")
    print("  - http://localhost:5000/register.html (всегда доступна)")
    print("  - http://localhost:5000/room.html (только для авторизованных)")
    print("  - http://localhost:5000/welcome.html (только для авторизованных)")
    app.run(host='0.0.0.0', port=5000, debug=True)