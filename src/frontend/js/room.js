
const API_BASE_URL = 'http://localhost:5000/api';

/** Эталонный размер сцены комнаты (координаты слотов в room.css) */
const ROOM_DESIGN_WIDTH = 1280;
const ROOM_DESIGN_HEIGHT = 720;
const ZOOM_DESIGN_WIDTH = 1000;
const ZOOM_DESIGN_HEIGHT = 500;
/** Доля экрана под окно зума (меньше = компактнее) */
const ZOOM_VIEWPORT_FILL = 0.75;
/** Минимальная высота верхней полосы (px), чтобы показать логотип */
const LETTERBOX_LOGO_MIN_HEIGHT = 88;

/** Размеры зума в % от эталона 1000×500 (cqw/cqh внутри #zoomStage) */
function zoomCqw(px) {
    return `calc(${px} / ${ZOOM_DESIGN_WIDTH} * 100cqw)`;
}

function zoomCqh(px) {
    return `calc(${px} / ${ZOOM_DESIGN_HEIGHT} * 100cqh)`;
}

function updateRoomScale() {
    const scale = Math.min(
        window.innerWidth / ROOM_DESIGN_WIDTH,
        window.innerHeight / ROOM_DESIGN_HEIGHT
    );
    const scaledW = ROOM_DESIGN_WIDTH * scale;
    const scaledH = ROOM_DESIGN_HEIGHT * scale;
    const letterboxX = Math.max(0, (window.innerWidth - scaledW) / 2);
    const letterboxY = Math.max(0, (window.innerHeight - scaledH) / 2);

    const zoomScale = Math.min(
        (window.innerWidth * ZOOM_VIEWPORT_FILL) / ZOOM_DESIGN_WIDTH,
        (window.innerHeight * ZOOM_VIEWPORT_FILL) / ZOOM_DESIGN_HEIGHT
    );

    document.documentElement.style.setProperty('--room-scale', String(scale));
    document.documentElement.style.setProperty('--ui-scale', String(scale));
    document.documentElement.style.setProperty('--zoom-scale', String(zoomScale));
    document.documentElement.style.setProperty('--letterbox-x', `${letterboxX}px`);
    document.documentElement.style.setProperty('--letterbox-y', `${letterboxY}px`);
    document.body.classList.toggle('letterbox-logo-visible', letterboxY >= LETTERBOX_LOGO_MIN_HEIGHT);
}

function getAuthToken() {
    return localStorage.getItem('session_token');
}

function getAuthHeaders() {
    const headers = {
        'Content-Type': 'application/json'
    };
    const token = getAuthToken();
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
}

// Добавь эти функции в начало room.js

// Сохранить состояние на сервер
async function saveStateToServer() {
    if (!currentUser) return;

    const stateToSave = {
        slotData: slotData,
        currentLevel: currentLevel,
        achievements: {}
    };

    // Собираем достижения
    const achievements = ['caring_parent', 'collector', 'flora_guard', 'patient_gardener', 'oops_error', 'all_lost'];
    achievements.forEach(id => {
        stateToSave.achievements[id] = localStorage.getItem(`achievement_unlocked_${currentUser}_${id}`) === 'true';
    });

    try {
        const response = await fetch(`${API_BASE_URL}/game/save`, {
            method: 'POST',
            headers: getAuthHeaders(),
            credentials: 'include',
            body: JSON.stringify(stateToSave)
        });
        const data = await response.json();
        if (!data.success) {
            console.warn('Не удалось сохранить состояние на сервер');
        }
    } catch (error) {
        console.error('Ошибка сохранения на сервер:', error);
    }
}

// Загрузить состояние с сервера
async function loadStateFromServer() {
    if (!currentUser) return false;

    try {
        const response = await fetch(`${API_BASE_URL}/game/load`, {
            method: 'GET',
            headers: getAuthHeaders(),
            credentials: 'include'
        });
        const data = await response.json();

        if (data.success && Object.keys(data.slotData).length > 0) {
            // Загружаем состояние сада
            Object.assign(slotData, data.slotData);

            // Загружаем уровень
            if (data.currentLevel) {
                currentLevel = data.currentLevel;
                localStorage.setItem(`currentLevel_${currentUser}`, String(currentLevel));
                updateLevelCircle(currentLevel);
            }

            // Загружаем достижения
            if (data.achievements) {
                for (const [id, unlocked] of Object.entries(data.achievements)) {
                    if (unlocked) {
                        localStorage.setItem(`achievement_unlocked_${currentUser}_${id}`, 'true');
                    }
                }
            }

            // Перерисовываем все слоты
            slots.forEach(slot => {
                const name = slot.dataset.slot;
                if (slotData[name]) {
                    if (slotData[name].plant && slotData[name].plantedAt) {
                        applyGrowthFromTime(name);
                    }
                    renderSlot(slot, slotData[name]);
                    if (slotData[name].plant && slotData[name].stage < 2) {
                        scheduleGrowth(name);
                    }
                    if (slotData[name].plant) {
                        scheduleLocationCheck(name);
                    }
                }
            });

            updateAchievementsDisplay();
            renderQuests();

            return true;
        }
        return false;
    } catch (error) {
        console.error('Ошибка загрузки с сервера:', error);
        return false;
    }
}

// ИСПРАВЛЕННАЯ saveState (локальная + серверная)
function saveState() {
    // Сохраняем локально
    localStorage.setItem(`garden_${currentUser}`, JSON.stringify(slotData));

    // Сохраняем на сервер (асинхронно, не блокируем)
    saveStateToServer().catch(console.error);
}

// ИСПРАВЛЕННАЯ функция входа/инициализации
// Найди в конце room.js функцию (async function init() и замени загрузку состояния)


let PLANTS = {};
let POT_CONFIG = {};
let WATERING_CAN_CONFIG = {};
let currentLevel = 1;
let currentUser = null;
let currentZoomedPlantId = null;

// Тестовые значения — заменить на дни/часы перед релизом
const SEEDLING_MS = 10 * 1000;
const BLOOM_MS = 61 * 1000;
const WATER_TIMING_TEST = true;
const TEST_WATER_MIN_MS = 20 * 1000;
const TEST_WATER_MAX_MS = 60 * 1000;
/** Перелив: 2 полива подряд с паузой меньше TEST_WATER_MIN_MS (20 сек в тесте) */
const OVERWATER_MIN_FAST_POLIVS = 2;

const PLANT_OFFSETS = {
    1: { // Спатифиллум
        default: { bottom: '35px', width: '100px', left: '50%' },
        stages: {
            1: { bottom: '35px', width: '90px', left: '50%' },
            2: { bottom: '20px', width: '120px', left: '50%' }
        },
        diseases: {
            'желтение': { bottom: '35px', width: '90px', left: '50%' },
            'не цветет': { bottom: '35px', width: '95px', left: '50%' },
            'сохнут кончики': { bottom: '35px', width: '100px', left: '50%' }
        }
    },
    2: { // Кактус
        default: { bottom: '45px', width: '60px', left: '50%' },
        stages: {
            1: { bottom: '45px', width: '60px', left: '50%' },
            2: { bottom: '40px', width: '70px', left: '50%' }
        },
        diseases: {
            'вытягивание': { bottom: '50px', width: '30px', left: '50%' },
            'не цветет': { bottom: '45px', width: '35px', left: '50%' },
            'сморщенный стебель': { bottom: '38px', width: '34px', left: '50%' }
        }
    },
    3: { // Фикус
        default: { bottom: '40px', width: '75px', left: '50%' },
        stages: {
            1: { bottom: '40px', width: '75px', left: '50%' },
            2: { bottom: '35px', width: '125px', left: '50%' }
        },
        diseases: {
            'желтение': { bottom: '40px', width: '90px', left: '50%' },
            'пятна': { bottom: '40px', width: '100px', left: '50%' },
            'увядание': { bottom: '40px', width: '75px', left: '50%' }
        }
    }
};

function getPlantOffsets(plantId, stage, diseaseText = null) {
    const plantConfig = PLANT_OFFSETS[plantId];
    if (!plantConfig) return { bottom: '40px', width: '70px', left: '50%' };

    const normalizedStage = Number(stage);
    const stageKey = Number.isFinite(normalizedStage) ? normalizedStage : 1;

    if (diseaseText) {
        const norm = s => s.toLowerCase().replace(/ё/g, 'е');
        for (const [key, offsets] of Object.entries(plantConfig.diseases || {})) {
            if (norm(diseaseText).includes(norm(key))) {
                return offsets;
            }
        }
        if (plantConfig.stages && plantConfig.stages[stageKey]) {
            return plantConfig.stages[stageKey];
        }
        return plantConfig.default;
    }

    if (plantConfig.stages && plantConfig.stages[stageKey]) {
        return plantConfig.stages[stageKey];
    }

    return plantConfig.default;
}

const PLANT_LIFT_CONFIG = {
    1: { // Спатифиллум
        1: {
            slot: { sprout: 18, healthy: 19, 'желтение': 40, 'не цветет': 51, 'сохнут кончики': 44, dead: -42, sick: 24 },
            zoom: { sprout: 40, healthy: 37, 'желтение': 70, 'не цветет': 84, 'сохнут кончики': 75, dead: -39, sick: 70 }
        },
        2: {
            slot: { sprout: 12, healthy: 12, 'желтение': 34, 'не цветет': 45, 'сохнут кончики': 38, dead: -48, sick: 19 },
            zoom: { sprout: 30, healthy: 27, 'желтение': 62, 'не цветет': 76, 'сохнут кончики': 68, dead: -48, sick: 62 }
        },
        3: {
            slot: { sprout: 36, healthy: 37, 'желтение': 58, 'не цветет': 69, 'сохнут кончики': 63, dead: -24, sick: 37 },
            zoom: { sprout: 57, healthy: 53, 'желтение': 87, 'не цветет': 102, 'сохнут кончики': 94, dead: -21, sick: 87 }
        }
    },
    2: { // Кактус
        1: {
            slot: { sprout: 10, healthy: -28, 'вытягивание': 36, 'не цветет': 40, 'сморщенный стебель': 42, dead: -28, sick: 0 },
            zoom: { sprout: 33, healthy: -20, 'вытягивание': 70, 'не цветет': 73, 'сморщенный стебель': 74, dead: -18, sick: 50 }
        },
        2: {
            slot: { sprout: 4, healthy: -34, 'вытягивание': 30, 'не цветет': 34, 'сморщенный стебель': 36, dead: -34, sick: 0 },
            zoom: { sprout: 24, healthy: -28, 'вытягивание': 60, 'не цветет': 64, 'сморщенный стебель': 65, dead: -2, sick: 50 }
        },
        3: {
            slot: { sprout: 28, healthy: -9, 'вытягивание': 54, 'не цветет': 58, 'сморщенный стебель': 60, dead: -10, sick: 0 },
            zoom: { sprout: 52, healthy: -2, 'вытягивание': 87, 'не цветет': 90, 'сморщенный стебель': 92, dead: 0, sick: 50 }
        }
    },
    3: { // Фикус
        1: {
            slot: { sprout: -33, healthy: -19, 'желтение': 40, 'пятна': 30, 'увядание': 43, dead: -28, sick: 0 },
            zoom: { sprout: -23, healthy: -10, 'желтение': 73, 'пятна': 60, 'увядание': 77, dead: -18, sick: 50 }
        },
        2: {
            slot: { sprout: -38, healthy: -25, 'желтение': 35, 'пятна': 25, 'увядание': 38, dead: -33, sick: 0 },
            zoom: { sprout: -32, healthy: -18, 'желтение': 62, 'пятна': 50, 'увядание': 67, dead: -27, sick: 50 }
        },
        3: {
            slot: { sprout: -13, healthy: 0, 'желтение': 60, 'пятна': 50, 'увядание': 62, dead: -8, sick: 0 },
            zoom: { sprout: -4, healthy: 8, 'желтение': 92, 'пятна': 75, 'увядание': 97, dead: 0, sick: 50 }
        }
    }
};

function getPotLift(type, plantId, potNum, stage, hasDisease, disease) {
    const plant = parseInt(plantId, 10) || 1;
    const pot   = parseInt(potNum,  10) || 1;
    const normalizedStage = Number(stage);
    const stageKey = Number.isFinite(normalizedStage) ? normalizedStage : 0;
    const plantCfg = PLANT_LIFT_CONFIG[plant] || PLANT_LIFT_CONFIG[1];
    const lifts = (plantCfg[pot] || plantCfg[1])[type];

    if (!hasDisease && stageKey === 1) return lifts.sprout ?? 0;
    if (!hasDisease && stageKey >= 2) return lifts.healthy ?? 0;

    if (disease === '__dead__') return lifts.dead ?? lifts.sick ?? 0;

    if (disease) {
        for (const key of Object.keys(lifts)) {
            if (key !== 'sick' && key !== 'dead' && key !== 'sprout' && key !== 'healthy') {
                const norm = s => s.toLowerCase().replace(/ё/g, 'е');
                if (norm(disease).includes(norm(key))) return lifts[key];
            }
        }
    }
    return lifts.sick ?? 0;
}

function getSlotPlantExtraLift(plantId, potNum, stage, hasDisease, disease) {
    return getPotLift('slot', plantId, potNum, stage, hasDisease, disease);
}

function getZoomPlantLift(plantId, potNum, stage, hasDisease, disease) {
    return getPotLift('zoom', plantId, potNum, stage, hasDisease, disease);
}

