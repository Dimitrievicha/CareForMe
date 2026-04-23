PRAGMA foreign_keys = ON;

-- -----------------------------------------------------
-- Таблица пользователей (аккаунты)
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY DEFAULT (LOWER(HEX(RANDOMBLOB(16)))),
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME,
    login_count INTEGER DEFAULT 0
);

-- -----------------------------------------------------
-- Таблица сессий (для поддержания входа)
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS sessions (
    id VARCHAR(36) PRIMARY KEY DEFAULT (LOWER(HEX(RANDOMBLOB(16)))),
    user_id VARCHAR(36) NOT NULL,
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_revoked BOOLEAN DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);


-- -----------------------------------------------------
-- Таблица профилей игроков (игровая статистика)
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS player_profiles (
    user_id VARCHAR(36) PRIMARY KEY,
    display_name VARCHAR(50),
    level INTEGER DEFAULT 1,
    xp INTEGER DEFAULT 0,
    coins INTEGER DEFAULT 0,
    total_plants_grown INTEGER DEFAULT 0,
    total_waterings INTEGER DEFAULT 0,
    total_mistakes INTEGER DEFAULT 0,
    total_deaths INTEGER DEFAULT 0,
    current_plants_count INTEGER DEFAULT 0,
    max_plants_slots INTEGER DEFAULT 1,
    tutorial_completed BOOLEAN DEFAULT 0,
    last_entry DATE DEFAULT CURRENT_DATE,
    consecutive_days INTEGER DEFAULT 1,
    best_streak INTEGER DEFAULT 1,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- -----------------------------------------------------
-- Таблица шаблонов растений (справочник)
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS plant_templates (
    id VARCHAR(36) PRIMARY KEY DEFAULT (LOWER(HEX(RANDOMBLOB(16)))),
    species_id INTEGER UNIQUE NOT NULL,
    species_name VARCHAR(100) NOT NULL,
    nickname VARCHAR(100),
    description TEXT,
    character_trait VARCHAR(100),
    water_interval_min INTEGER,
    water_interval_max INTEGER,
    light_requirement VARCHAR(20) CHECK (light_requirement IN ('low', 'medium', 'high')),
    humidity_preference VARCHAR(20) CHECK (humidity_preference IN ('low', 'medium', 'high')),
    watering_advice TEXT,
    light_advice TEXT,
    flowering_conditions TEXT,
    temp_advice TEXT,
    tips JSON DEFAULT '[]',
    symptoms JSON DEFAULT '[]',
    sort_order INTEGER DEFAULT 0
);

-- -----------------------------------------------------
-- Таблица растений пользователя
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS user_plants (
    id VARCHAR(36) PRIMARY KEY DEFAULT (LOWER(HEX(RANDOMBLOB(16)))),
    user_id VARCHAR(36) NOT NULL,
    template_id VARCHAR(36) NOT NULL,
    custom_name VARCHAR(100) DEFAULT '',
    last_watered DATE DEFAULT CURRENT_DATE,
    last_checked DATE DEFAULT CURRENT_DATE,
    health_status VARCHAR(20) DEFAULT 'healthy'
        CHECK (health_status IN ('healthy', 'wilting', 'overwatered', 'dying', 'dead')),
    growth_stage VARCHAR(20) DEFAULT 'seed'
        CHECK (growth_stage IN ('seed', 'seedling', 'growing', 'mature', 'flowering')),
    growth_progress FLOAT DEFAULT 0.0,
    current_light_level VARCHAR(20) DEFAULT 'medium'
        CHECK (current_light_level IN ('low', 'medium', 'high')),
    location VARCHAR(50) DEFAULT 'room',
    acquired_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_alive BOOLEAN DEFAULT 1,
    death_cause VARCHAR(50),
    death_date DATE,
    times_reborn INTEGER DEFAULT 0,
    times_flowered INTEGER DEFAULT 0,
    last_advice_shown DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (template_id) REFERENCES plant_templates(id)
);

-- -----------------------------------------------------
-- Таблица достижений
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS achievements (
    id VARCHAR(36) PRIMARY KEY DEFAULT (LOWER(HEX(RANDOMBLOB(16)))),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    requirement_type VARCHAR(50),
    target_value INTEGER,
    reward_coins INTEGER DEFAULT 50,
    reward_xp INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT 1,
    sort_order INTEGER DEFAULT 0
);

-- -----------------------------------------------------
-- Таблица прогресса достижений пользователя
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS user_achievements (
    user_id VARCHAR(36) NOT NULL,
    achievement_id VARCHAR(36) NOT NULL,
    current_progress INTEGER DEFAULT 0,
    is_completed BOOLEAN DEFAULT 0,
    completed_at DATE,
    claimed BOOLEAN DEFAULT 0,
    PRIMARY KEY (user_id, achievement_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (achievement_id) REFERENCES achievements(id) ON DELETE CASCADE
);

-- -----------------------------------------------------
-- Таблица уровней
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS level_requirements (
    level INTEGER PRIMARY KEY,
    required_xp INTEGER NOT NULL,
    reward_coins INTEGER DEFAULT 0,
    reward_new_plant_slot BOOLEAN DEFAULT 0,
    reward_title VARCHAR(100)
);

-- -----------------------------------------------------
-- Таблица истории ошибок (для умных советов)
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS user_mistakes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(36) NOT NULL,
    plant_id VARCHAR(36) NOT NULL,
    mistake_type VARCHAR(50) NOT NULL,
    occurred_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    was_advice_shown BOOLEAN DEFAULT 0,
    advice_tip_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (plant_id) REFERENCES user_plants(id) ON DELETE CASCADE
);

-- -----------------------------------------------------
-- Таблица советов
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS tips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tip_type VARCHAR(50) NOT NULL,
    title VARCHAR(100),
    message TEXT NOT NULL,
    is_positive BOOLEAN DEFAULT 0
);

