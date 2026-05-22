PRAGMA foreign_keys = ON;  -- Включение поддержки внешних ключей

-- -----------------------------------------------------
-- Таблица пользователей (учетные записи)
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
-- Таблица сессий (поддержание входа)
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
-- Таблица профилей игроков
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS player_profiles (
    user_id VARCHAR(36) PRIMARY KEY,
    display_name VARCHAR(50),
    current_level INTEGER DEFAULT 1,
    max_plants_slots INTEGER DEFAULT 1,
    total_plants_grown INTEGER DEFAULT 0,
    total_waterings INTEGER DEFAULT 0,
    total_mistakes INTEGER DEFAULT 0,
    total_deaths INTEGER DEFAULT 0,
    current_plants_count INTEGER DEFAULT 0,
    tutorial_completed BOOLEAN DEFAULT 0,
    last_entry DATE DEFAULT CURRENT_DATE,
    consecutive_days INTEGER DEFAULT 1,
    best_streak INTEGER DEFAULT 1,
    unlocked_pots TEXT DEFAULT '["standard"]',
    unlocked_watering_cans TEXT DEFAULT '["standard"]',
    current_pot VARCHAR(50) DEFAULT 'standard',
    current_watering_can VARCHAR(50) DEFAULT 'standard',
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
    disease TEXT DEFAULT '',
    why_disease TEXT DEFAULT '',
    water_interval_min INTEGER,
    water_interval_max INTEGER,
    light_requirement VARCHAR(20) CHECK (light_requirement IN ('low', 'medium', 'high')),
    humidity_preference VARCHAR(20) CHECK (humidity_preference IN ('low', 'medium', 'high')),
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
    has_perfect_growth BOOLEAN DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (template_id) REFERENCES plant_templates(id)
);

-- -----------------------------------------------------
-- Таблица достижений (справочник)
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS achievements (
    id VARCHAR(36) PRIMARY KEY DEFAULT (LOWER(HEX(RANDOMBLOB(16)))),
    name VARCHAR(100) UNIQUE NOT NULL,
    requirement_type VARCHAR(50),
    target_value INTEGER,
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
    PRIMARY KEY (user_id, achievement_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (achievement_id) REFERENCES achievements(id) ON DELETE CASCADE
);

-- -----------------------------------------------------
-- Таблица требований к уровням (задания)
-- -----------------------------------------------------
-- Назначение: Определение заданий для каждого уровня (1-5)
-- За выполнение заданий даются дизайны и слоты
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS level_requirements (
    level INTEGER PRIMARY KEY,

    -- ЗАДАНИЕ 1
    quest1_type VARCHAR(50),
    quest1_target INTEGER,
    quest1_description TEXT,

    -- ЗАДАНИЕ 2
    quest2_type VARCHAR(50),
    quest2_target INTEGER,
    quest2_description TEXT,

    -- ЗАДАНИЕ 3 (может быть NULL)
    quest3_type VARCHAR(50),
    quest3_target INTEGER,
    quest3_description TEXT,

    -- НАГРАДА
    reward_type VARCHAR(50),
    reward_value TEXT,
    reward_description TEXT
);

-- -----------------------------------------------------
-- Таблица прогресса выполнения заданий пользователя
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS user_level_progress (
    user_id VARCHAR(36) NOT NULL,
    level INTEGER NOT NULL,
    quest1_progress INTEGER DEFAULT 0,
    quest1_completed BOOLEAN DEFAULT 0,
    quest2_progress INTEGER DEFAULT 0,
    quest2_completed BOOLEAN DEFAULT 0,
    quest3_progress INTEGER DEFAULT 0,
    quest3_completed BOOLEAN DEFAULT 0,
    level_completed BOOLEAN DEFAULT 0,
    reward_claimed BOOLEAN DEFAULT 0,
    completed_at DATE,
    PRIMARY KEY (user_id, level),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);


-- -----------------------------------------------------
-- Таблица истории ошибок
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
-- Индексы
-- -----------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_plants_user ON user_plants(user_id);
CREATE INDEX IF NOT EXISTS idx_user_plants_alive ON user_plants(is_alive);
CREATE INDEX IF NOT EXISTS idx_player_profiles_level ON player_profiles(current_level);
CREATE INDEX IF NOT EXISTS idx_user_achievements_user ON user_achievements(user_id);
CREATE INDEX IF NOT EXISTS idx_user_mistakes_user ON user_mistakes(user_id);
CREATE INDEX IF NOT EXISTS idx_user_level_progress_user ON user_level_progress(user_id);