const ACHIEVEMENTS_CONFIG = {
    caring_parent: {
        name: 'Заботливый родитель',
        icon: 'images/achivement/parents/Заботливый родитель.png',
        reasonImage: 'images/achivement/parents/за что.png',
        unlockImage: 'images/achivement/parents/окно получения достижения.png',
        description: 'Вырастите цветок от семечка до полной зрелости, не допустив ни одной ошибки в уходе.',
        requirement: 'Вырастить любой цветок до максимальной стадии без критических ошибок'
    },
    collector: {
        name: 'Коллекционер',
        icon: 'images/achivement/collection/Коллекционер.png',
        reasonImage: 'images/achivement/collection/за что.png',
        unlockImage: 'images/achivement/collection/окно получения достижения.png',
        description: 'Соберите полную коллекцию растений, вырастив все доступные виды.',
        requirement: 'Вырастить все 3 вида цветов до зрелости: Спатифиллум, Кактус, Фикус'
    },
    flora_guard: {
        name: 'Страж флоры',
        icon: 'images/achivement/flora/Страж флоры.png',
        reasonImage: 'images/achivement/flora/за что.png',
        unlockImage: 'images/achivement/flora/окно получения достижения.png',
        description: 'Достигните максимального уровня, показывая свою преданность растениям.',
        requirement: 'Достигнуть 5 уровня в игре'
    },
    patient_gardener: {
        name: 'Терпеливый садовод',
        icon: 'images/achivement/gardens/Терпеливый садовод.png',
        reasonImage: 'images/achivement/gardens/за что.png',
        unlockImage: 'images/achivement/gardens/окно получения достижения.png',
        description: 'Проявите терпение и заботу, ухаживая за растениями целую неделю без пропусков.',
        requirement: 'Ухаживать за растениями 7 дней подряд (с ежедневным входом)'
    },
    oops_error: {
        name: 'Упс, ошибка',
        icon: 'images/achivement/error/Упс, ошибка.png',
        reasonImage: 'images/achivement/error/за что.png',
        unlockImage: 'images/achivement/error/окно получения достижения.png',
        description: 'Каждый садовод иногда ошибается. Получите первый негативный эффект от неправильного ухода.',
        requirement: 'Получить любой негативный эффект (пожелтение, увядание, ожог)'
    },
    all_lost: {
        name: 'Ой, всё пропало',
        icon: 'images/achivement/abyss/Ой все пропало.png',
        reasonImage: 'images/achivement/abyss/за что.png',
        unlockImage: 'images/achivement/abyss/окно получения достижения.png',
        description: 'К сожалению, даже опытные садоводы теряют растения. Впервые доведите цветок до гибели.',
        requirement: 'Впервые довести цветок до полного увядания ("смерти")'
    }
};

const REWARD_IMAGES = {
    1: 'images/reward/1.png',
    2: 'images/reward/2.png',
    3: 'images/reward/3.png',
    4: 'images/reward/4.png',
    5: ['images/reward/5_1.png', 'images/reward/5_2.png']
};

async function checkAuth() {
    try {
        const response = await fetch(`${API_BASE_URL}/auth/verify`, {
            method: 'GET',
            credentials: 'include',  // Для cookie
            headers: getAuthHeaders()  // И для токена
        });

        if (!response.ok) {
            window.location.href = 'register.html';
            return false;
        }

        const data = await response.json();
        if (!data.success) {
            window.location.href = 'register.html';
            return false;
        }

        if (!localStorage.getItem('username')) {
            localStorage.setItem('username', data.username);
            localStorage.setItem('userId', data.user_id);
        }

        currentUser = localStorage.getItem('username');
        return true;
    } catch (error) {
        console.error('Ошибка проверки авторизации:', error);
        window.location.href = 'register.html';
        return false;
    }
}