-- -----------------------------------------------------
-- Таблица кастомизации (открываемые предметы)
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS customizations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type VARCHAR(20) NOT NULL,
    name VARCHAR(100) NOT NULL,
    image_path VARCHAR(255),
    unlock_level INTEGER DEFAULT 1,
    unlock_achievement_id VARCHAR(36),
    price_coins INTEGER DEFAULT 0,
    is_default BOOLEAN DEFAULT 0,
    FOREIGN KEY (unlock_achievement_id) REFERENCES achievements(id)
);

-- -----------------------------------------------------
-- Таблица владения кастомизацией пользователем
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS user_customizations (
    user_id VARCHAR(36) NOT NULL,
    customization_id INTEGER NOT NULL,
    is_equipped BOOLEAN DEFAULT 0,
    acquired_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, customization_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (customization_id) REFERENCES customizations(id) ON DELETE CASCADE
);

-- =====================================================
-- ИНДЕКСЫ
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_plants_user ON user_plants(user_id);
CREATE INDEX IF NOT EXISTS idx_user_plants_alive ON user_plants(is_alive);
CREATE INDEX IF NOT EXISTS idx_player_profiles_level ON player_profiles(level);
CREATE INDEX IF NOT EXISTS idx_user_achievements_user ON user_achievements(user_id);
CREATE INDEX IF NOT EXISTS idx_user_mistakes_user ON user_mistakes(user_id);

-- Уровни
INSERT OR IGNORE INTO level_requirements (level, required_xp, reward_coins, reward_new_plant_slot, reward_title) VALUES
(1, 0, 0, 0, '🌱 Новичок'),
(2, 100, 50, 1, '🌿 Садовод'),
(3, 250, 100, 0, '🍃 Любитель'),
(4, 500, 150, 1, '🌸 Ценитель'),
(5, 1000, 200, 0, '🌳 Профи');

-- Советы
INSERT OR IGNORE INTO tips (tip_type, title, message, is_positive) VALUES
('overwater', '💧 Перелив', 'Ой, кажется, ты слишком любишь свой цветок. Перелив опаснее засухи!', 0),
('drought', '🏜️ Засуха', 'Пить хочется... Пора поливать!', 0),
('light', '☀️ Свет', 'Кажется, твоему другу не нравится его место.', 0),
('cold', '❌ Сквозняк', 'Бр-р, холодно! Убери цветок от окна.', 0),
('death_first', '💔 Первая потеря', 'Ничего страшного! Посади новый цветок.', 0),
('perfect_water', '✨ Идеально!', 'Ты чувствуешь своего зелёного друга!', 1),
('healed', '🎉 Выздоровел!', 'Ура! Снова здоров. Горжусь тобой!', 1),
('flowered', '🌸 Красота!', 'Смотри-ка, цветок! Ты делаешь всё правильно.', 1);

-- Базовая кастомизация
INSERT OR IGNORE INTO customizations (type, name, image_path, unlock_level, is_default) VALUES
('pot', 'Стандартный горшок', '/static/pots/default.png', 1, 1),
('watering_can', 'Стандартная лейка', '/static/cans/default.png', 1, 1);