async function loadPlantsCatalog() {
    try {
        const response = await fetch(`${API_BASE_URL}/plants/catalog`, {
            credentials: 'include',
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success && data.plants) {
            const plants = {};
            data.plants.forEach(plant => {
                const plantId = plant.species_id || plant.id;
                const speciesName = plant.species_name || plant.name || '';
                const folder = resolveSpeciesFolder(speciesName);
                const speciesNum = parseInt(plantId, 10);
                const sid = (speciesNum >= 1 && speciesNum <= 3) ? speciesNum
                    : (folder === 'spathiphyllum' ? 1 : folder === 'cactus' ? 2 : folder === 'ficus' ? 3 : 1);
                const assets = SPECIES_ASSETS[sid] || SPECIES_ASSETS[1];
                const plantFolder = folder || assets.plantFolder;
                const diseaseImages = { ...assets.diseaseImages };

                plants[plantId] = {
                    id: plantId,
                    name: plant.species_name || plant.name,
                    nickname: plant.nickname || plant.species_name || 'Растение',
                    description: plant.description || 'Описание отсутствует',
                    waterAdvice: plant.watering_advice || 'Поливай по графику',
                    lightAdvice: plant.light_advice || 'Обеспечь правильное освещение',
                    tips: Array.isArray(plant.tips) ? plant.tips.join('. ') : (plant.tips || 'Бережный уход - залог здоровья'),
                    waterIntervalMin: plant.water_interval_min || 24,
                    waterIntervalMax: plant.water_interval_max || 48,
                    unlockLevel: plant.unlock_level || 1,
                    plantFolder: plantFolder,
                    stages: {
                        1: `images/plant/${plantFolder}/stage/росток.png`,
                        2: `images/plant/${plantFolder}/stage/выросший.png`
                    },
                    diseaseImages: diseaseImages,
                    deadImage: assets.deadImage
                };
                ensurePlantDiseaseAssets(plants[plantId], sid);
            });
            PLANTS = plants;
            return true;
        }
        return false;
    } catch (error) {
        console.error('Ошибка загрузки растений:', error);
        return false;
    }
}


async function loadPots() {
    try {
        const response = await fetch(`${API_BASE_URL}/user/designs`, {
            credentials: 'include',
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success && data.all_pots) {
            const pots = {};
            const userLevel = data.user_level || currentLevel;

            data.all_pots.forEach(pot => {
                let potNum = parseInt(pot.id);
                const unlockLevel = pot.unlock_level || 1;
                const isUnlocked = unlockLevel <= userLevel || (data.unlocked_pots && data.unlocked_pots.includes(pot.id));

                pots[potNum] = {
                    name: pot.name,
                    img: pot.image,
                    unlockLevel: unlockLevel,
                    isUnlocked: isUnlocked
                };
            });
            POT_CONFIG = pots;
            return true;
        }
        return false;
    } catch (error) {
        console.error('Ошибка загрузки горшков:', error);
        return false;
    }
}

async function loadWateringCans() {
    try {
        const response = await fetch(`${API_BASE_URL}/user/designs`, {
            credentials: 'include',
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success && data.all_cans) {
            const cans = {};
            const userLevel = data.user_level || currentLevel;

            data.all_cans.forEach(can => {
                let canId = parseInt(can.id);
                const unlockLevel = can.unlock_level || 1;
                const isUnlocked = unlockLevel <= userLevel || (data.unlocked_cans && data.unlocked_cans.includes(can.id));

                cans[canId] = {
                    name: can.name,
                    img: can.image,
                    unlockLevel: unlockLevel,
                    isUnlocked: isUnlocked,
                    id: can.id
                };
            });
            WATERING_CAN_CONFIG = cans;
            return true;
        }
        return false;
    } catch (error) {
        console.error('Ошибка загрузки леек:', error);
        return false;
    }
}

function setDefaultPlants() {
    PLANTS = {
        1: {
            id: 1,
            name: 'Спатифиллум',
            nickname: 'Женское счастье',
            stages: {
                1: 'images/plant/spathiphyllum/stage/росток.png',
                2: 'images/plant/spathiphyllum/stage/выросший.png'
            },
            diseaseImages: {
                'желтение': 'images/plant/spathiphyllum/disease/желтение.png',
                'не цветет': 'images/plant/spathiphyllum/disease/не цветет.png',
                'сохнут кончики': 'images/plant/spathiphyllum/disease/сохнут кончики.png'
            },
            deadImage: 'images/plant/spathiphyllum/stage/спатифиллум умер.png',
            waterIntervalMin: 24,
            waterIntervalMax: 48,
            description: 'Нежный тропический гость с темно-зелеными листьями.',
            waterAdvice: 'Поливай раз в 1–2 дня, поддерживая почву слегка влажной.',
            lightAdvice: 'Не ставь под прямые солнечные лучи — будет ожог.',
            tips: 'Листья опустились? Срочно полей.',
            unlockLevel: 1,
            plantFolder: 'spathiphyllum'
        },
        2: {
            id: 2,
            name: 'Кактус',
            nickname: 'Колючий стоик',
            stages: {
                1: 'images/plant/cactus/stage/росток.png',
                2: 'images/plant/cactus/stage/выросший.png'
            },
            diseaseImages: {
                'вытягивание': 'images/plant/cactus/disease/вытягивание.png',
                'не цветет': 'images/plant/cactus/disease/не цветет.png',
                'сморщенный стебель': 'images/plant/cactus/disease/сморщенный стебель.png'
            },
            deadImage: 'images/plant/cactus/stage/кактус умер.png',
            waterIntervalMin: 168,
            waterIntervalMax: 240,
            description: 'Пухлый зеленый шар с выраженными ребрами и крепкими колючками.',
            waterAdvice: 'Забудь про частые поливы! Дай земле полностью просохнуть.',
            lightAdvice: 'Нуждается в ярком освещении 6–8 часов в день.',
            tips: 'Тельце стало мягким и потемнело у корней? Это перелив.',
            unlockLevel: 3,
            plantFolder: 'cactus'
        },
        3: {
            id: 3,
            name: 'Фикус',
            nickname: 'Хранитель домашнего очага',
            stages: {
                1: 'images/plant/ficus/stage/росток.png',
                2: 'images/plant/ficus/stage/выросший.png'
            },
            diseaseImages: {
                'желтение': 'images/plant/ficus/disease/желтение.png',
                'пятна': 'images/plant/ficus/disease/пятна.png',
                'увядание': 'images/plant/ficus/disease/увядание.png'
            },
            deadImage: 'images/plant/ficus/stage/фикус умер.png',
            waterIntervalMin: 72,
            waterIntervalMax: 96,
            description: 'Величественное дерево в миниатюре с плотными листьями.',
            waterAdvice: 'Поливай раз в 3–4 дня, по мере просыхания верхнего слоя почвы.',
            lightAdvice: 'Не хватает света? Поставь ближе к окну.',
            tips: 'Сбрасывает листья? Не любит сквозняков.',
            unlockLevel: 5,
            plantFolder: 'ficus'
        }
    };
}

function setDefaultPots() {
    POT_CONFIG = {
        1: { name: 'Горшок 1', img: '/images/pot/горшок1.png', unlockLevel: 1, isUnlocked: true },
        2: { name: 'Горшок 2', img: '/images/pot/горшок2.png', unlockLevel: 2, isUnlocked: currentLevel >= 2 },
        3: { name: 'Горшок 3', img: '/images/pot/горшок3.png', unlockLevel: 6, isUnlocked: currentLevel >= 6 }
    };
}

function setDefaultWateringCans() {
    WATERING_CAN_CONFIG = {
        1: { name: 'Лейка', img: '/images/water can/лейка.png', unlockLevel: 1, isUnlocked: true, id: '1' },
        2: { name: 'Лейка 2', img: '/images/water can/лейка2.png', unlockLevel: 4, isUnlocked: currentLevel >= 4, id: '2' }
    };
}

const STAGE_NAMES = ['🌰 Семечко посажено', '🌱 Росток', '🌸 Расцвёл'];

const LEVEL_REWARDS = {
    2: '🎉 Получен новый горшок (Горшок 2)!',
    3: '🌵 Получен новый цветок (Кактус)!',
    4: '💧 Получена новая лейка (Лейка 2)!',
    5: '🌿 Получен новый цветок (Фикус)!',
    6: '🏆 Получен легендарный Горшок 3 и ачивка "Страж флоры"!'
};

const slotData = {};
let activeSlot = null;
let zoomedSlot = null;

const popupQueue = [];
let popupShowing = false;

const slots = document.querySelectorAll('.pot-slot');
const modalPlacePot    = document.getElementById('modalPlacePot');
const modalPickFlower  = document.getElementById('modalPickFlower');
const zoomOverlay      = document.getElementById('zoomOverlay');
const modalAchievements= document.getElementById('modalAchievements');
const tutorialOverlay  = document.getElementById('tutorialOverlay');
const modalLevelReward = document.getElementById('modalLevelReward');
const modalWaterCan = document.getElementById('modalWaterCan');
const modalRepot = document.getElementById('modalRepot');
const modalMovePlant = document.getElementById('modalMovePlant');

function showNotification(message, isError = false) {
    const n = document.getElementById('notification');
    if (!n) return;
    n.querySelector('.notif-icon').textContent = isError ? '❌' : '✅';
    n.querySelector('.notif-text').textContent = message;
    n.classList.add('show');
    setTimeout(() => n.classList.remove('show'), 2800);
}

function openModal(el) { if (el) el.classList.add('active'); }
function closeModal(el) { if (el) el.classList.remove('active'); }

function showAchievementReasonToast(achievementId) {
    const config = ACHIEVEMENTS_CONFIG[achievementId];
    if (!config) return;

    const unlocked = localStorage.getItem(`achievement_unlocked_${currentUser}_${achievementId}`) === 'true';
    if (!unlocked) return;

    const toast = document.getElementById('achievementToast');
    const toastImg = document.getElementById('achievementToastImg');
    if (!toast || !toastImg) return;

    toastImg.src = config.reasonImage;
    toast.classList.add('show');

    setTimeout(() => {
        toast.classList.remove('show');
    }, 2500);
}

function showAchievementUnlockToast(achievementId) {
    const config = ACHIEVEMENTS_CONFIG[achievementId];
    if (!config) return;

    const toast = document.getElementById('achievementUnlockToast');
    const toastImg = document.getElementById('achievementUnlockToastImg');
    if (!toast || !toastImg) return;

    toastImg.src = config.unlockImage;
    toast.classList.add('show');

    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

function showRewardToast(level) {
    const toast = document.getElementById('rewardToast');
    const toastImg = document.getElementById('rewardToastImg');
    if (!toast || !toastImg) return;

    const reward = REWARD_IMAGES[level];
    if (!reward) return;

    if (Array.isArray(reward)) {
        let index = 0;
        function showNext() {
            if (index < reward.length) {
                toastImg.src = reward[index];
                toast.classList.add('show');
                setTimeout(() => {
                    toast.classList.remove('show');
                    index++;
                    setTimeout(showNext, 500);
                }, 2500);
            }
        }
        showNext();
    } else {
        toastImg.src = reward;
        toast.classList.add('show');
        setTimeout(() => {
            toast.classList.remove('show');
        }, 2500);
    }
}

function getAchievementIdByName(name) {
    for (const [id, config] of Object.entries(ACHIEVEMENTS_CONFIG)) {
        if (config.name === name || name.includes(config.name)) {
            return id;
        }
    }
    return null;
}

function updateAchievementsDisplay() {
    const achievements = document.querySelectorAll('.achievement-card');
    achievements.forEach(item => {
        const id = item.dataset.id;
        const unlocked = localStorage.getItem(`achievement_unlocked_${currentUser}_${id}`);
        const config = ACHIEVEMENTS_CONFIG[id];

        if (unlocked === 'true') {
            item.classList.remove('locked');
            const img = item.querySelector('img');
            if (img && config) {
                img.src = config.icon;
                img.style.filter = 'none';
                img.style.opacity = '1';
            }
        } else {
            item.classList.add('locked');
            const img = item.querySelector('img');
            if (img) {
                img.style.filter = 'grayscale(1)';
                img.style.opacity = '0.5';
            }
        }
    });
}

function initAchievementsClick() {
    const achievements = document.querySelectorAll('.achievement-card');
    achievements.forEach(item => {
        item.addEventListener('click', (e) => {
            e.stopPropagation();
            const id = item.dataset.id;
            showAchievementReasonToast(id);
        });
    });
}

function getUnlockedAchievementsCount() {
    let count = 0;
    const achievements = ['caring_parent', 'collector', 'flora_guard', 'patient_gardener', 'oops_error', 'all_lost'];
    achievements.forEach(id => {
        if (localStorage.getItem(`achievement_unlocked_${currentUser}_${id}`) === 'true') count++;
    });
    return count;
}

function checkAchievement_caringParent(slotName, data) {
    if (data.stage === 2 && !data.hasDisease && data.hadMistakes !== true) {
        const alreadyHave = localStorage.getItem(`achievement_unlocked_${currentUser}_caring_parent`);
        if (!alreadyHave) {
            localStorage.setItem(`achievement_unlocked_${currentUser}_caring_parent`, 'true');
            enqueuePopup('achievement', {
                name: 'Заботливый родитель',
                id: 'caring_parent'
            });
            updateAchievementsDisplay();
            return true;
        }
    }
    return false;
}

function checkAchievement_collector() {
    const grownSpecies = new Set();

    Object.entries(slotData).forEach(([slotName, data]) => {
        if (data && data.plant && data.stage === 2) {
            const plantId = parseInt(data.plant);
            grownSpecies.add(plantId);
        }
    });

    const requiredSpecies = [1, 2, 3];
    const allGrown = requiredSpecies.every(species => grownSpecies.has(species));

    if (allGrown) {
        const alreadyHave = localStorage.getItem(`achievement_unlocked_${currentUser}_collector`);
        if (!alreadyHave) {
            localStorage.setItem(`achievement_unlocked_${currentUser}_collector`, 'true');
            enqueuePopup('achievement', {
                name: 'Коллекционер',
                id: 'collector'
            });
            updateAchievementsDisplay();
            return true;
        }
    }
    return false;
}

function checkAchievement_level(level) {
    if (level >= 5) {
        const alreadyHave = localStorage.getItem(`achievement_unlocked_${currentUser}_flora_guard`);
        if (!alreadyHave) {
            localStorage.setItem(`achievement_unlocked_${currentUser}_flora_guard`, 'true');
            enqueuePopup('achievement', {
                name: 'Страж флоры',
                id: 'flora_guard'
            });
            updateAchievementsDisplay();
            return true;
        }
    }
    return false;
}

function checkAchievement_streak(streak) {
    if (streak >= 7) {
        const alreadyHave = localStorage.getItem(`achievement_unlocked_${currentUser}_patient_gardener`);
        if (!alreadyHave) {
            localStorage.setItem(`achievement_unlocked_${currentUser}_patient_gardener`, 'true');
            enqueuePopup('achievement', {
                name: 'Терпеливый садовод',
                id: 'patient_gardener'
            });
            updateAchievementsDisplay();
            return true;
        }
    }
    return false;
}

function checkAchievement_death() {
    const alreadyHave = localStorage.getItem(`achievement_unlocked_${currentUser}_all_lost`);
    if (!alreadyHave) {
        localStorage.setItem(`achievement_unlocked_${currentUser}_all_lost`, 'true');
        enqueuePopup('achievement', {
            name: 'Ой, всё пропало',
            id: 'all_lost'
        });
        updateAchievementsDisplay();
        return true;
    }
    return false;
}

function checkAchievement_negativeEffect() {
    const alreadyHave = localStorage.getItem(`achievement_unlocked_${currentUser}_oops_error`);
    if (!alreadyHave) {
        localStorage.setItem(`achievement_unlocked_${currentUser}_oops_error`, 'true');
        enqueuePopup('achievement', {
            name: 'Упс, ошибка',
            id: 'oops_error'
        });
        updateAchievementsDisplay();
        return true;
    }
    return false;
}

function checkAllAchievementsOnBloom(slotName, data) {
    checkAchievement_caringParent(slotName, data);
    checkAchievement_collector();
}

const SLOT_LIGHT = {
    'windowsill-1': 'high',
    'windowsill-2': 'high',
    'windowsill-3': 'medium',
    'desk-left': 'medium',
    'desk-right-1': 'low',
    'desk-right-2': 'low'
};

const PLANT_LIGHT_REQ = {
    1: 'low',
    2: 'high',
    3: 'medium'
};

const PLANT_DISEASES = {
    1: {
        too_light: '🍃 желтение — листья желтеют от солнечного ожога',
        big_pot: '🍃 не цветет — слишком большой горшок',
        under_watered: '🍃 сохнут кончики листьев — недостаток полива',
        overwatered: '🍃 желтение — листья желтеют от перелива'
    },
    2: {
        too_dark: '🌵 Вытягивание и бледность стебля — не хватает света',
        no_flower: '🌵 не цветет — нехватка света',
        under_watered: '🌵 Сморщенный стебель — недостаточный полив',
        overwatered: '🌵 Сморщенный стебель — перелив или застой воды'
    },
    3: {
        too_light: '🍂 Пятна на листьях — солнечный ожог',
        under_watered: '🍂 Желтеют листья — недостаток полива',
        overwatered: '🍂 Увядание листьев — перелив'
    }
};

const PLANT_DISEASE_TO_IMAGE_KEY = {
    1: { too_light: 'желтение', big_pot: 'не цветет', under_watered: 'сохнут кончики', overwatered: 'желтение' },
    2: { too_dark: 'вытягивание', no_flower: 'не цветет', under_watered: 'сморщенный стебель', overwatered: 'сморщенный стебель' },
    3: { too_light: 'пятна', under_watered: 'желтение', overwatered: 'увядание' }
};

const SPECIES_ASSETS = {
    1: {
        plantFolder: 'spathiphyllum',
        diseaseImages: {
            'желтение': 'images/plant/spathiphyllum/disease/желтение.png',
            'не цветет': 'images/plant/spathiphyllum/disease/не цветет.png',
            'сохнут кончики': 'images/plant/spathiphyllum/disease/сохнут кончики.png'
        },
        deadImage: 'images/plant/spathiphyllum/stage/спатифиллум умер.png'
    },
    2: {
        plantFolder: 'cactus',
        diseaseImages: {
            'вытягивание': 'images/plant/cactus/disease/вытягивание.png',
            'не цветет': 'images/plant/cactus/disease/не цветет.png',
            'сморщенный стебель': 'images/plant/cactus/disease/сморщенный стебель.png'
        },
        deadImage: 'images/plant/cactus/stage/кактус умер.png'
    },
    3: {
        plantFolder: 'ficus',
        diseaseImages: {
            'желтение': 'images/plant/ficus/disease/желтение.png',
            'пятна': 'images/plant/ficus/disease/пятна.png',
            'увядание': 'images/plant/ficus/disease/увядание.png'
        },
        deadImage: 'images/plant/ficus/stage/фикус умер.png'
    }
};

function resolveSpeciesFolder(speciesName) {
    const n = String(speciesName || '').toLowerCase().replace(/ё/g, 'е');
    if (n.includes('спатифилл') || n.includes('spathiphyllum')) return 'spathiphyllum';
    if (n.includes('кактус') || n.includes('cactus')) return 'cactus';
    if (n.includes('фикус') || n.includes('ficus')) return 'ficus';
    return null;
}

function resolveSpeciesId(plantKey, plant) {
    const n = parseInt(plantKey, 10);
    if (n >= 1 && n <= 3) return n;
    const folder = plant?.plantFolder;
    if (folder === 'spathiphyllum') return 1;
    if (folder === 'cactus') return 2;
    if (folder === 'ficus') return 3;
    const name = String(plant?.name || '').toLowerCase().replace(/ё/g, 'е');
    if (name.includes('спатифилл') || name.includes('spathiphyllum')) return 1;
    if (name.includes('кактус') || name.includes('cactus')) return 2;
    if (name.includes('фикус') || name.includes('ficus')) return 3;
    return Number.isFinite(n) && n > 0 ? n : 1;
}

function ensurePlantDiseaseAssets(plant, speciesId) {
    if (!plant) return;
    const sid = speciesId >= 1 && speciesId <= 3 ? speciesId : 1;
    const assets = SPECIES_ASSETS[sid];
    if (!assets) return;
    if (!plant.diseaseImages || Object.keys(plant.diseaseImages).length === 0) {
        plant.diseaseImages = { ...assets.diseaseImages };
    }
    if (!plant.plantFolder || plant.plantFolder === 'default') {
        plant.plantFolder = assets.plantFolder;
    }
    if (!plant.deadImage) {
        plant.deadImage = assets.deadImage;
    }
}

const LOCATION_DISEASE_TYPES = ['too_light', 'too_dark', 'no_flower', 'big_pot'];
const WATER_DISEASE_TYPES = ['under_watered', 'overwatered'];

function getWaterMinMs(plant) {
    return WATER_TIMING_TEST ? TEST_WATER_MIN_MS : (plant.waterIntervalMin || 24) * 3600000;
}

function getWaterMaxMs(plant) {
    return WATER_TIMING_TEST ? TEST_WATER_MAX_MS : (plant.waterIntervalMax || 48) * 3600000;
}

function msSinceLastWater(data) {
    if (!data?.lastWateredAt) return Infinity;
    return Date.now() - data.lastWateredAt;
}

function hasRegularWatering(data, plant) {
    if (!data?.lastWateredAt || !plant) return false;
    return msSinceLastWater(data) <= getWaterMaxMs(plant);
}

function countRecentFastWaterings(data, plant) {
    if (!data?.wateringHistory?.length) return 0;
    const minMs = getWaterMinMs(plant);
    return data.wateringHistory.slice(-3).filter(w => {
        const gap = w.gapMs != null ? w.gapMs : (w.intervalMs != null ? w.intervalMs : Infinity);
        return gap < minMs;
    }).length;
}

function hasOverwaterRisk(data, plant) {
    return countRecentFastWaterings(data, plant) >= OVERWATER_MIN_FAST_POLIVS;
}

function getBloomBlockReason(data, plant) {
    if (!data || !plant) return 'растение не готово';
    if (data.hasDisease) return 'не может расцвести из-за болезни';
    if (hasOverwaterRisk(data, plant)) return 'не может расцвести — слишком частый полив';
    if (!hasRegularWatering(data, plant)) return 'не может расцвести — нужен регулярный полив';
    return null;
}

function getDiseaseTypeFromMessage(plantKey, diseaseMsg) {
    const diseases = PLANT_DISEASES[plantKey];
    if (!diseases || !diseaseMsg) return null;
    for (const [type, msg] of Object.entries(diseases)) {
        if (msg === diseaseMsg) return type;
    }
    return null;
}

function recordWateringGap(data, now) {
    if (!data.wateringHistory) data.wateringHistory = [];
    if (data.lastWateredAt) {
        const gapMs = now - data.lastWateredAt;
        data.wateringHistory.push({ time: now, gapMs });
        if (data.wateringHistory.length > 5) data.wateringHistory.shift();
    }
}

function syncSlotHealthChecks(slotName) {
    const data = slotData[slotName];
    if (!data?.plant || data.stage < 1) return;
    checkWateringHealth(slotName, data);
    checkLocationDisease(slotName);
}

function isWaterDisease(plantKey, diseaseText) {
    if (!diseaseText) return false;
    const diseases = PLANT_DISEASES[plantKey];
    if (!diseases) return false;
    const text = normalizePlantText(diseaseText);
    for (const type of WATER_DISEASE_TYPES) {
        const msg = diseases[type];
        if (!msg) continue;
        const norm = normalizePlantText(msg);
        if (text === norm || text.includes(norm) || norm.includes(text)) return true;
    }
    return false;
}

function applyPlantDisease(slotName, data, diseaseType, source) {
    const plant = PLANTS[data.plant];
    const plantKey = resolveSpeciesId(data.plant, plant);
    const msg = PLANT_DISEASES[plantKey]?.[diseaseType];
    if (!msg || data.hasDisease || data.stage < 1) return false;

    data.hasDisease = true;
    data.hadMistakes = true;
    data.disease = msg;
    data.diseaseType = diseaseType;
    data.diseaseSource = source;
    data.diseaseStartTime = Date.now();
    showNotification(`⚠️ ${plant?.name || 'Растение'}: ${msg}`, true);
    saveState();
    checkAchievement_negativeEffect();
    refreshPlantVisual(slotName);
    return true;
}

function isLocationBasedDisease(plantKey, diseaseText) {
    if (!diseaseText || diseaseText === '__dead__') return false;
    const diseases = PLANT_DISEASES[plantKey];
    if (!diseases) return false;
    const text = normalizePlantText(diseaseText);
    for (const type of LOCATION_DISEASE_TYPES) {
        const msg = diseases[type];
        if (!msg) continue;
        const normMsg = normalizePlantText(msg);
        if (text === normMsg || text.includes(normMsg) || normMsg.includes(text)) {
            return true;
        }
    }
    return false;
}

function normalizePlantText(value) {
    return String(value).toLowerCase().replace(/ё/g, 'е').trim();
}

function resolvePlantStage(data) {
    const stage = Number(data?.stage);
    return Number.isFinite(stage) ? stage : 0;
}

function getHealthyStageImage(plant, stage) {
    if (!plant?.stages) return null;
    if (stage <= 1) return plant.stages[1] || null;
    return plant.stages[2] || plant.stages[1] || null;
}

function getDiseaseImageKey(plant, diseaseText, plantId = null, diseaseType = null) {
    if (!plant?.diseaseImages) return null;

    const pid = plantId || resolveSpeciesId(plant.id, plant);
    const typeMap = PLANT_DISEASE_TO_IMAGE_KEY[pid];

    if (diseaseType && typeMap?.[diseaseType] && plant.diseaseImages[typeMap[diseaseType]]) {
        return typeMap[diseaseType];
    }

    if (!diseaseText) return null;

    const text = normalizePlantText(diseaseText);

    if (plant.diseaseImages[diseaseText]) {
        return diseaseText;
    }

    if (typeMap) {
        for (const [type, imageKey] of Object.entries(typeMap)) {
            const msg = PLANT_DISEASES[pid]?.[type];
            if (!msg || !imageKey) continue;
            const normMsg = normalizePlantText(msg);
            if (text === normMsg || text.includes(normMsg) || normMsg.includes(text)) {
                return imageKey;
            }
        }
    }

    for (const key of Object.keys(plant.diseaseImages)) {
        const normalizedKey = normalizePlantText(key);
        if (text === normalizedKey || text.includes(normalizedKey)) {
            return key;
        }
    }

    return null;
}

function getDiseaseImage(plant, diseaseText, plantId = null, diseaseType = null) {
    if (!plant?.diseaseImages || (!diseaseText && !diseaseType)) return null;

    const pid = plantId || resolveSpeciesId(plant.id, plant);
    ensurePlantDiseaseAssets(plant, pid);

    const imageKey = getDiseaseImageKey(plant, diseaseText, pid, diseaseType);
    if (imageKey && plant.diseaseImages[imageKey]) {
        return plant.diseaseImages[imageKey];
    }

    return null;
}

function getFirstDiseaseImage(plant) {
    const images = plant?.diseaseImages;
    if (!images) return null;
    const paths = Object.values(images);
    return paths.length ? paths[0] : null;
}

/**
 * Единые метаданные для картинки и позиции (слот + зум).
 * layout: sprout | bloom | disease | dead
 */
function getPlantVisualMeta(plant, data) {
    if (!plant || !data?.plant) return null;

    const stage = resolvePlantStage(data);
    if (stage < 1) return null;

    const plantId = resolveSpeciesId(data.plant, plant);
    ensurePlantDiseaseAssets(plant, plantId);
    const pot = Number(data.pot) || 1;

    if (data.disease === '__dead__') {
        return {
            imageUrl: plant.deadImage || getHealthyStageImage(plant, 1),
            stage,
            plantId,
            pot,
            layout: 'dead',
            disease: '__dead__'
        };
    }

    if (data.hasDisease && data.disease) {
        const diseaseImg = getDiseaseImage(plant, data.disease, plantId, data.diseaseType)
            || getFirstDiseaseImage(plant);
        if (diseaseImg) {
            return {
                imageUrl: diseaseImg,
                stage,
                plantId,
                pot,
                layout: 'disease',
                disease: data.disease
            };
        }
    }

    return {
        imageUrl: getHealthyStageImage(plant, stage),
        stage,
        plantId,
        pot,
        layout: stage >= 2 ? 'bloom' : 'sprout',
        disease: null
    };
}

function getPlantDisplayImage(plant, data) {
    return getPlantVisualMeta(plant, data)?.imageUrl || null;
}

function getOffsetsForVisual(meta) {
    if (meta.layout === 'disease') {
        return getPlantOffsets(meta.plantId, meta.stage, meta.disease);
    }
    return getPlantOffsets(meta.plantId, meta.stage, null);
}

function getPotLiftForVisual(type, meta) {
    const hasDisease = meta.layout === 'disease' || meta.layout === 'dead';
    const disease = meta.layout === 'dead' ? '__dead__' : meta.disease;
    return getPotLift(type, meta.plantId, meta.pot, meta.stage, hasDisease, disease);
}

function updateZoomPlantVisual(data) {
    const plantImg = document.getElementById('zoomPlantImg');
    if (!plantImg || !data?.plant) return;

    const plant = PLANTS[data.plant];
    if (!plant) return;

    const meta = getPlantVisualMeta(plant, data);
    if (!meta) {
        plantImg.style.display = 'none';
        return;
    }

    plantImg.src = meta.imageUrl;
    plantImg.style.display = 'block';

    const offsets = getOffsetsForVisual(meta);
    const zoomLift = getPotLiftForVisual('zoom', meta);
    const zoomScale = 2.0;

    if (offsets) {
        const bottomPx = parseInt(offsets.bottom, 10) + zoomLift;
        const widthPx = Math.round(parseInt(offsets.width, 10) * zoomScale);
        plantImg.style.bottom = zoomCqh(bottomPx);
        plantImg.style.width = zoomCqw(widthPx);
    } else {
        plantImg.style.bottom = zoomCqh(35 + zoomLift);
        plantImg.style.width = zoomCqw(180);
    }
}

function refreshPlantVisual(slotName) {
    const data = slotData[slotName];
    if (!data) return;

    const slotEl = document.querySelector(`[data-slot="${slotName}"]`);
    if (slotEl) renderSlot(slotEl, data);

    if (zoomedSlot && zoomedSlot.name === slotName) {
        updateZoomPlantVisual(data);
        updateDiseaseInfo(data);
        showFixAdvice(data);

        const zoomStageLabel = document.getElementById('zoomStageLabel');
        if (zoomStageLabel && data.plant) {
            const stage = resolvePlantStage(data);
            if (stage === 0) {
                zoomStageLabel.textContent = STAGE_NAMES[0];
            } else if (stage === 1) {
                zoomStageLabel.textContent = data.hasDisease ? '🤒 Росток болеет' : STAGE_NAMES[1];
            } else if (stage >= 2) {
                zoomStageLabel.textContent = data.hasDisease ? '🤒 Цветёт, но болеет' : STAGE_NAMES[2];
            }
        }
    }
}

function tryHealUnderwaterOnWater(data) {
    if (!data?.hasDisease) return false;
    const plantKey = resolveSpeciesId(data.plant, PLANTS[data.plant]);
    const underMsg = PLANT_DISEASES[plantKey]?.under_watered;
    if (!underMsg || data.disease !== underMsg) return false;
    data.hasDisease = false;
    data.disease = null;
    data.diseaseType = null;
    data.diseaseSource = null;
    markHealedPlant();
    return true;
}

function checkWateringHealth(slotName, data) {
    if (!data || !data.plant) return;
    const plant = PLANTS[data.plant];
    if (!plant || data.stage < 1) return;

    const plantKey = resolveSpeciesId(data.plant, plant);
    const now = Date.now();
    const maxMs = getWaterMaxMs(plant);
    const sinceWaterMs = msSinceLastWater(data);

    if (hasOverwaterRisk(data, plant) && PLANT_DISEASES[plantKey]?.overwatered) {
        applyPlantDisease(slotName, data, 'overwatered', 'water');
    } else if (!data.hasDisease) {
        const needsWater = !data.lastWateredAt
            ? (now - (data.plantedAt || now)) > maxMs
            : sinceWaterMs > maxMs;
        if (needsWater && PLANT_DISEASES[plantKey]?.under_watered) {
            applyPlantDisease(slotName, data, 'under_watered', 'water');
        }
    }

    saveState();
}

function getLocationDiseaseForSlot(plantKey, slotName, data) {
    const slotLight = SLOT_LIGHT[slotName];
    const diseases = PLANT_DISEASES[plantKey];
    if (!diseases) return null;

    if (plantKey === 1 && data.pot === 3) return diseases.big_pot;

    if (!slotLight) return null;

    if (plantKey === 1) {
        if (slotLight === 'high') return diseases.too_light;
    } else if (plantKey === 2) {
        if (slotLight === 'low') return diseases.too_dark;
        if (slotLight !== 'high') return diseases.no_flower;
    } else if (plantKey === 3) {
        if (slotLight === 'high') return diseases.too_light;
    }

    return null;
}

function checkLocationDisease(slotName) {
    const data = slotData[slotName];
    if (!data || !data.plant || data.stage < 1) return;

    const plantKey = resolveSpeciesId(data.plant, PLANTS[data.plant]);
    let diseaseMsg = getLocationDiseaseForSlot(plantKey, slotName, data);

    if (diseaseMsg && !data.hasDisease) {
        data.hasDisease = true;
        data.hadMistakes = true;
        data.disease = diseaseMsg;
        data.diseaseType = getDiseaseTypeFromMessage(plantKey, diseaseMsg);
        data.diseaseSource = (plantKey === 1 && data.pot === 3 && diseaseMsg === PLANT_DISEASES[1].big_pot)
            ? 'pot' : 'location';
        saveState();
        showNotification(`🤒 ${PLANTS[data.plant]?.name}: ${diseaseMsg}`, true);
        checkAchievement_negativeEffect();
        refreshPlantVisual(slotName);
    } else if (!diseaseMsg && data.hasDisease && isLocationBasedDisease(plantKey, data.disease) && data.stage >= 1) {
        data.hasDisease = false;
        data.disease = null;
        data.diseaseType = null;
        data.diseaseSource = null;
        saveState();
        markHealedPlant();
        refreshPlantVisual(slotName);
        applyGrowthFromTime(slotName);
    }
}

function scheduleLocationCheck(slotName) {
    checkLocationDisease(slotName);
    setTimeout(() => {
        if (slotData[slotName]?.plant) {
            scheduleLocationCheck(slotName);
        }
    }, 30000);
}

function scheduleOverwateringCheck() {
    const tickMs = WATER_TIMING_TEST ? 10 * 1000 : 60 * 1000;
    setInterval(() => {
        Object.keys(slotData).forEach(slotName => {
            const data = slotData[slotName];
            if (data && data.plant && data.stage >= 1) {
                checkWateringHealth(slotName, data);
            }
        });
    }, tickMs);
}

function enqueuePopup(type, data) {
    popupQueue.push({ type, data });
    if (!popupShowing) processPopupQueue();
}

function processPopupQueue() {
    if (popupQueue.length === 0) { popupShowing = false; return; }
    popupShowing = true;
    const { type, data } = popupQueue.shift();
    if (type === 'level') showLevelRewardPopup(data);
    else if (type === 'achievement') showAchievementPopup(data);
}

function showLevelRewardPopup({ level, rewardText }) {
    updateLevelCircle(level);
    showRewardToast(level);
    checkAndUnlockPots();
    checkAndUnlockWateringCans();
    renderPotChoices();
    renderFlowerChoices();
    renderWateringCanChoices();
    checkAchievement_level(level);
    setTimeout(processPopupQueue, 3000);
}

function showAchievementPopup({ name, id }) {
    showAchievementUnlockToast(id);
    setTimeout(processPopupQueue, 3000);
}

function updateLevelCircle(lvl) {
    currentLevel = lvl;
    const levelNum = document.getElementById('levelNum');
    if (levelNum) levelNum.textContent = lvl;
}

const QUESTS_BY_LEVEL = {
    1: [
        { id: 'plant_first', desc: 'Посадить первое растение', check: () => Object.values(slotData).some(d => d && d.plant) },
        { id: 'water_once', desc: 'Полить растение 1 раз', check: () => getTotalWaterings() >= 1 },
        { id: 'read_tip', desc: 'Прочитать описание цветка', check: () => !!localStorage.getItem(`readDescriptionDone_${currentUser}`) }
    ],
    2: [
        { id: 'grow_stage2', desc: 'Вырастить цветок до 2-й стадии роста', check: () => Object.values(slotData).some(d => d && d.stage >= 1) },
        { id: 'login_3days', desc: 'Заходить в игру 3 дня подряд', check: () => getLoginStreak() >= 3 },
        { id: 'heal_plant', desc: 'Вылечить растение от болезни', check: () => localStorage.getItem(`healedPlant_${currentUser}`) === 'true' }
    ],
    3: [
        { id: 'grow_2species', desc: 'Вырастить 2 разных растения до зрелости', check: () => getMatureSpeciesCount() >= 2 },
        { id: 'water_3times', desc: 'Полить растения 3 раза', check: () => getTotalWaterings() >= 3 },
        { id: 'login_5days', desc: 'Заходить в игру 5 дней подряд', check: () => getLoginStreak() >= 5 }
    ],
    4: [
        { id: 'water_6times', desc: 'Полить растения 6 раз', check: () => getTotalWaterings() >= 6 },
        { id: 'login_7days', desc: 'Заходить в игру 7 дней подряд', check: () => getLoginStreak() >= 7 },
        { id: 'grow_3rd_plant', desc: 'Вырастить 3-е растение', check: () => getMatureSpeciesCount() >= 3 }
    ],
    5: [
        { id: 'no_mistakes_7days', desc: 'Не допускать критических ошибок 7 дней подряд', check: () => !!localStorage.getItem(`noMistakes7_${currentUser}`) },
        { id: 'login_10days', desc: 'Заходить в игру 10 дней подряд', check: () => getLoginStreak() >= 10 },
        { id: 'get_achievements', desc: 'Получить 3 разные ачивки', check: () => getUnlockedAchievementsCount() >= 3 }
    ]
};

function getTotalWaterings() {
    return parseInt(localStorage.getItem(`totalWaterings_${currentUser}`) || '0');
}
function getLoginStreak() {
    return parseInt(localStorage.getItem(`loginStreak_${currentUser}`) || '1');
}
function getMatureSpeciesCount() {
    const species = new Set();
    Object.values(slotData).forEach(d => { if (d && d.plant && d.stage >= 2) species.add(d.plant); });
    return species.size;
}

function getQuestsDoneIds() {
    try { return JSON.parse(localStorage.getItem(`questsDone_${currentUser}`) || '[]'); } catch { return []; }
}
function markQuestDone(id) {
    const done = getQuestsDoneIds();
    if (!done.includes(id)) { done.push(id); localStorage.setItem(`questsDone_${currentUser}`, JSON.stringify(done)); }
}

/** Блокирует автоповышение уровня из renderQuests (для DEV LEVEL UP) */
let suppressQuestAutoLevelUp = false;
let questLevelUpTimeoutId = null;

function cancelPendingQuestLevelUp() {
    if (questLevelUpTimeoutId !== null) {
        clearTimeout(questLevelUpTimeoutId);
        questLevelUpTimeoutId = null;
    }
}

function renderQuests() {
    const list = document.getElementById('questsList');
    if (!list) return;

    const quests = QUESTS_BY_LEVEL[currentLevel] || [];
    const done = getQuestsDoneIds();
    const allowAutoQuest = !suppressQuestAutoLevelUp;

    if (quests.length === 0) {
        list.innerHTML = '<div class="quest-item">Все задания выполнены! 🌟</div>';
        return;
    }

    list.innerHTML = quests.map(q => {
        const isDone = done.includes(q.id) || (allowAutoQuest && q.check());
        if (allowAutoQuest && isDone && !done.includes(q.id)) markQuestDone(q.id);
        return `<div class="quest-item ${isDone ? 'done' : ''}">
            <span class="quest-check">${isDone ? '✓' : '○'}</span>
            <span class="quest-desc">${q.desc}</span>
        </div>`;
    }).join('');

    const allDone = quests.every(q => done.includes(q.id) || (allowAutoQuest && q.check()));
    if (allDone && allowAutoQuest) {
        const levelUpKey = `levelUp_${currentLevel}_done_${currentUser}`;
        if (!localStorage.getItem(levelUpKey)) {
            localStorage.setItem(levelUpKey, '1');
            cancelPendingQuestLevelUp();
            questLevelUpTimeoutId = setTimeout(() => {
                questLevelUpTimeoutId = null;
                const newLevel = currentLevel + 1;
                const reward = LEVEL_REWARDS[newLevel] || 'Продолжай ухаживать за растениями!';
                enqueuePopup('level', { level: newLevel, rewardText: reward });
                localStorage.setItem(`currentLevel_${currentUser}`, String(newLevel));
                updateLevelCircle(newLevel);
                renderQuests();
            }, 1200);
        }
    }
}

function checkQuestsAfterAction() {
    renderQuests();
}

function markHealedPlant() {
    if (!localStorage.getItem(`healedPlant_${currentUser}`)) {
        localStorage.setItem(`healedPlant_${currentUser}`, 'true');
        checkQuestsAfterAction();
        showNotification('💚 Растение выздоровело! Задание выполнено!', false);
    }
}

function checkAndUnlockPots() {
    const userLevel = currentLevel;
    let unlockedAny = false;

    Object.entries(POT_CONFIG).forEach(([num, cfg]) => {
        const unlockLevel = cfg.unlockLevel || 1;
        if (unlockLevel <= userLevel && !cfg.isUnlocked) {
            POT_CONFIG[num].isUnlocked = true;
            unlockedAny = true;
            showNotification(`🎉 Новый горшок разблокирован: ${cfg.name}!`, false);
        }
    });

    if (unlockedAny) {
        renderPotChoices();
        if (modalRepot && modalRepot.classList.contains('active')) {
            renderRepotChoices();
        }
    }
}

function checkAndUnlockWateringCans() {
    const userLevel = currentLevel;
    let unlockedAny = false;

    Object.entries(WATERING_CAN_CONFIG).forEach(([id, cfg]) => {
        const unlockLevel = cfg.unlockLevel || 1;
        if (unlockLevel <= userLevel && !cfg.isUnlocked) {
            WATERING_CAN_CONFIG[id].isUnlocked = true;
            unlockedAny = true;
            showNotification(`🎉 Новая лейка разблокирована: ${cfg.name}!`, false);
        }
    });

    if (unlockedAny) {
        renderWateringCanChoices();
    }
}

function renderPotChoices() {
    const row = document.getElementById('potChoicesRow');
    if (!row) return;
    row.innerHTML = '';

    Object.entries(POT_CONFIG).forEach(([num, cfg]) => {
        const locked = !cfg.isUnlocked;
        const div = document.createElement('div');
        div.className = 'pot-choice' + (locked ? ' locked-choice' : '');
        div.dataset.pot = num;
        div.innerHTML = `<img src="${cfg.img}" alt="${cfg.name}"${locked ? ' style="filter:grayscale(1) opacity(0.5)"' : ''}>
            <span>${cfg.name}</span>
            ${locked ? `<span class="unlock-hint">🔒 ур.${cfg.unlockLevel}</span>` : ''}`;
        if (!locked) {
            div.addEventListener('click', () => {
                if (activeSlot) {
                    placePot(activeSlot, parseInt(num));
                    closeModal(modalPlacePot);
                }
            });
        } else {
            div.title = `Открывается на ${cfg.unlockLevel}-м уровне`;
        }
        row.appendChild(div);
    });
}

function renderFlowerChoices() {
    const row = document.getElementById('flowerChoicesRow');
    if (!row) return;
    row.innerHTML = '';

    if (Object.keys(PLANTS).length === 0) {
        row.innerHTML = '<div class="flower-choice">Загрузка растений...</div>';
        return;
    }

    Object.entries(PLANTS).forEach(([key, plant]) => {
        const locked = plant.unlockLevel > currentLevel;
        const previewImage = plant.stages && plant.stages[1] ? plant.stages[1] : 'images/plant/default/stage/росток.png';

        const div = document.createElement('div');
        div.className = 'flower-choice' + (locked ? ' locked-choice' : '');
        div.dataset.plant = key;
        div.innerHTML = `<img src="${previewImage}" alt="${plant.name}"${locked ? ' style="filter:grayscale(1) opacity(0.5)"' : ''}>
            <span>${plant.name}</span>
            ${locked ? `<span class="unlock-hint">🔒 ур.${plant.unlockLevel}</span>` : ''}`;

        if (!locked) {
            div.addEventListener('click', () => {
                const plantKey = div.dataset.plant;
                if (!activeSlot) {
                    showNotification('Ошибка: горшок не выбран', true);
                    return;
                }
                const name = activeSlot.dataset.slot;
                if (!slotData[name]) {
                    showNotification('Ошибка: данные горшка не найдены', true);
                    return;
                }
                slotData[name].plant = plantKey;
                slotData[name].stage = 0;
                slotData[name].plantedAt = Date.now();
                slotData[name].lastWateredAt = null;
                slotData[name].totalWaterings = 0;
                slotData[name].hasDisease = false;
                slotData[name].hadMistakes = false;
                slotData[name].disease = null;
                slotData[name].wateringHistory = [];
                renderSlot(activeSlot, slotData[name]);
                closeModal(modalPickFlower);
                activeSlot = null;
                showNotification(`${plant.name} посажен! 🌱 Первый росток появится через 10 секунд...`, false);
                saveState();
                checkQuestsAfterAction();
                scheduleGrowth(name);
                scheduleLocationCheck(name);
            });
        } else {
            div.title = `Открывается на ${plant.unlockLevel}-м уровне`;
        }
        row.appendChild(div);
    });
}

function renderWateringCanChoices() {
    const row = document.getElementById('waterCanChoicesRow');
    if (!row) return;
    row.innerHTML = '';

    const currentCanId = parseInt(localStorage.getItem(`currentWateringCan_${currentUser}`) || '1');

    Object.entries(WATERING_CAN_CONFIG).forEach(([id, cfg]) => {
        const locked = !cfg.isUnlocked;
        const isCurrent = parseInt(id) === currentCanId;
        const div = document.createElement('div');
        div.className = 'watercan-choice' + (locked ? ' locked-choice' : '') + (isCurrent ? ' current-can' : '');
        div.dataset.can = id;
        div.innerHTML = `<img src="${cfg.img}" alt="${cfg.name}"${locked ? ' style="filter:grayscale(1) opacity(0.5)"' : ''}>
            <span>${cfg.name}</span>
            ${locked ? `<span class="unlock-hint">🔒 ур.${cfg.unlockLevel}</span>` : ''}`;

        if (!locked && !isCurrent) {
            div.addEventListener('click', () => {
                changeWateringCan(parseInt(id), cfg);
            });
        } else if (locked) {
            div.title = `Открывается на ${cfg.unlockLevel}-м уровне`;
        }
        row.appendChild(div);
    });
}

async function changeWateringCan(canId, canConfig) {
    try {
        const response = await fetch(`${API_BASE_URL}/user/settings/design`, {
            method: 'POST',
            headers: getAuthHeaders(),
            credentials: 'include',
            body: JSON.stringify({
                type: 'watering_can',
                design_id: String(canId)
            })
        });

        const data = await response.json();

        if (data.success) {
            localStorage.setItem(`currentWateringCan_${currentUser}`, String(canId));
            showNotification(`Лейка сменена на ${canConfig.name}! 💧`, false);
            updateWateringCanDisplay(canId);
            if (modalWaterCan) closeModal(modalWaterCan);
            renderWateringCanChoices();
        } else {
            showNotification(data.error || 'Ошибка смены лейки', true);
        }
    } catch (error) {
        console.error('Ошибка смены лейки:', error);
        showNotification('Ошибка соединения с сервером', true);
    }
}

function updateWateringCanDisplay(canId) {
    const wateringCanIcon = document.getElementById('wateringCanIcon');
    if (wateringCanIcon && WATERING_CAN_CONFIG[canId]) {
        wateringCanIcon.src = WATERING_CAN_CONFIG[canId].img;
        wateringCanIcon.alt = WATERING_CAN_CONFIG[canId].name;
    }
    const wateringCanImg = document.getElementById('wateringCanImg');
    if (wateringCanImg && WATERING_CAN_CONFIG[canId]) {
        wateringCanImg.src = WATERING_CAN_CONFIG[canId].img;
    }
}

let moveFromSlot = null;

function renderMoveChoices() {
    const row = document.getElementById('moveChoicesRow');
    if (!row) return;
    row.innerHTML = '';

    const currentSlotData = slotData[moveFromSlot];
    if (!currentSlotData || !currentSlotData.pot) {
        showNotification('Ошибка: данные горшка не найдены', true);
        closeModal(modalMovePlant);
        moveFromSlot = null;
        return;
    }

    const allSlots = document.querySelectorAll('.pot-slot');

    allSlots.forEach(slotEl => {
        const slotName = slotEl.dataset.slot;
        const targetData = slotData[slotName];
        const isCurrent = slotName === moveFromSlot;

        if (isCurrent) return;

        const isEmpty = !targetData || !targetData.pot;

        const div = document.createElement('div');
        div.className = 'pot-choice';

        if (isEmpty) {
            div.classList.add('empty-slot');
        } else {
            div.classList.add('occupied-slot');
        }

        div.dataset.slot = slotName;

        let slotDisplayName = slotName.replace(/-/g, ' ');
        let potImg = '/images/room/пунктир.png';
        let statusHtml = '';

        if (isEmpty) {
            statusHtml = '<span class="free-label">🆓 Свободно</span>';
        } else {
            if (targetData.pot && POT_CONFIG[targetData.pot]) {
                potImg = POT_CONFIG[targetData.pot].img;
            }
            const plantName = targetData.plant && PLANTS[targetData.plant]
                ? PLANTS[targetData.plant].name
                : 'Пустой горшок';
            statusHtml = `<span class="occupied-label">🌿 ${plantName}</span>`;
        }

        div.innerHTML = `
            <img src="${potImg}" alt="место" style="${isEmpty ? 'width:60px; height:60px; opacity:0.6' : ''}">
            <span>${slotDisplayName}</span>
            ${statusHtml}
        `;

        div.addEventListener('click', (e) => {
            e.stopPropagation();
            if (!moveFromSlot) return;

            if (isEmpty) {
                movePlantToEmptySlot(moveFromSlot, slotName);
            } else {
                swapPlants(moveFromSlot, slotName);
            }
            closeModal(modalMovePlant);
            moveFromSlot = null;
        });

        row.appendChild(div);
    });
}

function movePlantToEmptySlot(fromSlot, toSlot) {
    if (!slotData[fromSlot]) {
        showNotification('❌ Ошибка: источник не найден', true);
        return;
    }

    if (slotData[toSlot] && slotData[toSlot].pot) {
        showNotification('❌ Это место уже занято!', true);
        return;
    }

    const movedData = {
        pot: slotData[fromSlot].pot,
        plant: slotData[fromSlot].plant,
        stage: slotData[fromSlot].stage,
        plantedAt: slotData[fromSlot].plantedAt,
        lastWateredAt: slotData[fromSlot].lastWateredAt,
        totalWaterings: slotData[fromSlot].totalWaterings,
        hasDisease: slotData[fromSlot].hasDisease,
        hadMistakes: slotData[fromSlot].hadMistakes,
        disease: slotData[fromSlot].disease,
        diseaseSource: slotData[fromSlot].diseaseSource,
        bloomedAt: slotData[fromSlot].bloomedAt,
        sproutedAt: slotData[fromSlot].sproutedAt,
        wateringHistory: slotData[fromSlot].wateringHistory || []
    };

    slotData[toSlot] = movedData;
    delete slotData[fromSlot];

    const fromSlotEl = document.querySelector(`[data-slot="${fromSlot}"]`);
    const toSlotEl = document.querySelector(`[data-slot="${toSlot}"]`);

    if (fromSlotEl) renderSlot(fromSlotEl, null);
    if (toSlotEl) renderSlot(toSlotEl, slotData[toSlot]);

    saveState();
    showNotification(`🪴 Растение перемещено на новое место!`, false);

    if (slotData[toSlot] && slotData[toSlot].plant) {
        setTimeout(() => {
            checkLocationDisease(toSlot);
            refreshPlantVisual(toSlot);
        }, 100);
    }

    if (zoomedSlot && zoomedSlot.name === fromSlot) {
        closeModal(zoomOverlay);
        zoomedSlot = null;
    } else if (zoomedSlot && zoomedSlot.name === toSlot) {
        openZoom(toSlotEl, toSlot, slotData[toSlot]);
    }
}

function swapPlants(slotA, slotB) {
    if (!slotData[slotA] || !slotData[slotB]) return;

    const dataA = { ...slotData[slotA] };
    const dataB = { ...slotData[slotB] };

    slotData[slotA] = dataB;
    slotData[slotB] = dataA;

    const slotElA = document.querySelector(`[data-slot="${slotA}"]`);
    const slotElB = document.querySelector(`[data-slot="${slotB}"]`);

    if (slotElA) renderSlot(slotElA, slotData[slotA]);
    if (slotElB) renderSlot(slotElB, slotData[slotB]);

    saveState();
    showNotification(`🔄 Горшки переставлены местами!`, false);

    if (slotData[slotA] && slotData[slotA].plant) {
        checkLocationDisease(slotA);
        refreshPlantVisual(slotA);
    }
    if (slotData[slotB] && slotData[slotB].plant) {
        checkLocationDisease(slotB);
        refreshPlantVisual(slotB);
    }

    if (zoomedSlot) {
        if (zoomedSlot.name === slotA) {
            openZoom(slotElA, slotA, slotData[slotA]);
        } else if (zoomedSlot.name === slotB) {
            openZoom(slotElB, slotB, slotData[slotB]);
        }
    }
}

slots.forEach(slot => {
    slot.addEventListener('click', () => {
        const name = slot.dataset.slot;
        const data = slotData[name];
        if (!data || !data.pot) {
            activeSlot = slot;
            renderPotChoices();
            openModal(modalPlacePot);
        } else {
            openZoom(slot, name, data);
        }
    });
});

const cancelPlacePot = document.getElementById('cancelPlacePot');
if (cancelPlacePot) cancelPlacePot.addEventListener('click', () => closeModal(modalPlacePot));
const cancelPickFlower = document.getElementById('cancelPickFlower');
if (cancelPickFlower) {
    cancelPickFlower.addEventListener('click', () => {
        closeModal(modalPickFlower);
        activeSlot = null;
        showNotification('Выбери цветок позже 🌱', false);
    });
}
if (modalPlacePot) modalPlacePot.addEventListener('click', e => { if (e.target === modalPlacePot) closeModal(modalPlacePot); });

function placePot(slotEl, potNum) {
    const name = slotEl.dataset.slot;
    slotData[name] = { pot: potNum, plant: null, stage: -1, lastWateredAt: null, totalWaterings: 0, wateringsToNextStage: 3 };
    renderSlot(slotEl, slotData[name]);
    showNotification('Горшок поставлен! Теперь посади цветок 🌱', false);
    saveState();
}

function removePlantFromSlot(slotName) {
    if (!slotData[slotName]) return;

    const data = slotData[slotName];

    if (data.plant && data.stage < 2) {
        checkAchievement_death();
    }

    data.plant = null;
    data.stage = -1;
    data.plantedAt = null;
    data.lastWateredAt = null;
    data.totalWaterings = 0;
    data.hasDisease = false;
    data.hadMistakes = false;
    data.disease = null;
    data.wateringHistory = [];

    const slotEl = document.querySelector(`[data-slot="${slotName}"]`);
    if (slotEl) renderSlot(slotEl, data);

    if (zoomedSlot && zoomedSlot.name === slotName) {
        openZoom(slotEl, slotName, data);
    }

    showNotification(`🌿 Горшок освобождён!`, false);
    saveState();
    checkQuestsAfterAction();
}

function removePotFromSlot(slotName) {
    if (!slotData[slotName]) return;

    const data = slotData[slotName];
    if (data.plant && data.stage < 2) {
        checkAchievement_death();
    }

    slotData[slotName] = { pot: null, plant: null, stage: -1, lastWateredAt: null, totalWaterings: 0, wateringsToNextStage: 3 };

    const slotEl = document.querySelector(`[data-slot="${slotName}"]`);
    if (slotEl) renderSlot(slotEl, slotData[slotName]);

    closeModal(zoomOverlay);
    zoomedSlot = null;

    showNotification(`🪣 Горшок убран!`, false);
    saveState();
    checkQuestsAfterAction();
}

function renderSlot(slotEl, data) {
    if (!slotEl) return;

    const existingPot = slotEl.querySelector('.slot-placed-pot');
    if (existingPot) existingPot.remove();
    const existingPlant = slotEl.querySelector('.slot-plant-img');
    if (existingPlant) existingPlant.remove();
    const existingDiseaseEffect = slotEl.querySelector('.slot-disease-effect');
    if (existingDiseaseEffect) existingDiseaseEffect.remove();

    if (!data || !data.pot) {
        slotEl.classList.remove('filled');
        slotEl.style.cursor = 'pointer';

        const slotImg = slotEl.querySelector('.slot-img');
        if (slotImg) slotImg.style.display = 'block';

        const hint = slotEl.querySelector('.slot-hint');
        if (hint) hint.textContent = 'Поставить горшок';
        return;
    }

    slotEl.classList.add('filled');
    slotEl.style.cursor = 'pointer';

    const slotImg = slotEl.querySelector('.slot-img');
    if (slotImg) slotImg.style.display = 'none';

    const potImg = document.createElement('img');
    const potConfig = POT_CONFIG[data.pot];
    if (potConfig) {
        potImg.src = potConfig.img;
        potImg.className = 'slot-placed-pot';
        potImg.alt = `Горшок ${data.pot}`;
        slotEl.prepend(potImg);
    }

    if (data.plant && data.stage >= 1 && PLANTS[data.plant]) {
        const plantImg = document.createElement('img');
        const plant = PLANTS[data.plant];
        const plantId = parseInt(data.plant);

        const meta = getPlantVisualMeta(plant, data);

        if (meta?.imageUrl) {
            plantImg.src = meta.imageUrl;
            plantImg.className = 'slot-plant-img';
            plantImg.alt = plant.name;

            const offsets = getOffsetsForVisual(meta);
            if (offsets) {
                const baseLiftPx = 50;
                const extraLiftPx = getPotLiftForVisual('slot', meta);

                plantImg.style.bottom = `calc(${offsets.bottom} + ${baseLiftPx + extraLiftPx}px)`;
                plantImg.style.width = offsets.width;
                plantImg.style.left = offsets.left;
                plantImg.style.transform = 'translateX(-50%) scale(1.50)';
                plantImg.style.transformOrigin = 'bottom center';
            }

            slotEl.appendChild(plantImg);

            if ((meta.layout === 'disease' || meta.layout === 'dead') && meta.stage >= 1) {
                const diseaseEffect = document.createElement('div');
                diseaseEffect.className = 'slot-disease-effect';
                diseaseEffect.textContent = meta.layout === 'dead' ? '💀' : '🤒';
                slotEl.appendChild(diseaseEffect);
            }
        }
    }

    const hint = slotEl.querySelector('.slot-hint');
    if (hint) {
        if (!data.plant) {
            hint.innerHTML = 'Посадить<br>цветок';
        } else if (data.stage === 0) {
            hint.textContent = 'Прорастает...';
        } else if (data.stage === 1) {
            if (data.hasDisease) {
                hint.textContent = 'Болеет...';
            } else {
                hint.textContent = 'Росток';
            }
        } else if (data.stage === 2) {
            if (data.hasDisease) {
                hint.innerHTML = 'Цветёт,<br>но болеет';
            } else {
                hint.textContent = 'Цветёт!';
            }
        }
    }
}

function updateGrowthTimer(data) {
    if (!data || !data.plant || data.stage >= 2) {
        const timerBox = document.getElementById('growthTimerBox');
        if (timerBox) timerBox.style.display = 'none';
        return;
    }

    const now = Date.now();
    const msSincePlanted = now - data.plantedAt;

    if (data.stage === 0) {
        const msLeft = Math.max(0, SEEDLING_MS - msSincePlanted);
        const secondsLeft = Math.ceil(msLeft / 1000);
        const timerBox = document.getElementById('growthTimerBox');
        if (timerBox) {
            timerBox.innerHTML = `🌱 Росток через ${secondsLeft} сек.`;
            timerBox.style.display = 'block';
        }
    } else if (data.stage === 1) {
        const msLeft = Math.max(0, BLOOM_MS - msSincePlanted);
        const secondsLeft = Math.ceil(msLeft / 1000);
        const timerBox = document.getElementById('growthTimerBox');
        if (timerBox) {
            timerBox.innerHTML = `🌸 Цветение через ${secondsLeft} сек.`;
            timerBox.style.display = 'block';
        }
    }
}

function updateNextWateringTimer(data) {
    if (!data || !data.plant) {
        const timerBox = document.getElementById('waterTimerBox');
        if (timerBox) timerBox.style.display = 'none';
        return;
    }

    const plant = PLANTS[data.plant];
    if (!plant) return;

    const now = Date.now();
    let timerText = '';

    const minMs = getWaterMinMs(plant);
    const maxMs = getWaterMaxMs(plant);
    const sinceMs = msSinceLastWater(data);

    if (data.lastWateredAt) {
        if (sinceMs < minMs) {
            const left = Math.ceil((minMs - sinceMs) / 1000);
            timerText = WATER_TIMING_TEST ? `💧 Полив через ${left} сек.` : `💧 Полив через ${Math.ceil((minMs - sinceMs) / 3600000)} ч`;
        } else if (sinceMs <= maxMs) {
            timerText = `⏰ Пора поливать!`;
        } else {
            timerText = `⚠️ Срочно полей!`;
        }
    } else {
        timerText = `🌱 Нужен первый полив`;
    }

    const timerBox = document.getElementById('waterTimerBox');
    if (timerBox) {
        timerBox.innerHTML = timerText;
        timerBox.style.display = 'block';
    }
}

function updateDiseaseInfo(data) {
    const diseaseBox = document.getElementById('diseaseBox');
    const diseaseText = document.getElementById('diseaseText');

    if (!diseaseBox || !diseaseText) return;

    if (data.hasDisease && data.disease && data.stage >= 1) {
        diseaseText.innerHTML = data.disease;
        diseaseBox.style.display = 'block';
    } else {
        diseaseBox.style.display = 'none';
    }
}

function showFixAdvice(data) {
    const fixBox = document.getElementById('fixAdviceBox');
    const fixText = document.getElementById('fixAdviceText');
    if (!fixBox || !fixText) return;

    if (data.hasDisease && data.disease && data.stage >= 1) {
        let advice = '';
        const norm = normalizePlantText(data.disease);
        if (norm.includes('ожог') || norm.includes('пятна') || norm.includes('свет')) {
            advice = '💡 Решение: Убери с подоконника — слишком яркий свет. Переставь горшок через «Переставить горшок».';
        } else if (norm.includes('недостаток полива') || norm.includes('сохнут кончики')) {
            advice = '💧 Решение: Полей растение. Следи, чтобы полив был регулярным.';
        } else if (norm.includes('перелив') || norm.includes('увядание')) {
            advice = '💧 Решение: Дай почве просохнуть, поливай реже.';
        } else if (norm.includes('вытягивание') || norm.includes('нехватка света') || norm.includes('не цветет')) {
            advice = '💡 Решение: Переставь на более светлое место (подоконник).';
        } else if (data.disease.includes('горшок')) {
            advice = '🪴 Решение: Пересади растение в горшок поменьше.';
        } else {
            advice = '🌿 Решение: Измени условия ухода: проверь полив и освещение.';
        }
        fixText.innerHTML = advice;
        fixBox.style.display = 'block';
    } else {
        fixBox.style.display = 'none';
    }
}

function showDescription(plantKey) {
    const plant = PLANTS[plantKey];
    const descEl = document.getElementById('plantDescription');
    const descriptionBox = document.getElementById('descriptionBox');

    if (!descEl || !plant) return;

    descEl.innerHTML = `
        <div class="desc-text">
            <h4>${plant.name} «${plant.nickname}»</h4>
            <p>${plant.description}</p>
            <h4>💧 Полив</h4>
            <p>${plant.waterAdvice}</p>
            <h4>☀️ Свет</h4>
            <p>${plant.lightAdvice}</p>
            <h4>💡 Советы</h4>
            <p>${plant.tips}</p>
        </div>
    `;

    if (descriptionBox) descriptionBox.style.display = 'block';

    if (!localStorage.getItem(`readDescriptionDone_${currentUser}`)) {
        localStorage.setItem(`readDescriptionDone_${currentUser}`, '1');
        checkQuestsAfterAction();
        showNotification('📖 Задание выполнено: описание прочитано!', false);
    }
}

function populateDevPanel(plant) {
    const sel = document.getElementById('devStateSelect');
    if (!sel) return;

    const currentVal = sel.value;

    // Убираем старые disease-опции (все кроме sprout, healthy, dead)
    Array.from(sel.options).filter(o => !['sprout', 'healthy', 'dead'].includes(o.value))
        .forEach(o => sel.removeChild(o));

    const deadOption = Array.from(sel.options).find(o => o.value === 'dead');
    const emojiMap = {
        'желтение': '🍃', 'не цветет': '🌿', 'сохнут кончики': '🍃',
        'вытягивание': '🌵', 'сморщенный стебель': '🌵',
        'пятна': '🍂', 'увядание': '🍂'
    };

    if (plant?.diseaseImages) {
        for (const key of Object.keys(plant.diseaseImages)) {
            const opt = document.createElement('option');
            opt.value = key;
            opt.textContent = (emojiMap[key] || '🤒') + ' Болезнь: ' + key;
            sel.insertBefore(opt, deadOption);
        }
    }

    if (Array.from(sel.options).some(o => o.value === currentVal)) sel.value = currentVal;
    else sel.value = 'healthy';
}

function openZoom(slotEl, name, data) {
    zoomedSlot = { slotEl, name };
    currentZoomedPlantId = name;
    if (devStatePanel) devStatePanel.style.display = 'block';

    const zoomPotImg = document.getElementById('zoomPotImg');
    if (zoomPotImg && POT_CONFIG[data.pot]) {
        zoomPotImg.src = POT_CONFIG[data.pot].img;
        zoomPotImg.style.width = data.pot === 3 ? zoomCqw(185) : zoomCqw(200);
    }

    const plantImg = document.getElementById('zoomPlantImg');
    const waterBtn = document.getElementById('waterBtnLeft');
    const descBtn = document.getElementById('descBtnRight');
    const repotBtn = document.getElementById('repotBtnLeft');
    const moveBtn = document.getElementById('moveBtnLeft');
    const removeBtn = document.getElementById('removeBtnLeft');
    const plantBtn = document.getElementById('plantBtnLeft');
    const descriptionBox = document.getElementById('descriptionBox');

    const hasPlant = data.plant && data.stage >= 0 && PLANTS[data.plant];

    if (hasPlant) {
        const plant = PLANTS[data.plant];
        const plantId = parseInt(data.plant);
        populateDevPanel(plant);

        if (plantImg) {
            updateZoomPlantVisual(data);
        }

        const zoomPlantName = document.getElementById('zoomPlantName');
        if (zoomPlantName) zoomPlantName.textContent = `${plant.name} — ${plant.nickname}`;

        const zoomStageLabel = document.getElementById('zoomStageLabel');
        if (zoomStageLabel) {
            if (data.stage === 0) {
                zoomStageLabel.textContent = 'Семечко посажено';
            } else if (data.stage === 1) {
                if (data.hasDisease) {
                    zoomStageLabel.textContent = 'Росток болеет';
                } else {
                    zoomStageLabel.textContent = 'Росток';
                }
            } else if (data.stage === 2) {
                if (data.hasDisease) {
                    zoomStageLabel.textContent = 'Цветёт, но болеет';
                } else {
                    zoomStageLabel.textContent = 'Расцвёл';
                }
            } else {
                zoomStageLabel.textContent = STAGE_NAMES[data.stage] || STAGE_NAMES[0];
            }
        }

        if (waterBtn) {
            waterBtn.disabled = false;
            waterBtn.style.display = 'block'; }
        if (descBtn) descBtn.style.display = 'block';
        if (repotBtn) repotBtn.style.display = 'block';
        if (moveBtn) moveBtn.style.display = 'block';
        if (removeBtn) removeBtn.style.display = 'block';
        if (plantBtn) plantBtn.style.display = 'none';
        if (descriptionBox) descriptionBox.style.display = 'none';

        updateWateringInfo(data);
        updateGrowthTimer(data);
        updateNextWateringTimer(data);
        updateDiseaseInfo(data);
        showFixAdvice(data);

    } else {
        if (plantImg) plantImg.style.display = 'none';

        const zoomPlantName = document.getElementById('zoomPlantName');
        if (zoomPlantName) zoomPlantName.textContent = 'Пустой горшок';

        const zoomStageLabel = document.getElementById('zoomStageLabel');
        if (zoomStageLabel) zoomStageLabel.textContent = 'Посади цветок!';

        if (waterBtn) {
            waterBtn.disabled = true;
            waterBtn.style.display = 'none'; }
        if (descBtn) descBtn.style.display = 'none';
        if (repotBtn) repotBtn.style.display = 'none';
        if (moveBtn) moveBtn.style.display = 'none';
        if (removeBtn) removeBtn.style.display = 'block';
        if (plantBtn) plantBtn.style.display = 'block';
        if (descriptionBox) descriptionBox.style.display = 'none';

        const wateringInfo = document.getElementById('wateringInfo');
        if (wateringInfo) wateringInfo.innerHTML = '';

        const growthTimerBox = document.getElementById('growthTimerBox');
        if (growthTimerBox) growthTimerBox.style.display = 'none';

        const waterTimerBox = document.getElementById('waterTimerBox');
        if (waterTimerBox) waterTimerBox.style.display = 'none';

        const diseaseBox = document.getElementById('diseaseBox');
        if (diseaseBox) diseaseBox.style.display = 'none';

        const fixBox = document.getElementById('fixAdviceBox');
        if (fixBox) fixBox.style.display = 'none';
    }

    const wateringAnim = document.getElementById('wateringAnim');
    if (wateringAnim) wateringAnim.classList.remove('active');

    openModal(zoomOverlay);
}

function updateWateringInfo(data) {
    const infoEl = document.getElementById('wateringInfo');
    if (!infoEl) return;
    if (!data.plant || data.stage >= 2 || !PLANTS[data.plant]) { infoEl.innerHTML = ''; return; }

    const plant = PLANTS[data.plant];
    const minDays = plant.waterIntervalMin / 24;
    const maxDays = plant.waterIntervalMax / 24;
    const now = Date.now();
    let statusHTML = '';

    if (data.lastWateredAt) {
        const hoursAgo = (now - data.lastWateredAt) / 3600000;
        if (hoursAgo < plant.waterIntervalMin) {
            const hoursLeft = plant.waterIntervalMin - hoursAgo;
            statusHTML = `<span class="water-ok">💧 Следующий полив через ~${Math.ceil(hoursLeft)}ч</span>`;
        } else if (hoursAgo <= plant.waterIntervalMax) {
            statusHTML = `<span class="water-ready">⏰ Пора поливать!</span>`;
        } else {
            statusHTML = `<span class="water-danger">⚠️ Засыхает! Полей немедленно!</span>`;
        }
    } else {
        statusHTML = `<span class="water-ready">🌱 Нужен первый полив!</span>`;
    }
    infoEl.innerHTML = `<div class="watering-schedule">
        <div class="schedule-title">График полива: каждые ${minDays}–${maxDays} дней</div>
        <div class="schedule-status">${statusHTML}</div>
        <div class="schedule-advice">${plant.waterAdvice}</div>
    </div>`;
}

const zoomClose = document.getElementById('zoomClose');
if (zoomClose) zoomClose.addEventListener('click', () => { closeModal(zoomOverlay); if (devStatePanel) devStatePanel.style.display = 'none'; });
if (zoomOverlay) zoomOverlay.addEventListener('click', e => { if (e.target === zoomOverlay) { closeModal(zoomOverlay); if (devStatePanel) devStatePanel.style.display = 'none'; } });

// ПЕРЕСАДКА (смена дизайна горшка)
const cancelRepot = document.getElementById('cancelRepot');
if (cancelRepot) cancelRepot.addEventListener('click', () => closeModal(modalRepot));
if (modalRepot) modalRepot.addEventListener('click', e => { if (e.target === modalRepot) closeModal(modalRepot); });

function renderRepotChoices() {
    const row = document.getElementById('repotChoicesRow');
    if (!row) return;
    row.innerHTML = '';

    const currentSlotData = zoomedSlot ? slotData[zoomedSlot.name] : null;
    const currentPot = currentSlotData ? currentSlotData.pot : null;

    Object.entries(POT_CONFIG).forEach(([num, cfg]) => {
        const locked = !cfg.isUnlocked;
        const isCurrent = parseInt(num) === currentPot;
        const div = document.createElement('div');
        div.className = 'pot-choice' + (locked ? ' locked-choice' : '') + (isCurrent ? ' current-pot' : '');
        div.dataset.pot = num;
        div.innerHTML = `<img src="${cfg.img}" alt="${cfg.name}"${locked ? ' style="filter:grayscale(1) opacity(0.5)"' : ''}>
            <span>${cfg.name}</span>
            ${locked ? `<span class="unlock-hint">🔒 ур.${cfg.unlockLevel}</span>` : ''}`;
        if (!locked && !isCurrent) {
            div.addEventListener('click', () => {
                if (!zoomedSlot) return;
                const name = zoomedSlot.name;
                const data = slotData[name];
                if (!data) return;
                data.pot = parseInt(num);
                const slotEl = document.querySelector(`[data-slot="${name}"]`);
                if (slotEl) renderSlot(slotEl, data);
                closeModal(modalRepot);
                showNotification(`🪴 Растение пересажено в ${cfg.name}!`, false);
                saveState();
                const zoomPotImg = document.getElementById('zoomPotImg');
                if (zoomPotImg && POT_CONFIG[data.pot]) zoomPotImg.src = POT_CONFIG[data.pot].img;
            });
        }
        row.appendChild(div);
    });
}

const descBtnRight = document.getElementById('descBtnRight');
if (descBtnRight) {
    descBtnRight.addEventListener('click', () => {
        if (!zoomedSlot) return;
        const data = slotData[zoomedSlot.name];
        if (data && data.plant && PLANTS[data.plant]) {
            showDescription(data.plant);
        }
    });
}

const plantBtnLeft = document.getElementById('plantBtnLeft');
if (plantBtnLeft) {
    plantBtnLeft.addEventListener('click', () => {
        if (!zoomedSlot) return;
        activeSlot = zoomedSlot.slotEl;
        closeModal(zoomOverlay);
        renderFlowerChoices();
        setTimeout(() => openModal(modalPickFlower), 50);
    });
}

const removeBtnLeft = document.getElementById('removeBtnLeft');
if (removeBtnLeft) {
    removeBtnLeft.addEventListener('click', () => {
        if (!zoomedSlot) return;
        if (confirm('Вы уверены, что хотите выбросить растение вместе с горшком?')) {
            removePotFromSlot(zoomedSlot.name);
            closeModal(zoomOverlay);
        }
    });
}

const removePotBtn = document.getElementById('removePotBtn');
if (removePotBtn) {
    removePotBtn.addEventListener('click', () => {
        if (!zoomedSlot) return;
        if (confirm('Убрать горшок вместе с растением?')) {
            removePotFromSlot(zoomedSlot.name);
        }
    });
}

const repotBtnLeft = document.getElementById('repotBtnLeft');
if (repotBtnLeft) {
    repotBtnLeft.addEventListener('click', () => {
        if (!zoomedSlot) return;
        closeModal(zoomOverlay);
        renderRepotChoices();
        setTimeout(() => openModal(modalRepot), 100);
    });
}

const moveBtnLeft = document.getElementById('moveBtnLeft');
if (moveBtnLeft) {
    moveBtnLeft.addEventListener('click', () => {
        if (!zoomedSlot) return;

        moveFromSlot = zoomedSlot.name;
        closeModal(zoomOverlay);
        renderMoveChoices();
        setTimeout(() => {
            openModal(modalMovePlant);
        }, 100);
    });
}

const waterBtnLeft = document.getElementById('waterBtnLeft');
if (waterBtnLeft) {
    waterBtnLeft.addEventListener('click', () => {
        if (!zoomedSlot) return;
        const { slotEl, name } = zoomedSlot;
        const data = slotData[name];
        if (!data?.plant || !PLANTS[data.plant]) return;

        const plant = PLANTS[data.plant];
        const now = Date.now();

        if (data.lastWateredAt) {
            const sinceMs = now - data.lastWateredAt;
            const minMs = getWaterMinMs(plant);
            if (sinceMs < minMs) {
                const waitSec = Math.ceil((minMs - sinceMs) / 1000);
                const unit = WATER_TIMING_TEST ? `${waitSec} сек.` : `${Math.ceil((minMs - sinceMs) / 3600000)} ч.`;
                showNotification(`⚠️ Слишком рано! Лучше поливать через ${unit} Растение может заболеть.`, true);
            }
        }

        startWateringAnimation();

        setTimeout(() => {
            recordWateringGap(data, now);
            data.lastWateredAt = now;
            data.totalWaterings = (data.totalWaterings || 0) + 1;

            const globalTotal = getTotalWaterings() + 1;
            localStorage.setItem(`totalWaterings_${currentUser}`, String(globalTotal));

            tryHealUnderwaterOnWater(data);
            checkWateringHealth(name, data);
            applyGrowthFromTime(name);

            showNotification('Полито! 💧 Растение радуется', false);

            renderSlot(slotEl, data);
            updateWateringInfo(data);
            updateNextWateringTimer(data);

            updateZoomPlantVisual(data);

            const zoomStageLabel = document.getElementById('zoomStageLabel');
            if (zoomStageLabel) {
                const stage = resolvePlantStage(data);
                if (stage === 0) {
                    zoomStageLabel.textContent = STAGE_NAMES[0];
                } else if (stage === 1) {
                    zoomStageLabel.textContent = data.hasDisease ? '🤒 Росток болеет' : STAGE_NAMES[1];
                } else if (stage >= 2) {
                    zoomStageLabel.textContent = data.hasDisease ? '🤒 Цветёт, но болеет' : STAGE_NAMES[2];
                }
            }

            stopWateringAnimation();
            saveState();
            checkQuestsAfterAction();
        }, 2000);
    });
}

function startWateringAnimation() {
    const anim = document.getElementById('wateringAnim');
    const dropsContainer = document.getElementById('waterDrops');
    if (dropsContainer) dropsContainer.innerHTML = '';
    for (let i = 0; i < 8; i++) {
        const drop = document.createElement('div');
        drop.className = 'drop';
        drop.style.left = (10 + Math.random() * 50) + 'px';
        drop.style.animationDelay = (Math.random() * 0.5) + 's';
        drop.style.animationDuration = (0.5 + Math.random() * 0.3) + 's';
        dropsContainer?.appendChild(drop);
    }
    if (anim) anim.classList.add('active');
    if (waterBtnLeft) waterBtnLeft.disabled = true;
}

function stopWateringAnimation() {
    const anim = document.getElementById('wateringAnim');
    if (anim) anim.classList.remove('active');
    if (waterBtnLeft) waterBtnLeft.disabled = false;
}

let musicPlaying = false;
const musicBtnEl = document.getElementById('musicBtn');
const bgMusic = document.getElementById('bgMusic');

if (bgMusic) bgMusic.src = 'music/song.mp3';

function tryAutoplay() {
    if (!bgMusic) return;
    bgMusic.play().then(() => {
        musicPlaying = true;
        if (musicBtnEl) musicBtnEl.textContent = '🎵';
    }).catch(() => {});
}

window.addEventListener('load', () => { setTimeout(tryAutoplay, 500); });

if (musicBtnEl) {
    musicBtnEl.addEventListener('click', () => {
        if (!bgMusic) return;
        if (musicPlaying) {
            bgMusic.pause();
            musicBtnEl.textContent = '🔇';
            musicPlaying = false;
        } else {
            bgMusic.play().catch(() => showNotification('Не удалось воспроизвести музыку', true));
            musicBtnEl.textContent = '🎵';
            musicPlaying = true;
        }
    });
}

const achievementsBtn = document.getElementById('achievementsBtn');
if (achievementsBtn) achievementsBtn.addEventListener('click', () => openModal(modalAchievements));
const closeAchievements = document.getElementById('closeAchievements');
if (closeAchievements) closeAchievements.addEventListener('click', () => closeModal(modalAchievements));
if (modalAchievements) modalAchievements.addEventListener('click', e => { if (e.target === modalAchievements) closeModal(modalAchievements); });

const waterCanBtn = document.getElementById('waterCanBtn');
if (waterCanBtn) {
    waterCanBtn.addEventListener('click', () => {
        renderWateringCanChoices();
        openModal(modalWaterCan);
    });
}

const closeWaterCan = document.getElementById('closeWaterCan');
if (closeWaterCan) {
    closeWaterCan.addEventListener('click', () => closeModal(modalWaterCan));
}

if (modalWaterCan) {
    modalWaterCan.addEventListener('click', (e) => {
        if (e.target === modalWaterCan) closeModal(modalWaterCan);
    });
}

const helpBtn = document.getElementById('helpBtn');
if (helpBtn) {
    helpBtn.addEventListener('click', () => {
        openTutorial();
    });
}

const exitBtn = document.getElementById('exitBtn');
if (exitBtn) {
    exitBtn.addEventListener('click', () => {
        if (confirm('Выйти из аккаунта?')) {
            saveState();
            localStorage.removeItem('username');
            localStorage.removeItem('userId');
            localStorage.removeItem('session_token');
            localStorage.removeItem('isReturningUser');
            fetch(`${API_BASE_URL}/auth/logout`, {
                method: 'POST',
                credentials: 'include',
                headers: getAuthHeaders()
            })
                .finally(() => { window.location.href = 'register.html'; });
        }
    });
}

const cancelMove = document.getElementById('cancelMove');
if (cancelMove) {
    cancelMove.addEventListener('click', () => {
        closeModal(modalMovePlant);
        moveFromSlot = null;
    });
}

if (modalMovePlant) {
    modalMovePlant.addEventListener('click', (e) => {
        if (e.target === modalMovePlant) {
            closeModal(modalMovePlant);
            moveFromSlot = null;
        }
    });
}

document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
        [modalPlacePot, modalPickFlower, zoomOverlay, modalAchievements, modalWaterCan, modalRepot, modalMovePlant].forEach(closeModal);
    }
});

function loadState() {
    try {
        const raw = localStorage.getItem(`garden_${currentUser}`);
        if (raw) {
            const parsed = JSON.parse(raw);
            Object.assign(slotData, parsed);
            slots.forEach(slot => {
                const name = slot.dataset.slot;
                if (slotData[name]) {
                    if (slotData[name].plant && slotData[name].plantedAt) {
                        applyGrowthFromTime(name);
                    }
                    renderSlot(slot, slotData[name]);
                    if (slotData[name].plant && slotData[name].stage < 2) {
                        scheduleGrowth(name);
                    }
                    if (slotData[name].plant) {
                        scheduleLocationCheck(name);
                    }
                }
            });
        }
    } catch (e) {
        console.warn('Не удалось загрузить состояние комнаты', e);
    }
}

function applyGrowthFromTime(slotName) {
    const data = slotData[slotName];
    if (!data || !data.plant || !data.plantedAt) return;

    const msSincePlanted = Date.now() - data.plantedAt;

    if (msSincePlanted >= BLOOM_MS && data.stage < 2) {
        syncSlotHealthChecks(slotName);
        const dataAfter = slotData[slotName];
        const plant = PLANTS[dataAfter.plant];
        const bloomBlock = getBloomBlockReason(dataAfter, plant);
        if (!bloomBlock && dataAfter.stage >= 1) {
            const oldStage = dataAfter.stage;
            dataAfter.stage = 2;
            dataAfter.bloomedAt = dataAfter.bloomedAt || (dataAfter.plantedAt + BLOOM_MS);
            const slotEl = document.querySelector(`[data-slot="${slotName}"]`);
            if (slotEl) renderSlot(slotEl, dataAfter);

            if (oldStage !== 2) {
                showNotification(`🌸 ${PLANTS[dataAfter.plant]?.name} расцвело!`, false);
                checkAllAchievementsOnBloom(slotName, dataAfter);
            }
            saveState();
            checkQuestsAfterAction();
        } else if (bloomBlock) {
            showNotification(`⚠️ ${PLANTS[dataAfter.plant]?.name} ${bloomBlock}!`, true);
        }
    } else if (msSincePlanted >= SEEDLING_MS && data.stage < 1) {
        const oldStage = data.stage;
        data.stage = 1;
        data.sproutedAt = data.sproutedAt || (data.plantedAt + SEEDLING_MS);
        const slotEl = document.querySelector(`[data-slot="${slotName}"]`);
        if (slotEl) renderSlot(slotEl, data);

        if (oldStage !== 1) {
            showNotification(`🌱 ${PLANTS[data.plant]?.name} дало росток!`, false);
            setTimeout(() => {
                checkLocationDisease(slotName);
                if (data.lastWateredAt) {
                    checkWateringHealth(slotName, data);
                }
            }, 100);
        }
        saveState();
        checkQuestsAfterAction();
    }
}

function scheduleGrowth(slotName) {
    const data = slotData[slotName];
    if (!data || !data.plant || !data.plantedAt) return;

    const now = Date.now();
    const msSincePlanted = now - data.plantedAt;

    if (data.stage === 0 && msSincePlanted < SEEDLING_MS) {
        const msUntilSeedling = Math.max(0, SEEDLING_MS - msSincePlanted);
        setTimeout(() => {
            const d = slotData[slotName];
            if (!d || !d.plant || d.stage !== 0) return;
            d.stage = 1;
            d.sproutedAt = Date.now();
            const slotEl = document.querySelector(`[data-slot="${slotName}"]`);
            if (slotEl) renderSlot(slotEl, d);
            showNotification(`🌱 ${PLANTS[d.plant]?.name} дало росток!`, false);
            saveState();
            checkQuestsAfterAction();
            scheduleGrowth(slotName);
        }, msUntilSeedling);
    } else if (data.stage === 1 && msSincePlanted < BLOOM_MS) {
        const msUntilBloom = Math.max(0, BLOOM_MS - msSincePlanted);
        setTimeout(() => {
            const d = slotData[slotName];
            if (!d || !d.plant || d.stage !== 1) return;
            syncSlotHealthChecks(slotName);
            const fresh = slotData[slotName];
            const plant = PLANTS[fresh.plant];
            const bloomBlock = getBloomBlockReason(fresh, plant);
            if (bloomBlock) {
                showNotification(`⚠️ ${PLANTS[fresh.plant]?.name} ${bloomBlock}!`, true);
                return;
            }
            fresh.stage = 2;
            fresh.bloomedAt = Date.now();
            const slotEl = document.querySelector(`[data-slot="${slotName}"]`);
            if (slotEl) renderSlot(slotEl, fresh);
            showNotification(`🌸 ${PLANTS[fresh.plant]?.name} расцвело!`, false);
            checkAllAchievementsOnBloom(slotName, fresh);
            saveState();
            checkQuestsAfterAction();
        }, msUntilBloom);
    }
}

function loadLevel() {
    const lvl = parseInt(localStorage.getItem(`currentLevel_${currentUser}`) || '1');
    updateLevelCircle(lvl);
}

const TOTAL_STEPS = 4;
let tutStep = 0;

function showTutStep(n) {
    const steps = document.querySelectorAll('.tutorial-step');
    const dots = document.querySelectorAll('.tut-dot');

    if (n < 0) n = 0;
    if (n >= TOTAL_STEPS) n = TOTAL_STEPS - 1;
    tutStep = n;

    for (let i = 0; i < steps.length; i++) {
        if (i === n) {
            steps[i].classList.add('active');
        } else {
            steps[i].classList.remove('active');
        }
    }

    for (let i = 0; i < dots.length; i++) {
        if (i === n) {
            dots[i].classList.add('active');
        } else {
            dots[i].classList.remove('active');
        }
    }
}

function closeTutorial() {
    const overlay = document.getElementById('tutorialOverlay');
    if (overlay) {
        overlay.style.display = 'none';
        overlay.classList.remove('active');
    }
    if (currentUser) {
        localStorage.setItem(`tutorialDone_${currentUser}`, '1');
    }
    tutStep = 0;
}

function openTutorial() {
    tutStep = 0;
    showTutStep(0);
    const overlay = document.getElementById('tutorialOverlay');
    if (overlay) {
        overlay.style.display = 'flex';
        overlay.classList.add('active');
    }
}

function nextTutorialStep() {
    if (tutStep >= TOTAL_STEPS - 1) {
        closeTutorial();
    } else {
        tutStep++;
        showTutStep(tutStep);
    }
}

function goToTutorialStep(step) {
    tutStep = step;
    showTutStep(tutStep);
}

window.closeTutorialGlobal = function() {
    closeTutorial();
    return false;
};

window.nextTutorialGlobal = function() {
    nextTutorialStep();
    return false;
};

window.goToTutorialStep = function(step) {
    goToTutorialStep(step);
    return false;
};

if (tutorialOverlay) {
    tutorialOverlay.addEventListener('click', function(e) {
        if (e.target === tutorialOverlay) {
            closeTutorial();
        }
    });
}

updateRoomScale();
window.addEventListener('resize', updateRoomScale);

(async function init() {

    const loadingOverlay = document.createElement('div');
    loadingOverlay.id = 'loadingOverlay';
    loadingOverlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.8);z-index:10000;display:flex;justify-content:center;align-items:center;flex-direction:column;';
    loadingOverlay.innerHTML = '<div style="font-size:50px;animation:spin 1s linear infinite;">🌱</div><div style="color:white;margin-top:20px;">Загрузка игры...</div>';
    document.body.appendChild(loadingOverlay);

    const style = document.createElement('style');
    style.textContent = '@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }';
    document.head.appendChild(style);

    const isAuth = await checkAuth();
    if (!isAuth) return;

    const results = await Promise.all([
        loadPlantsCatalog(),
        loadPots(),
        loadWateringCans()
    ]);

    if (!results[0] || Object.keys(PLANTS).length === 0) {
        console.warn('Не удалось загрузить растения, использую стандартные');
        setDefaultPlants();
    }

    if (!results[1] || Object.keys(POT_CONFIG).length === 0) {
        console.warn('Не удалось загрузить горшки, использую стандартные');
        setDefaultPots();
    }

    if (!results[2] || Object.keys(WATERING_CAN_CONFIG).length === 0) {
        console.warn('Не удалось загрузить лейки, использую стандартные');
        setDefaultWateringCans();
    }

    loadLevel();
    checkAndUnlockPots();
    checkAndUnlockWateringCans();
    const loadedFromServer = await loadStateFromServer();
    if (!loadedFromServer) {
        loadState();
    }
    renderQuests();
    renderPotChoices();
    renderFlowerChoices();
    renderWateringCanChoices();
    updateAchievementsDisplay();
    initAchievementsClick();
    scheduleOverwateringCheck();

    const savedCan = localStorage.getItem(`currentWateringCan_${currentUser}`);
    updateWateringCanDisplay(savedCan ? parseInt(savedCan) : 1);

    const today = new Date().toDateString();
    const lastVisit = localStorage.getItem(`lastVisitDate_${currentUser}`);
    if (lastVisit !== today) {
        localStorage.setItem(`lastVisitDate_${currentUser}`, today);
        if (lastVisit) {
            const yesterday = new Date(lastVisit);
            yesterday.setDate(yesterday.getDate() + 1);
            if (yesterday.toDateString() === today) {
                const streak = getLoginStreak() + 1;
                localStorage.setItem(`loginStreak_${currentUser}`, String(streak));
                checkAchievement_streak(streak);
                checkQuestsAfterAction();
            } else {
                localStorage.setItem(`loginStreak_${currentUser}`, '1');
            }
        } else {
            localStorage.setItem(`loginStreak_${currentUser}`, '1');
        }
    }

    const isNewUser = localStorage.getItem('isReturningUser') === 'false';
    const tutDone = localStorage.getItem(`tutorialDone_${currentUser}`);
    if (isNewUser && !tutDone) {
        showTutStep(0);
        setTimeout(() => openModal(tutorialOverlay), 600);
    }

    loadingOverlay.remove();
})();

// ===== DEV LEVEL UP (временная отладка уровня) =====
const DEV_MAX_LEVEL = 6;

function applyUnlocksForLevel(level) {
    Object.entries(POT_CONFIG).forEach(([num, cfg]) => {
        POT_CONFIG[num].isUnlocked = (cfg.unlockLevel || 1) <= level;
    });
    Object.entries(WATERING_CAN_CONFIG).forEach(([id, cfg]) => {
        WATERING_CAN_CONFIG[id].isUnlocked = (cfg.unlockLevel || 1) <= level;
    });
}

function resetDevLevelToOne() {
    cancelPendingQuestLevelUp();
    localStorage.setItem(`questsDone_${currentUser}`, '[]');
    for (let lvl = 1; lvl <= 5; lvl++) {
        localStorage.removeItem(`levelUp_${lvl}_done_${currentUser}`);
    }
    localStorage.setItem(`currentLevel_${currentUser}`, '1');
    updateLevelCircle(1);
    applyUnlocksForLevel(1);
}

function refreshUiAfterDevLevelChange() {
    suppressQuestAutoLevelUp = true;
    try {
        renderQuests();
        renderPotChoices();
        renderFlowerChoices();
        renderWateringCanChoices();
    } finally {
        suppressQuestAutoLevelUp = false;
    }
}

function stepDevLevel() {
    if (!currentUser) return;

    cancelPendingQuestLevelUp();

    if (currentLevel >= DEV_MAX_LEVEL) {
        resetDevLevelToOne();
        refreshUiAfterDevLevelChange();
        saveState();
        showNotification('🛠️ DEV LEVEL UP: сброс на 1-й уровень', false);
        return;
    }

    const prevLevel = currentLevel;
    const newLevel = currentLevel + 1;

    if (prevLevel >= 1 && prevLevel <= 5) {
        localStorage.setItem(`levelUp_${prevLevel}_done_${currentUser}`, '1');
    }

    localStorage.setItem(`currentLevel_${currentUser}`, String(newLevel));
    updateLevelCircle(newLevel);
    applyUnlocksForLevel(newLevel);

    refreshUiAfterDevLevelChange();
    checkAndUnlockPots();
    checkAndUnlockWateringCans();
    saveState();

    showNotification(`🛠️ DEV LEVEL UP: уровень ${newLevel}`, false);
}

const devBtn = document.getElementById('devBtn');
if (devBtn) {
    devBtn.addEventListener('click', stepDevLevel);
}

// ===== DEV: панель переключения состояний =====
const devStatePanel = document.getElementById('devStatePanel');

document.getElementById('zoomOverlay')?.addEventListener('transitionend', () => {
    if (devStatePanel) {
        devStatePanel.style.display = zoomedSlot ? 'block' : 'none';
    }
});

const devApplyState = document.getElementById('devApplyState');
if (devApplyState) {
    devApplyState.addEventListener('click', () => {
        if (!zoomedSlot) { alert('Сначала открой слот (кликни на горшок)'); return; }
        const name = zoomedSlot.name;
        const data = slotData[name];
        if (!data || !data.plant) { alert('В слоте нет растения'); return; }

        const state = document.getElementById('devStateSelect').value;
        const plant = PLANTS[data.plant];

        data.hasDisease = false;
        data.disease = null;
        data.diseaseStartTime = null;

        if (state === 'sprout') {
            data.stage = 1;
        } else if (state === 'healthy') {
            data.stage = 2;
        } else if (state === 'dead') {
            data.stage = 2;
            data.hasDisease = true;
            data.disease = '__dead__';
        } else {
            // значение = ключ болезни напрямую (желтение / вытягивание / не цветет / ...)
            data.stage = 2;
            data.hasDisease = true;
            data.disease = state;
        }

        saveState();
        const slotEl = zoomedSlot.slotEl;
        renderSlot(slotEl, data);
        openZoom(slotEl, name, data);
        if (devStatePanel) devStatePanel.style.display = 'block';
        console.log('[DEV] state:', state, '| disease:', data.disease, '| plant:', data.plant, '| pot:', data.pot);
    });
}
