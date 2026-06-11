const API_BASE_URL = 'http://localhost:5000/api';

const ROOM_DESIGN_WIDTH = 1280;
const ROOM_DESIGN_HEIGHT = 720;
const ZOOM_DESIGN_WIDTH = 780;
const ZOOM_DESIGN_HEIGHT = 500;
const ZOOM_VIEWPORT_FILL = 0.75;
const LETTERBOX_LOGO_MIN_HEIGHT = 88;

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
    if (typeof window.updateUIScale === 'function') window.updateUIScale();
}

function getAuthToken() {
    return localStorage.getItem('session_token');
}

function getAuthHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    const token = getAuthToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
    return headers;
}

let pendingWateringCanFromGame = null;

function normalizeWateringCanId(value) {
    if (value === 'standard') return 1;
    const id = parseInt(value, 10);
    return Number.isFinite(id) && id > 0 ? id : 1;
}

function getCurrentWateringCanId() {
    if (!currentUser) return 1;
    return normalizeWateringCanId(localStorage.getItem(`currentWateringCan_${currentUser}`));
}

function setCurrentWateringCanId(canId, { persistGame = false } = {}) {
    if (!currentUser) return;
    const id = normalizeWateringCanId(canId);
    if (!isWateringCanUnlocked(WATERING_CAN_CONFIG[id])) return;
    localStorage.setItem(`currentWateringCan_${currentUser}`, String(id));
    updateWateringCanDisplay(id);
    if (persistGame) saveState();
}

function restoreWateringCanSelection() {
    if (!currentUser) return;

    const candidates = [
        pendingWateringCanFromGame,
        getCurrentWateringCanId()
    ];

    for (const raw of candidates) {
        if (raw == null) continue;
        const id = normalizeWateringCanId(raw);
        if (WATERING_CAN_CONFIG[id] && isWateringCanUnlocked(WATERING_CAN_CONFIG[id])) {
            setCurrentWateringCanId(id, { persistGame: false });
            pendingWateringCanFromGame = null;
            return;
        }
    }

    setCurrentWateringCanId(1, { persistGame: false });
    pendingWateringCanFromGame = null;
}

async function saveStateToServer() {
    if (!currentUser) return;

    const stateToSave = {
        slotData: slotData,
        currentLevel: currentLevel,
        achievements: {}
    };

    const achievements = ['caring_parent', 'collector', 'flora_guard', 'patient_gardener', 'oops_error', 'all_lost'];
    achievements.forEach(id => {
        stateToSave.achievements[id] = localStorage.getItem(`achievement_unlocked_${currentUser}_${id}`) === 'true';
    });
    stateToSave.achievements.__currentWateringCan = getCurrentWateringCanId();

    try {
        const response = await fetch(`${API_BASE_URL}/game/save`, {
            method: 'POST',
            headers: getAuthHeaders(),
            credentials: 'include',
            body: JSON.stringify(stateToSave)
        });
        await response.json();
    } catch (error) {
        console.error('Ошибка сохранения на сервер:', error);
    }
}

function normalizeTipsLines(input) {
    if (input == null || input === '') return [];
    const rawItems = Array.isArray(input) ? input : [input];
    return rawItems
        .flatMap((item) => String(item).replace(/\\n/g, '\n').split(/\r?\n|\|/))
        .map((line) => line.trim().replace(/^[•\-–—]\s*/, ''))
        .filter(Boolean);
}

async function loadStateFromServer() {
    if (!currentUser) return false;

    try {
        const response = await fetch(`${API_BASE_URL}/game/load`, {
            method: 'GET',
            headers: getAuthHeaders(),
            credentials: 'include'
        });
        const data = await response.json();

        if (data.success) {
            if (data.achievements?.__currentWateringCan != null) {
                pendingWateringCanFromGame = normalizeWateringCanId(data.achievements.__currentWateringCan);
            }

            if (data.slotData && Object.keys(data.slotData).length > 0) {
                Object.assign(slotData, data.slotData);
            }

            if (data.currentLevel) {
                currentLevel = data.currentLevel;
                localStorage.setItem(`currentLevel_${currentUser}`, String(currentLevel));
                updateLevelCircle(currentLevel);
            }

            if (data.achievements) {
                for (const [id, unlocked] of Object.entries(data.achievements)) {
                    if (id.startsWith('__')) continue;
                    if (unlocked) {
                        localStorage.setItem(`achievement_unlocked_${currentUser}_${id}`, 'true');
                    }
                }
            }

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
                        if (slotData[name].hasDisease || isPlantDead(slotData[name])) {
                            scheduleSicknessDeathCheck(name);
                        }
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

function saveState() {
    localStorage.setItem(`garden_${currentUser}`, JSON.stringify({
        slotData,
        currentWateringCan: getCurrentWateringCanId()
    }));
    saveStateToServer().catch(console.error);
}

let PLANTS = {};
let POT_CONFIG = {};
let WATERING_CAN_CONFIG = {};

const POT_DISPLAY_NAMES = {
    1: 'Обычный',
    2: 'С рисунком',
    3: 'Большой'
};

const WATERING_CAN_DISPLAY_NAMES = {
    1: 'Бежевая',
    2: 'Розовая'
};

function applyPotDisplayNames(pots) {
    Object.keys(pots).forEach(num => {
        const key = parseInt(num, 10);
        if (POT_DISPLAY_NAMES[key]) pots[num].name = POT_DISPLAY_NAMES[key];
    });
}

function applyWateringCanDisplayNames(cans) {
    Object.keys(cans).forEach(id => {
        const key = normalizeWateringCanId(id);
        if (WATERING_CAN_DISPLAY_NAMES[key]) cans[id].name = WATERING_CAN_DISPLAY_NAMES[key];
    });
}

let currentLevel = 1;
let currentUser = null;
let currentZoomedPlantId = null;

const SEEDLING_MS = 10 * 1000;
const BLOOM_MS = 61 * 1000;
const WATER_TIMING_TEST = true;
const TEST_WATER_MIN_MS = 20 * 1000;
const TEST_WATER_MAX_MS = 60 * 1000;
const OVERWATER_MIN_FAST_POLIVS = 2;
const SICK_UNTIL_DEATH_MS = WATER_TIMING_TEST ? 45 * 1000 : 5 * 24 * 3600000;
const SICK_DEATH_CHECK_TICK_MS = WATER_TIMING_TEST ? 5 * 1000 : 60 * 60 * 1000;

function plantVisual(bottom, width, pot1, pot2, pot3, extra = {}) {
    return {
        bottom,
        width,
        left: '50%',
        pots: {
            1: { slotLift: pot1[0], zoomLift: pot1[1] },
            2: { slotLift: pot2[0], zoomLift: pot2[1] },
            3: { slotLift: pot3[0], zoomLift: pot3[1] }
        },
        ...extra
    };
}

const PLANT_VISUAL_CONFIG = {
    1: {
        sprout: plantVisual('35px', '90px', [18, 42], [12, 32], [36, 63]),
        bloom: plantVisual('20px', '120px', [19, 39], [12, 29], [37, 57]),
        dead: plantVisual('35px', '100px', [-42, -39], [-48, -48], [-24, -21]),
        diseases: {
            too_light: plantVisual('35px', '100px', [40, 69], [34, 59], [58, 86], { imageKey: 'желтение' }),
            big_pot: plantVisual('35px', '95px', [51, 84], [45, 75], [69, 103], { imageKey: 'не цветет' }),
            under_watered: plantVisual('35px', '100px', [44, 75], [38, 65], [63, 94], { imageKey: 'сохнут кончики' }),
            overwatered: plantVisual('35px', '100px', [40, 69], [34, 59], [58, 86], { imageKey: 'желтение' })
        }
    },
    2: {
        sprout: plantVisual('45px', '60px', [10, 35], [4, 26], [28, 54]),
        bloom: plantVisual('40px', '70px', [-28, -19], [-34, -27], [-9, -1]),
        dead: plantVisual('40px', '65px', [-28, -18], [-34, -28], [-10, 0]),
        diseases: {
            too_dark: plantVisual('50px', '30px', [36, 70], [30, 60], [54, 88], { imageKey: 'вытягивание' }),
            no_flower: plantVisual('45px', '35px', [40, 73], [34, 64], [58, 90], { imageKey: 'не цветет' }),
            under_watered: plantVisual('38px', '34px', [42, 75], [36, 66], [60, 93], { imageKey: 'сморщенный стебель' }),
            overwatered: plantVisual('38px', '34px', [42, 75], [36, 66], [60, 93], { imageKey: 'сморщенный стебель' })
        }
    },
    3: {
        sprout: plantVisual('40px', '75px', [-33, -23], [-38, -32], [-13, -4]),
        bloom: plantVisual('35px', '125px', [-19, -6], [-25, -14], [0, 12]),
        dead: plantVisual('19px', '95px', [-28, -25], [-33, -34], [-10, -8]),
        diseases: {
            too_light: plantVisual('40px', '80px', [34, 66], [27, 58], [52, 84], { imageKey: 'пятна' }),
            under_watered: plantVisual('40px', '75px', [42, 77], [35, 67], [60, 96], { imageKey: 'желтение' }),
            overwatered: plantVisual('40px', '55px', [43, 81], [38, 71], [62, 101], { imageKey: 'увядание' })
        }
    }
};

function getVisualStateEntry(plantId, stateKey) {
    const cfg = PLANT_VISUAL_CONFIG[plantId] || PLANT_VISUAL_CONFIG[1];
    if (!cfg || !stateKey) return null;
    if (stateKey === 'sprout' || stateKey === 'bloom' || stateKey === 'dead') return cfg[stateKey];
    return cfg.diseases?.[stateKey] || null;
}

function resolveVisualStateKey(plantId, stage, diseaseText = null, diseaseType = null) {
    if (diseaseText === '__dead__' || diseaseType === 'dead') return 'dead';
    if (diseaseType && PLANT_VISUAL_CONFIG[plantId]?.diseases?.[diseaseType]) return diseaseType;
    if (diseaseText || diseaseType) {
        const imageKey = getDiseaseImageKeyForPlant(plantId, diseaseType, diseaseText);
        if (imageKey) {
            for (const [type, entry] of Object.entries(PLANT_VISUAL_CONFIG[plantId]?.diseases || {})) {
                if (entry.imageKey === imageKey) return type;
            }
        }
    }
    return Number(stage) >= 2 ? 'bloom' : 'sprout';
}

function getVisualEntryByDisease(plantId, diseaseType, diseaseText) {
    const pid = parseInt(plantId, 10) || 1;
    const stateKey = resolveVisualStateKey(pid, 1, diseaseText, diseaseType);
    if (stateKey === 'sprout' || stateKey === 'bloom') return null;
    return getVisualStateEntry(pid, stateKey);
}

function getDiseaseImageKeyForPlant(plantId, diseaseType, diseaseText) {
    const pid = parseInt(plantId, 10) || 1;
    const fromVisual = PLANT_VISUAL_CONFIG[pid]?.diseases?.[diseaseType]?.imageKey;
    if (fromVisual) return fromVisual;
    if (diseaseType && PLANT_DISEASE_TO_IMAGE_KEY[pid]?.[diseaseType]) {
        return PLANT_DISEASE_TO_IMAGE_KEY[pid][diseaseType];
    }
    if (!diseaseText) return null;
    const norm = normalizePlantText(diseaseText);
    for (const [type, imageKey] of Object.entries(PLANT_DISEASE_TO_IMAGE_KEY[pid] || {})) {
        const msg = PLANT_DISEASES[pid]?.[type];
        if (!msg) continue;
        const normMsg = normalizePlantText(msg);
        if (norm === normMsg || norm.includes(normMsg) || normMsg.includes(norm)) {
            return imageKey;
        }
    }
    for (const entry of Object.values(PLANT_VISUAL_CONFIG[pid]?.diseases || {})) {
        if (entry.imageKey && norm.includes(normalizePlantText(entry.imageKey))) return entry.imageKey;
    }
    return null;
}

function getPlantOffsets(plantId, stage, diseaseText = null, diseaseType = null) {
    const pid = parseInt(plantId, 10) || 1;
    const entry = getVisualEntryByDisease(pid, diseaseType, diseaseText)
        || getVisualStateEntry(pid, resolveVisualStateKey(pid, stage, diseaseText, diseaseType));
    if (!entry) return { bottom: '40px', width: '70px', left: '50%' };
    return { bottom: entry.bottom, width: entry.width, left: entry.left || '50%' };
}

function getPotLift(type, plantId, potNum, stage, hasDisease, disease, diseaseType = null) {
    const pid = parseInt(plantId, 10) || 1;
    const pot = parseInt(potNum, 10) || 1;
    let entry;
    if (disease === '__dead__' || diseaseType === 'dead') {
        entry = getVisualStateEntry(pid, 'dead');
    } else if (hasDisease && (disease || diseaseType)) {
        entry = getVisualEntryByDisease(pid, diseaseType, disease);
    } else {
        entry = getVisualStateEntry(pid, Number(stage) >= 2 ? 'bloom' : 'sprout');
    }
    const lifts = entry?.pots?.[pot] || entry?.pots?.[1];
    if (!lifts) return 0;
    return type === 'zoom' ? (lifts.zoomLift ?? 0) : (lifts.slotLift ?? 0);
}

function getSlotPlantExtraLift(plantId, potNum, stage, hasDisease, disease, diseaseType = null) {
    return getPotLift('slot', plantId, potNum, stage, hasDisease, disease, diseaseType);
}

function getZoomPlantLift(plantId, potNum, stage, hasDisease, disease, diseaseType = null) {
    return getPotLift('zoom', plantId, potNum, stage, hasDisease, disease, diseaseType);
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

async function markTutorialCompleteOnServer() {
    try {
        await fetch(`${API_BASE_URL}/auth/complete_tutorial`, {
            method: 'POST',
            credentials: 'include',
            headers: getAuthHeaders()
        });
    } catch (error) {
        console.error('Не удалось сохранить прохождение обучения:', error);
    }
}
async function checkAuth() {
    try {
        const response = await fetch(`${API_BASE_URL}/auth/verify`, {
            method: 'GET',
            credentials: 'include',
            headers: getAuthHeaders()
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

        if (data.need_tutorial === false) {
            localStorage.setItem('isReturningUser', 'true');
            localStorage.removeItem('pendingFirstTimeTutorial');
        } else if (data.need_tutorial === true && localStorage.getItem('isReturningUser') !== 'false') {
            localStorage.setItem('isReturningUser', 'true');
            localStorage.removeItem('pendingFirstTimeTutorial');
        }

        currentUser = localStorage.getItem('username');
        return true;
    } catch (error) {
        console.error('Ошибка проверки авторизации:', error);
        window.location.href = 'register.html';
        return false;
    }
}

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
                    nickname: plant.nickname || '',
                    description: plant.description || 'Описание отсутствует',
                    character_trait: plant.character_trait || '',
                    character_description: plant.character_description || '',
                    waterAdvice: plant.watering_advice || 'Поливай по графику',
                    lightAdvice: plant.light_advice || 'Обеспечь правильное освещение',
                    tips: Array.isArray(plant.tips) ? plant.tips.join('|') : (plant.tips || 'Бережный уход - залог здоровья'),
                    waterIntervalMin: plant.water_interval_min || 24,
                    waterIntervalMax: plant.water_interval_max || 48,
                    unlockLevel: plant.unlock_level || 1,
                    plantFolder: plantFolder,
                    stages: {
                        1: `images/plant/${plantFolder}/stage/росток.png`,
                        2: `images/plant/${plantFolder}/stage/выросший.png`
                    },
                    diseaseImages: diseaseImages,
                    deadImage: assets.deadImage,
                    watering_advice: plant.watering_advice || '',
                    light_advice: plant.light_advice || '',
                    fullDescription: plant.description || '',
                    tips_array: plant.tips || [],
                    advice_list: normalizeTipsLines(plant.tips || []),
                    symptoms: plant.symptoms || [],
                    why_disease: plant.why_disease || '',
                    flowering_conditions: plant.flowering_conditions || ''
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
            const storedLevel = parseInt(localStorage.getItem(`currentLevel_${currentUser}`) || '1', 10);
            const userLevel = Math.max(data.user_level || 1, storedLevel, currentLevel);

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
            applyPotDisplayNames(pots);
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
            const storedLevel = parseInt(localStorage.getItem(`currentLevel_${currentUser}`) || '1', 10);
            const userLevel = Math.max(data.user_level || 1, storedLevel, currentLevel);
            if (userLevel > currentLevel) currentLevel = userLevel;
            const unlockedCans = (data.unlocked_cans || []).map(String);

            data.all_cans.forEach(can => {
                let canId = parseInt(can.id, 10);
                if (!Number.isFinite(canId)) canId = can.id;
                const unlockLevel = can.unlock_level || 1;
                const canKey = String(can.id);
                const isUnlocked = unlockLevel <= userLevel
                    || unlockedCans.includes(canKey)
                    || (canKey === '1' && unlockedCans.includes('standard'))
                    || (canKey === '2' && unlockedCans.includes('2'));

                cans[canId] = {
                    name: can.name,
                    img: can.image,
                    unlockLevel: unlockLevel,
                    isUnlocked: isUnlocked,
                    id: can.id
                };
            });
            applyWateringCanDisplayNames(cans);
            WATERING_CAN_CONFIG = cans;
            checkAndUnlockWateringCans();
            const serverCan = data.current?.watering_can;
            if (serverCan && pendingWateringCanFromGame == null) {
                const normalized = normalizeWateringCanId(serverCan);
                if (cans[normalized]?.isUnlocked) {
                    pendingWateringCanFromGame = normalized;
                }
            }
            return true;
        }
        return false;
    } catch (error) {
        console.error('Ошибка загрузки леек:', error);
        return false;
    }
}

function isWateringCanUnlocked(cfg) {
    if (!cfg) return false;
    if (cfg.isUnlocked) return true;
    const unlockLevel = cfg.unlockLevel || 1;
    return unlockLevel <= currentLevel;
}

function applyWateringCanChange(canId, canConfig) {
    setCurrentWateringCanId(canId, { persistGame: false });
    showNotification(`Лейка сменена на ${canConfig.name}! 💧`, false);
    if (modalWaterCan) closeModal(modalWaterCan);
    renderWateringCanChoices();
    saveState();
}

const STAGE_NAMES = ['🌰 Семечко посажено', '🌱 Росток', '🌸 Расцвёл'];
const PLANT_SICK_LABEL = 'Болеет';
const PLANT_DEAD_LABEL = 'Умерло';

const LEVEL_REWARDS = {
    2: '🎉 Получен новый горшок «С рисунком»!',
    3: '🌵 Получен новый цветок (Кактус)!',
    4: '💧 Получена новая лейка «Розовая»!',
    5: '🌿 Получен новый цветок (Фикус)!',
    6: '🏆 Получен горшок «Большой» и ачивка «Страж флоры»!'
};

const slotData = {};
let activeSlot = null;
let zoomedSlot = null;
let zoomTimerTickId = null;

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
const devStatePanel = document.getElementById('devStatePanel');
const devStateSelect = document.getElementById('devStateSelect');
const devApplyStateBtn = document.getElementById('devApplyState');

const NOTIFICATION_DURATION_MS = 10 * 1000;
let notificationIdSeq = 0;
const activeNotifications = [];

function refreshNotificationLayers() {
    activeNotifications.forEach((entry, index) => {
        const isTop = index === activeNotifications.length - 1;
        entry.element.classList.toggle('is-covered', !isTop);
        entry.element.style.zIndex = String(400 + index);
    });
}

function dismissNotification(id) {
    const index = activeNotifications.findIndex(n => n.id === id);
    if (index === -1) return;

    const [entry] = activeNotifications.splice(index, 1);
    clearTimeout(entry.timer);

    const removeEl = () => {
        entry.element.remove();
        refreshNotificationLayers();
    };

    entry.element.classList.remove('show');
    const onEnd = (e) => {
        if (e.propertyName !== 'transform') return;
        entry.element.removeEventListener('transitionend', onEnd);
        removeEl();
    };
    entry.element.addEventListener('transitionend', onEnd);
    setTimeout(() => {
        if (entry.element.isConnected) removeEl();
    }, 400);
}

function showNotification(message, isError = false) {
    const stack = document.getElementById('notificationStack');
    if (!stack) return;

    const id = ++notificationIdSeq;
    const el = document.createElement('div');
    el.className = `notification-item light-notification${isError ? ' is-error' : ''}`;
    el.dataset.notifId = String(id);
    el.innerHTML = `
        <span class="notif-icon">${isError ? '❌' : '✅'}</span>
        <span class="notif-text"></span>
        <button type="button" class="notif-close" aria-label="Закрыть уведомление">×</button>
    `;
    el.querySelector('.notif-text').textContent = message;
    el.querySelector('.notif-close').addEventListener('click', () => dismissNotification(id));

    stack.appendChild(el);
    requestAnimationFrame(() => {
        refreshNotificationLayers();
        el.classList.add('show');
    });

    const timer = setTimeout(() => dismissNotification(id), NOTIFICATION_DURATION_MS);
    activeNotifications.push({ id, element: el, timer });
}

function openModal(el) { if (el) el.classList.add('active'); }
function closeModal(el) {
    if (el) el.classList.remove('active');
    if (el === zoomOverlay) stopZoomTimerTick();
}

function getWheelScrollDelta(e, scrollEl) {
    if (e.deltaMode === 1) return e.deltaY * 16;
    if (e.deltaMode === 2) return e.deltaY * scrollEl.clientHeight;
    return e.deltaY;
}

function wheelScrollBy(scrollEl, delta) {
    const maxTop = Math.max(0, scrollEl.scrollHeight - scrollEl.clientHeight);
    scrollEl.scrollTop = Math.max(0, Math.min(maxTop, scrollEl.scrollTop + delta));
}

const WHEEL_SCROLL_LAYERS = [
    { overlayId: 'modalPlantDescription', scrollSelector: '.plant-desc-text-wrapper' },
    { overlayId: 'modalAchievements', scrollSelector: '.achievements-grid-custom' },
];

function getActiveWheelScrollTarget() {
    for (const { overlayId, scrollSelector } of WHEEL_SCROLL_LAYERS) {
        const overlay = document.getElementById(overlayId);
        if (!overlay?.classList.contains('active')) continue;
        const scrollEl = overlay.querySelector(scrollSelector);
        if (scrollEl) return scrollEl;
    }
    if (document.querySelector('.modal-overlay.active, .tutorial-overlay.active')) return null;
    const questsList = document.querySelector('.quests-list');
    if (questsList && questsList.scrollHeight > questsList.clientHeight) return questsList;
    return null;
}

document.addEventListener('wheel', (e) => {
    const scrollEl = getActiveWheelScrollTarget();
    if (!scrollEl) return;
    e.preventDefault();
    wheelScrollBy(scrollEl, getWheelScrollDelta(e, scrollEl));
}, { passive: false });

function stopZoomTimerTick() {
    if (zoomTimerTickId !== null) {
        clearInterval(zoomTimerTickId);
        zoomTimerTickId = null;
    }
}

function refreshZoomPanelTimers() {
    if (!zoomedSlot?.name) return;

    const slotName = zoomedSlot.name;
    const data = slotData[slotName];
    if (!data?.plant) return;

    const prevStage = data.stage;
    if (!isPlantDead(data)) {
        applyGrowthFromTime(slotName);
    }

    const fresh = slotData[slotName];
    if (!fresh) return;

    if (fresh.stage !== prevStage) {
        refreshPlantVisual(slotName);
    }

    updateGrowthTimer(fresh);
    updateNextWateringTimer(fresh);
}

function startZoomTimerTick() {
    stopZoomTimerTick();
    refreshZoomPanelTimers();
    zoomTimerTickId = setInterval(refreshZoomPanelTimers, 1000);
}

const ACHIEVEMENT_REASON_TOAST_MS = 5 * 1000;

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
    }, ACHIEVEMENT_REASON_TOAST_MS);
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
async function notifyAchievementToServer(event = null, extra = {}) {
    try {
        const body = event ? { event, ...extra } : {};
        await fetch(`${API_BASE_URL}/achievements/event`, {
            method: 'POST',
            credentials: 'include',
            headers: getAuthHeaders(),
            body: JSON.stringify(body)
        });
    } catch (e) {
        console.error('Ошибка синхронизации достижения с сервером:', e);
    }
}

async function loadAchievementsFromServer() {
    if (!currentUser) return;
    try {
        const resp = await fetch(`${API_BASE_URL}/achievements/`, {
            credentials: 'include',
            headers: getAuthHeaders()
        });
        const data = await resp.json();
        if (!data.success) return;

        const backToFrontId = {
            'grow_to_maturity_perfect': 'caring_parent',
            'first_wither':             'all_lost',
            'first_negative_effect':    'oops_error',
            'grow_all_species':         'collector',
            'daily_streak':             'patient_gardener',
            'reach_level':              'flora_guard'
        };

        data.achievements.forEach(ach => {
            if (ach.is_completed) {
                const frontId = backToFrontId[ach.requirement_type] || ach.requirement_type;
                localStorage.setItem(`achievement_unlocked_${currentUser}_${frontId}`, 'true');
            }
        });

        updateAchievementsDisplay();
    } catch (e) {
        console.error('Ошибка загрузки достижений с сервера:', e);
    }
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
            notifyAchievementToServer('perfect_growth');
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
            notifyAchievementToServer('species_collected');
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
            notifyAchievementToServer('reach_level');
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
            notifyAchievementToServer('daily_streak');
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
        notifyAchievementToServer('death');
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
        notifyAchievementToServer('mistake');
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

const NOTIFICATION_TEXTS = {
    disease: {
        overwatered: 'Ой, кажется, ты слишком любишь свой цветок. Перелив опаснее засухи. Дай земле просохнуть, прежде чем поливать снова! 🌱',
        under_watered: 'Пить хочется... Твой цветок показывает, что пора поливать. Не жди, пока земля превратится в пыль. Одна лейка — и он снова весёлый! 💧',
        too_light: 'Кажется, твоему другу не нравится его место. Попробуй переставить горшок туда, где посветлее. Свет — это важно! ☀️',
        too_dark: 'Кажется, твоему другу не нравится его место. Попробуй переставить горшок туда, где потемнее. Свет — это важно! ☀️',
        big_pot: 'Слишком большой горшок мешает зацвести. Пересади в горшок поменьше — цветку будет уютнее! 🪴',
        no_flower: 'Кажется, твоему другу не нравится его место. Попробуй переставить горшок туда, где посветлее. Свет — это важно! ☀️'
    },
    death: {
        first: 'Ничего страшного! Даже у настоящих садоводов бывает. Посади новый цветок — он будет рад тебя видеть. А я подскажу, как не повторить ту же ошибку. 💚',
        overwatered: 'Бедняга утонул... В следующий раз проверяй землю: если влажная — лейку в сторону. Попробуем ещё?',
        under_watered: 'Он ждал воды слишком долго... Поставь напоминание в телефоне или просто заглядывай почаще. Ты справишься!',
        too_light: 'Жара сделала своё дело. Но теперь ты знаешь: каждому цветку нужно своё место. Давай посадим новый?',
        too_dark: 'Тень сделала своё дело. Но теперь ты знаешь: каждому цветку нужно своё место. Давай посадим новый?',
        complex: 'Бывает. Не кори себя. Просто начни заново — твой сад никуда не денется. А я всегда рядом с советами. 🌸'
    },
    positive: {
        idealWater: 'Идеально! Ты чувствуешь своего зелёного друга. Так держать!',
        recovered: 'Ура! Снова здоров. Ты быстро научился понимать его сигналы. Горжусь тобой!',
        bloomed: 'Смотри-ка, цветок! Это значит, ты делаешь всё правильно. Красота 🥰',
        goodLocation: 'Ты выбрал правильное место! Цветочку тут комфортно'
    }
};

const POSITIVE_TIP_DAILY_LIMIT = 2;

function getPositiveTipsTodayCount() {
    const key = `positiveTips_${currentUser}_${new Date().toDateString()}`;
    return parseInt(localStorage.getItem(key) || '0', 10) || 0;
}

function bumpPositiveTipsTodayCount() {
    const dateKey = new Date().toDateString();
    const key = `positiveTips_${currentUser}_${dateKey}`;
    localStorage.setItem(key, String(getPositiveTipsTodayCount() + 1));
}

function showPositiveTip(tipKey) {
    const text = NOTIFICATION_TEXTS.positive[tipKey];
    if (!text) return;
    if (getPositiveTipsTodayCount() >= POSITIVE_TIP_DAILY_LIMIT) return;
    showNotification(text, false);
    bumpPositiveTipsTodayCount();
}

function showDiseaseAdvice(diseaseType) {
    const text = NOTIFICATION_TEXTS.disease[diseaseType];
    if (!text) return;
    showNotification(text, true);
}

function resolveDeathCauseType(data) {
    if (!data) return null;
    if (data.diseaseType && data.diseaseType !== 'dead') return data.diseaseType;
    const plantKey = resolveSpeciesId(data.plant, PLANTS[data.plant]);
    return getDiseaseTypeFromMessage(plantKey, data.disease);
}

function showPlantDeathNotification(data) {
    if (!data?.plant) return;

    const firstKey = `firstPlantDeath_${currentUser}`;
    const isFirst = !localStorage.getItem(firstKey);
    if (isFirst) localStorage.setItem(firstKey, '1');

    let text;
    if (isFirst) {
        text = NOTIFICATION_TEXTS.death.first;
    } else if (isComplexMistakeDeath(data)) {
        text = NOTIFICATION_TEXTS.death.complex;
    } else {
        const cause = resolveDeathCauseType(data);
        if (cause === 'overwatered') text = NOTIFICATION_TEXTS.death.overwatered;
        else if (cause === 'under_watered') text = NOTIFICATION_TEXTS.death.under_watered;
        else if (cause === 'too_light') text = NOTIFICATION_TEXTS.death.too_light;
        else if (cause === 'too_dark' || cause === 'no_flower') text = NOTIFICATION_TEXTS.death.too_dark;
        else text = NOTIFICATION_TEXTS.death.first;
    }

    showNotification(text, false);
}

const LOCATION_DISEASE_TYPES = ['too_light', 'too_dark', 'no_flower', 'big_pot'];
const WATER_DISEASE_TYPES = ['under_watered', 'overwatered'];

const MISTAKE_CATEGORY_BY_SOURCE = {
    water: 'water',
    location: 'place',
    pot: 'pot'
};

function createEmptyMistakeCategories() {
    return { water: false, place: false, pot: false };
}

function ensureMistakeCategories(data) {
    if (!data.mistakeCategories) {
        data.mistakeCategories = createEmptyMistakeCategories();
    }
    return data.mistakeCategories;
}

function recordPlantMistakeCategory(data, source) {
    const categoryKey = MISTAKE_CATEGORY_BY_SOURCE[source];
    if (!categoryKey || !data) return;
    ensureMistakeCategories(data)[categoryKey] = true;
}

function countMistakeCategories(data) {
    const cats = ensureMistakeCategories(data);
    return Object.values(cats).filter(Boolean).length;
}

function isComplexMistakeDeath(data) {
    return countMistakeCategories(data) >= 2;
}

function isPlantDead(data) {
    return data?.disease === '__dead__' || data?.diseaseType === 'dead';
}

function ensureDiseaseStartTime(data) {
    if (data?.hasDisease && !isPlantDead(data) && !data.diseaseStartTime) {
        data.diseaseStartTime = Date.now();
    }
}

function applyPlantDeath(slotName, data) {
    if (!data?.plant || isPlantDead(data)) return false;

    data.hasDisease = true;
    data.hadMistakes = true;
    data.disease = '__dead__';
    data.diseaseType = 'dead';
    data.diseaseSource = 'neglect';
    data.devManualState = false;

    showPlantDeathNotification(data);
    checkAchievement_death();
    saveState();

    refreshPlantVisual(slotName);
    return true;
}

function checkPlantDeathFromSickness(slotName) {
    const data = slotData[slotName];
    if (!data?.plant || data.stage < 1) return;
    if (data.devManualState || isPlantDead(data)) return;
    if (!data.hasDisease) return;

    ensureDiseaseStartTime(data);
    if (Date.now() - data.diseaseStartTime < SICK_UNTIL_DEATH_MS) return;

    applyPlantDeath(slotName, data);
}

function scheduleSicknessDeathCheck(slotName) {
    checkPlantDeathFromSickness(slotName);
    setTimeout(() => {
        const data = slotData[slotName];
        if (!data?.plant || isPlantDead(data)) return;
        if (data.hasDisease && !data.devManualState) {
            checkPlantDeathFromSickness(slotName);
            scheduleSicknessDeathCheck(slotName);
        }
    }, SICK_DEATH_CHECK_TICK_MS);
}

function resetZoomButtonDisabledState() {
    ['waterBtnLeft', 'descBtnRight', 'repotBtnLeft', 'moveBtnLeft', 'plantBtnLeft', 'removeBtnLeft'].forEach((id) => {
        const btn = document.getElementById(id);
        if (btn) btn.disabled = false;
    });
}

function setZoomControlsForPlantState(data) {
    const dead = isPlantDead(data);
    const ids = ['waterBtnLeft', 'repotBtnLeft', 'moveBtnLeft', 'plantBtnLeft'];
    ids.forEach((id) => {
        const btn = document.getElementById(id);
        if (!btn) return;
        btn.disabled = dead;
    });
    const removeBtn = document.getElementById('removeBtnLeft');
    if (removeBtn) removeBtn.disabled = false;

    const growthTimerBox = document.getElementById('growthTimerBox');
    const waterTimerBox = document.getElementById('waterTimerBox');
    if (dead) {
        if (growthTimerBox) growthTimerBox.style.display = 'none';
        if (waterTimerBox) waterTimerBox.style.display = 'none';
    }
}

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

function notifyBloomBlockedOnce(data, bloomBlock) {
    if (!data?.plant || !bloomBlock) return;
    if (data.bloomBlockNotified === bloomBlock) return;

    data.bloomBlockNotified = bloomBlock;
    const plantName = PLANTS[data.plant]?.name || 'Растение';
    showNotification(`⚠️ ${plantName} ${bloomBlock}!`, true);
    saveState();
}

function clearBloomBlockNotified(data) {
    if (data?.bloomBlockNotified) {
        delete data.bloomBlockNotified;
    }
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
    if (!data?.plant || data.stage < 1 || isPlantDead(data)) return;
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
    if (!msg || isPlantDead(data) || data.hasDisease || data.stage < 1) return false;

    data.hasDisease = true;
    data.hadMistakes = true;
    data.disease = msg;
    data.diseaseType = diseaseType;
    data.diseaseSource = source;
    data.diseaseStartTime = Date.now();
    recordPlantMistakeCategory(data, source);
    showDiseaseAdvice(diseaseType);
    saveState();
    checkAchievement_negativeEffect();
    refreshPlantVisual(slotName);
    scheduleSicknessDeathCheck(slotName);
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

function getPlantVisualMeta(plant, data) {
    if (!plant || !data?.plant) return null;

    const stage = resolvePlantStage(data);
    if (stage < 1) return null;

    const plantId = resolveSpeciesId(data.plant, plant);
    ensurePlantDiseaseAssets(plant, plantId);
    const pot = Number(data.pot) || 1;

    if (data.disease === '__dead__') {
        const visualStateKey = 'dead';
        return {
            imageUrl: plant.deadImage || getHealthyStageImage(plant, 1),
            stage,
            plantId,
            pot,
            layout: 'dead',
            disease: '__dead__',
            diseaseType: 'dead',
            imageKey: null,
            visualStateKey,
            visualEntry: getVisualStateEntry(plantId, visualStateKey)
        };
    }

    if (data.hasDisease && data.disease) {
        const diseaseImg = getDiseaseImage(plant, data.disease, plantId, data.diseaseType)
            || getFirstDiseaseImage(plant);
        if (diseaseImg) {
            const diseaseType = data.diseaseType || null;
            const visualStateKey = resolveVisualStateKey(plantId, stage, data.disease, diseaseType);
            return {
                imageUrl: diseaseImg,
                stage,
                plantId,
                pot,
                layout: 'disease',
                disease: data.disease,
                diseaseType,
                imageKey: getDiseaseImageKey(plant, data.disease, plantId, diseaseType),
                visualStateKey,
                visualEntry: getVisualStateEntry(plantId, visualStateKey)
            };
        }
    }

    const visualStateKey = stage >= 2 ? 'bloom' : 'sprout';
    return {
        imageUrl: getHealthyStageImage(plant, stage),
        stage,
        plantId,
        pot,
        layout: visualStateKey,
        disease: null,
        diseaseType: null,
        imageKey: null,
        visualStateKey,
        visualEntry: getVisualStateEntry(plantId, visualStateKey)
    };
}

function getPlantDisplayImage(plant, data) {
    return getPlantVisualMeta(plant, data)?.imageUrl || null;
}

function getOffsetsForVisual(meta) {
    const entry = meta.visualEntry || getVisualStateEntry(meta.plantId, meta.visualStateKey);
    if (!entry) return getPlantOffsets(meta.plantId, meta.stage, meta.disease, meta.diseaseType);
    return { bottom: entry.bottom, width: entry.width, left: entry.left || '50%' };
}

function getPotLiftForVisual(type, meta) {
    const entry = meta.visualEntry || getVisualStateEntry(meta.plantId, meta.visualStateKey);
    const pot = meta.pot || 1;
    const lifts = entry?.pots?.[pot] || entry?.pots?.[1];
    if (!lifts) {
        const hasDisease = meta.layout === 'disease' || meta.layout === 'dead';
        const disease = meta.layout === 'dead' ? '__dead__' : meta.disease;
        return getPotLift(type, meta.plantId, meta.pot, meta.stage, hasDisease, disease, meta.diseaseType);
    }
    return type === 'zoom' ? (lifts.zoomLift ?? 0) : (lifts.slotLift ?? 0);
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
        setZoomControlsForPlantState(data);

        const zoomStageLabel = document.getElementById('zoomStageLabel');
        if (zoomStageLabel && data.plant) {
            if (isPlantDead(data)) {
                zoomStageLabel.textContent = PLANT_DEAD_LABEL;
            } else {
                const stage = resolvePlantStage(data);
                if (stage === 0) {
                    zoomStageLabel.textContent = STAGE_NAMES[0];
                } else if (data.hasDisease) {
                    zoomStageLabel.textContent = PLANT_SICK_LABEL;
                } else if (stage === 1) {
                    zoomStageLabel.textContent = STAGE_NAMES[1];
                } else if (stage >= 2) {
                    zoomStageLabel.textContent = STAGE_NAMES[2];
                }
            }
        }
    }
}

function tryHealUnderwaterOnWater(data) {
    if (!data?.hasDisease || isPlantDead(data)) return false;
    const plantKey = resolveSpeciesId(data.plant, PLANTS[data.plant]);
    const underMsg = PLANT_DISEASES[plantKey]?.under_watered;
    if (!underMsg || data.disease !== underMsg) return false;
    data.hasDisease = false;
    data.disease = null;
    data.diseaseType = null;
    data.diseaseSource = null;
    data.diseaseStartTime = null;
    markHealedPlant();
    return true;
}

function getOverwaterHealDryMs(plant) {
    return getWaterMinMs(plant);
}

function isOverwaterDisease(data, plantKey) {
    if (!data?.hasDisease) return false;
    if (data.diseaseType === 'overwatered') return true;
    const overMsg = PLANT_DISEASES[plantKey]?.overwatered;
    return overMsg && data.disease === overMsg;
}

function tryHealOverwaterOnDry(slotName, data, plant) {
    if (!data?.hasDisease || isPlantDead(data)) return false;
    const plantKey = resolveSpeciesId(data.plant, plant);
    if (!isOverwaterDisease(data, plantKey)) return false;
    if (!data.lastWateredAt) return false;
    if (msSinceLastWater(data) < getOverwaterHealDryMs(plant)) return false;

    data.hasDisease = false;
    data.disease = null;
    data.diseaseType = null;
    data.diseaseSource = null;
    data.diseaseStartTime = null;
    data.wateringHistory = [];
    markHealedPlant();
    refreshPlantVisual(slotName);
    return true;
}

function checkWateringHealth(slotName, data) {
    if (!data || !data.plant) return;
    if (data.devManualState || isPlantDead(data)) return;
    const plant = PLANTS[data.plant];
    if (!plant || data.stage < 1) return;

    const plantKey = resolveSpeciesId(data.plant, plant);
    tryHealOverwaterOnDry(slotName, data, plant);

    const now = Date.now();
    const maxMs = getWaterMaxMs(plant);
    const sinceWaterMs = msSinceLastWater(data);

    const needsWater = !data.lastWateredAt
        ? (now - (data.plantedAt || now)) > maxMs
        : sinceWaterMs > maxMs;

    if (hasOverwaterRisk(data, plant) && PLANT_DISEASES[plantKey]?.overwatered) {
        recordPlantMistakeCategory(data, 'water');
        applyPlantDisease(slotName, data, 'overwatered', 'water');
    } else if (needsWater && PLANT_DISEASES[plantKey]?.under_watered) {
        recordPlantMistakeCategory(data, 'water');
        if (!data.hasDisease) {
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
    if (data.devManualState || isPlantDead(data)) return;

    const plantKey = resolveSpeciesId(data.plant, PLANTS[data.plant]);
    let diseaseMsg = getLocationDiseaseForSlot(plantKey, slotName, data);

    if (diseaseMsg) {
        const mistakeSource = (plantKey === 1 && data.pot === 3 && diseaseMsg === PLANT_DISEASES[1].big_pot)
            ? 'pot' : 'location';
        recordPlantMistakeCategory(data, mistakeSource);

        if (!data.hasDisease) {
            data.hasDisease = true;
            data.hadMistakes = true;
            data.disease = diseaseMsg;
            data.diseaseType = getDiseaseTypeFromMessage(plantKey, diseaseMsg);
            data.diseaseSource = mistakeSource;
            saveState();
            if (data.diseaseType) showDiseaseAdvice(data.diseaseType);
            checkAchievement_negativeEffect();
            refreshPlantVisual(slotName);
            scheduleSicknessDeathCheck(slotName);
        } else {
            saveState();
        }
    } else if (!diseaseMsg && data.hasDisease && isLocationBasedDisease(plantKey, data.disease) && data.stage >= 1) {
        data.hasDisease = false;
        data.disease = null;
        data.diseaseType = null;
        data.diseaseSource = null;
        saveState();
        markHealedPlant({ skipRecoveryTip: true });
        showPositiveTip('goodLocation');
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

function markHealedPlant({ skipRecoveryTip = false } = {}) {
    if (!skipRecoveryTip) showPositiveTip('recovered');
    if (!localStorage.getItem(`healedPlant_${currentUser}`)) {
        localStorage.setItem(`healedPlant_${currentUser}`, 'true');
        checkQuestsAfterAction();
        showNotification('💚 Задание выполнено: растение выздоровело!', false);
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
            const notifyKey = `potUnlockNotified_${currentUser}_${num}`;
            if (!localStorage.getItem(notifyKey)) {
                localStorage.setItem(notifyKey, '1');
                showNotification(`🎉 Новый горшок разблокирован: ${cfg.name}!`, false);
            }
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
        if (unlockLevel <= userLevel && !isWateringCanUnlocked(cfg)) {
            WATERING_CAN_CONFIG[id].isUnlocked = true;
            unlockedAny = true;
            const notifyKey = `wateringCanUnlockNotified_${currentUser}_${id}`;
            if (!localStorage.getItem(notifyKey)) {
                localStorage.setItem(notifyKey, '1');
                showNotification(`🎉 Новая лейка разблокирована: ${cfg.name}!`, false);
            }
        }
    });

    if (unlockedAny) {
        renderWateringCanChoices();
    }
}
function buildChoiceCardInnerHTML({ imgSrc, imgAlt, title, extraHtml = '', imgClass = '', imgStyle = '' }) {
    const classAttr = imgClass ? ` class="${imgClass}"` : '';
    const styleAttr = imgStyle ? ` style="${imgStyle}"` : '';
    return `
        <div class="choice-card-media">
            <img src="${imgSrc}" alt="${imgAlt}"${classAttr}${styleAttr}>
        </div>
        <div class="choice-card-caption">
            <span class="choice-card-title">${title}</span>
            ${extraHtml}
        </div>`;
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
        div.innerHTML = buildChoiceCardInnerHTML({
            imgSrc: cfg.img,
            imgAlt: cfg.name,
            title: cfg.name,
            extraHtml: locked ? `<span class="unlock-hint">🔒 ур.${cfg.unlockLevel}</span>` : '',
            imgStyle: locked ? 'filter:grayscale(1) opacity(0.5)' : ''
        });
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
        const previewImage = plant.stages?.[2] || plant.stages?.[1] || 'images/plant/default/stage/выросший.png';

        const div = document.createElement('div');
        div.className = 'flower-choice' + (locked ? ' locked-choice' : '');
        div.dataset.plant = key;
        div.innerHTML = buildChoiceCardInnerHTML({
            imgSrc: previewImage,
            imgAlt: plant.name,
            title: plant.name,
            extraHtml: locked ? `<span class="unlock-hint">🔒 ур.${plant.unlockLevel}</span>` : '',
            imgStyle: locked ? 'filter:grayscale(1) opacity(0.5)' : ''
        });

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
                slotData[name].diseaseType = null;
                slotData[name].diseaseSource = null;
                slotData[name].mistakeCategories = createEmptyMistakeCategories();
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
        const locked = !isWateringCanUnlocked(cfg);
        const isCurrent = parseInt(id, 10) === currentCanId;
        const div = document.createElement('div');
        div.className = 'watercan-choice' + (locked ? ' locked-choice' : '') + (isCurrent ? ' current-can' : '');
        div.dataset.can = id;
        div.innerHTML = buildChoiceCardInnerHTML({
            imgSrc: cfg.img,
            imgAlt: cfg.name,
            title: cfg.name,
            extraHtml: locked ? `<span class="unlock-hint">🔒 ур.${cfg.unlockLevel}</span>` : '',
            imgStyle: locked ? 'filter:grayscale(1) opacity(0.5)' : ''
        });

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
    if (!isWateringCanUnlocked(canConfig)) {
        showNotification('Лейка ещё не открыта', true);
        return;
    }

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
            applyWateringCanChange(canId, canConfig);
            return;
        }

        console.warn('Смена лейки на сервере:', data.error);
        applyWateringCanChange(canId, canConfig);
    } catch (error) {
        console.error('Ошибка смены лейки:', error);
        applyWateringCanChange(canId, canConfig);
    }
}

function syncWateringCanLayout(canId) {
    const anim = document.getElementById('wateringAnim');
    if (anim) anim.dataset.can = String(canId);
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
    syncWateringCanLayout(canId);
}

const MOVE_MODAL_VISUAL = {
    1: {
        sprout: {
            1: { bottom: '8px', width: '55px', lift: -43 },
            2: { bottom: '10px', width: '50px', lift: -46 },
            3: { bottom: '12px', width: '65px', lift: -38 }
        },
        bloom: {
            1: { bottom: '10px', width: '90px', lift: -63 },
            2: { bottom: '5px', width: '85px', lift: -58 },
            3: { bottom: '10px', width: '100px', lift: -55 }
        },
        dead: {
            1: { bottom: '15px', width: '70px', lift: -98 },
            2: { bottom: '13px', width: '65px', lift: -95 },
            3: { bottom: '17px', width: '80px', lift: -95 }
        },
        diseases: {
            too_light: {
                1: { bottom: '14px', width: '70px', lift: -39 },
                2: { bottom: '12px', width: '65px', lift: -40 },
                3: { bottom: '16px', width: '80px', lift: -30 }
            },
            big_pot: {
                1: { bottom: '18px', width: '60px', lift: -35 },
                2: { bottom: '15px', width: '55px', lift: -35 },
                3: { bottom: '20px', width: '60px', lift: -25 }
            },
            under_watered: {
                1: { bottom: '15px', width: '70px', lift: -37 },
                2: { bottom: '13px', width: '65px', lift: -37 },
                3: { bottom: '18px', width: '80px', lift: -27 }
            },
            overwatered: {
                1: { bottom: '14px', width: '70px', lift: -38 },
                2: { bottom: '12px', width: '65px', lift: -40 },
                3: { bottom: '12px', width: '80px', lift: -26 }
            }
        }
    },
    2: {
        sprout: {
            1: { bottom: '35px', width: '50px', lift: -78 },
            2: { bottom: '30px', width: '45px', lift: -75 },
            3: { bottom: '40px', width: '55px', lift: -73 }
        },
        bloom: {
            1: { bottom: '15px', width: '45px', lift: -80 },
            2: { bottom: '15px', width: '45px', lift: -83 },
            3: { bottom: '25px', width: '55px', lift: -88 }
        },
        dead: {
            1: { bottom: '16px', width: '45px', lift: -85 },
            2: { bottom: '16px', width: '40px', lift: -83 },
            3: { bottom: '17px', width: '50px', lift: -79 }
        },
        diseases: {
            too_dark: {
                1: { bottom: '20px', width: '25px', lift: -37 },
                2: { bottom: '17px', width: '20px', lift: -39 },
                3: { bottom: '27px', width: '30px', lift: -32 }
            },
            no_flower: {
                1: { bottom: '17px', width: '28px', lift: -36 },
                2: { bottom: '12px', width: '25px', lift: -34 },
                3: { bottom: '15px', width: '30px', lift: -21 }
            },
            under_watered: {
                1: { bottom: '12px', width: '23px', lift: -33 },
                2: { bottom: '7px', width: '25px', lift: -32 },
                3: { bottom: '17px', width: '22px', lift: -26 }
            },
            overwatered: {
                1: { bottom: '12px', width: '23px', lift: -33 },
                2: { bottom: '7px', width: '25px', lift: -32 },
                3: { bottom: '17px', width: '22px', lift: -26 }
            }
        }
    },
    3: {
        sprout: {
            1: { bottom: '30px', width: '65px', lift: -115 },
            2: { bottom: '25px', width: '60px', lift: -108 },
            3: { bottom: '35px', width: '70px', lift: -110 }
        },
        bloom: {
            1: { bottom: '25px', width: '110px', lift: -105 },
            2: { bottom: '20px', width: '105px', lift: -100 },
            3: { bottom: '30px', width: '115px', lift: -100 }
        },
        dead: {
            1: { bottom: '15px', width: '85px', lift: -118 },
            2: { bottom: '10px', width: '80px', lift: -110 },
            3: { bottom: '20px', width: '90px', lift: -112 }
        },
        diseases: {
            too_light: {
                1: { bottom: '32px', width: '70px', lift: -60 },
                2: { bottom: '27px', width: '65px', lift: -59 },
                3: { bottom: '37px', width: '75px', lift: -55 }
            },
            under_watered: {
                1: { bottom: '34px', width: '65px', lift: -55 },
                2: { bottom: '29px', width: '60px', lift: -54 },
                3: { bottom: '39px', width: '70px', lift: -49 }
            },
            overwatered: {
                1: { bottom: '35px', width: '50px', lift: -55 },
                2: { bottom: '30px', width: '45px', lift: -53 },
                3: { bottom: '40px', width: '55px', lift: -48 }
            }
        }
    },
    global: {
        enabled: true,
        baseLiftPx: 50,
        plantScale: 1.50,
        containerMinHeight: 150,
        defaultFallback: { bottom: '35px', width: '75px', lift: 0 }
    }
};

let moveFromSlot = null;

function getMoveModalVisual(plantId, visualState, potNum, diseaseType = null) {
    const plantConfig = MOVE_MODAL_VISUAL[plantId];
    if (!plantConfig || !MOVE_MODAL_VISUAL.global.enabled) return null;

    let stateConfig = null;
    let stateKey = visualState;
    if (visualState === 'disease' && diseaseType) {
        stateKey = diseaseType;
    }

    if (stateKey === 'sprout' || stateKey === 'bloom' || stateKey === 'dead') {
        stateConfig = plantConfig[stateKey];
    } else if (plantConfig.diseases && plantConfig.diseases[stateKey]) {
        stateConfig = plantConfig.diseases[stateKey];
    }

    if (!stateConfig) return null;

    const potConfig = stateConfig[potNum];
    if (potConfig) return potConfig;
    if (stateConfig[1]) return stateConfig[1];
    return MOVE_MODAL_VISUAL.global.defaultFallback;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function renderMoveChoices() {
    const row = document.getElementById('moveChoicesRow');
    if (!row) return;
    row.innerHTML = '';

    if (!moveFromSlot) {
        closeModal(modalMovePlant);
        return;
    }

    const currentSlotData = slotData[moveFromSlot];
    if (!currentSlotData || !currentSlotData.pot) {
        showNotification('Ошибка: данные горшка не найдены', true);
        closeModal(modalMovePlant);
        moveFromSlot = null;
        return;
    }

    const allSlots = document.querySelectorAll('.pot-slot');
    const slotNamesMap = {
        'windowsill-1': 'Подоконник левый',
        'windowsill-2': 'Подоконник центр',
        'windowsill-3': 'Подоконник правый',
        'desk-left': 'Стол левый',
        'desk-right-1': 'Стол правый 1',
        'desk-right-2': 'Стол правый 2'
    };

    allSlots.forEach(slotEl => {
        const slotName = slotEl.dataset.slot;
        const targetData = slotData[slotName];
        const isCurrent = slotName === moveFromSlot;
        if (isCurrent) return;

        const isEmpty = !targetData || !targetData.pot;
        const hasPlant = targetData && targetData.plant && targetData.stage >= 1 && PLANTS[targetData.plant];

        const div = document.createElement('div');
        div.className = 'pot-choice';
        if (isEmpty) div.classList.add('empty-slot');
        else if (hasPlant) div.classList.add('occupied-slot');
        div.dataset.slot = slotName;

        let slotDisplayName = slotNamesMap[slotName] || slotName.replace(/-/g, ' ');
        let potImg = '/images/room/пунктир.png';
        let statusHtml = '';

        if (targetData && targetData.pot && POT_CONFIG[targetData.pot]) {
            potImg = POT_CONFIG[targetData.pot].img;
        }

        if (isEmpty) {
            statusHtml = '<span class="free-label">🆓 Свободно</span>';
        } else if (hasPlant) {
            const plant = PLANTS[targetData.plant];
            const plantName = plant.name;
            const stageText = targetData.stage >= 2 ? '🌸' : '🌱';
            const diseaseText = targetData.hasDisease ? ' 🤒' : '';
            statusHtml = `<span class="occupied-label">${stageText} ${plantName}${diseaseText}</span>`;
        } else if (targetData.pot) {
            statusHtml = `<span class="occupied-label">🪴 Пустой горшок</span>`;
        }

        let mediaHtml = '';

        if (hasPlant) {
            const plant = PLANTS[targetData.plant];
            const plantId = resolveSpeciesId(targetData.plant, plant);
            const potNum = targetData.pot || 1;
            const stage = targetData.stage >= 2 ? 'bloom' : 'sprout';

            let visualState = stage;
            let diseaseType = null;

            if (isPlantDead(targetData)) {
                visualState = 'dead';
            } else if (targetData.hasDisease && targetData.diseaseType) {
                visualState = 'disease';
                diseaseType = targetData.diseaseType;
            }

            const customVisual = getMoveModalVisual(plantId, visualState, potNum, diseaseType);

            if (customVisual) {
                const finalBottom = `calc(${customVisual.bottom} + ${MOVE_MODAL_VISUAL.global.baseLiftPx + (customVisual.lift || 0)}px)`;
                const plantImage = getPlantDisplayImage(plant, targetData);

                mediaHtml = `
                    <div class="choice-card-media" style="position: relative; display: flex; align-items: flex-end; justify-content: center; min-height: ${MOVE_MODAL_VISUAL.global.containerMinHeight}px;">
                        <img src="${potImg}" alt="горшок" style="position: relative; z-index: 1; width: 70%; margin-bottom: -10px;">
                        <img src="${plantImage}" alt="растение" style="position: absolute; bottom: ${finalBottom}; left: 50%; transform: translateX(-50%) scale(${MOVE_MODAL_VISUAL.global.plantScale}); transform-origin: bottom center; width: ${customVisual.width}; z-index: 2;">
                    </div>
                `;
            } else {
                const meta = getPlantVisualMeta(plant, targetData);
                if (meta?.imageUrl) {
                    const offsets = getOffsetsForVisual(meta);
                    const extraLiftPx = getPotLiftForVisual('slot', meta);
                    const bottomValue = offsets
                        ? `calc(${offsets.bottom} + ${MOVE_MODAL_VISUAL.global.baseLiftPx + extraLiftPx}px)`
                        : `calc(40% + ${MOVE_MODAL_VISUAL.global.baseLiftPx}px)`;
                    const widthValue = offsets ? offsets.width : '55%';

                    mediaHtml = `
                        <div class="choice-card-media" style="position: relative; display: flex; align-items: flex-end; justify-content: center; min-height: ${MOVE_MODAL_VISUAL.global.containerMinHeight}px;">
                            <img src="${potImg}" alt="горшок" style="position: relative; z-index: 1; width: 70%; margin-bottom: -10px;">
                            <img src="${meta.imageUrl}" alt="растение" style="position: absolute; bottom: ${bottomValue}; left: 50%; transform: translateX(-50%) scale(${MOVE_MODAL_VISUAL.global.plantScale}); transform-origin: bottom center; width: ${widthValue}; z-index: 2;">
                        </div>
                    `;
                } else {
                    mediaHtml = `
                        <div class="choice-card-media" style="min-height: ${MOVE_MODAL_VISUAL.global.containerMinHeight}px; display: flex; align-items: flex-end; justify-content: center;">
                            <img src="${potImg}" alt="горшок" style="width: 70%;">
                        </div>
                    `;
                }
            }
        } else {
            mediaHtml = `
                <div class="choice-card-media" style="min-height: ${MOVE_MODAL_VISUAL.global.containerMinHeight}px; display: flex; align-items: flex-end; justify-content: center;">
                    <img src="${potImg}" alt="место" ${isEmpty ? 'class="choice-card-img--empty"' : ''} style="width: 70%;">
                </div>
            `;
        }

        div.innerHTML = `
            ${mediaHtml}
            <div class="choice-card-caption">
                <span class="choice-card-title">${escapeHtml(slotDisplayName)}</span>
                ${statusHtml}
            </div>
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
    if (isPlantDead(slotData[fromSlot])) return;

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

    movedData.devManualState = false;
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
    if (isPlantDead(slotData[slotA]) || isPlantDead(slotData[slotB])) return;

    const dataA = { ...slotData[slotA] };
    const dataB = { ...slotData[slotB] };

    if (dataA) dataA.devManualState = false;
    if (dataB) dataB.devManualState = false;
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

    if (data.plant && !isPlantDead(data) && data.stage < 2) {
        showPlantDeathNotification(data);
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
    data.diseaseType = null;
    data.diseaseSource = null;
    data.diseaseStartTime = null;
    data.mistakeCategories = createEmptyMistakeCategories();
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
    if (data.plant && !isPlantDead(data) && data.stage < 2) {
        showPlantDeathNotification(data);
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
        potImg.alt = potConfig.name || `Горшок ${data.pot}`;
        slotEl.prepend(potImg);
    }

    if (data.plant && data.stage >= 1 && PLANTS[data.plant]) {
        const plantImg = document.createElement('img');
        const plant = PLANTS[data.plant];
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
        }
    }

    const hint = slotEl.querySelector('.slot-hint');
    if (hint) {
        if (!data.plant) {
            hint.innerHTML = 'Посадить<br>цветок';
        } else if (data.stage === 0) {
            hint.textContent = 'Прорастает...';
        } else if (isPlantDead(data)) {
            hint.textContent = PLANT_DEAD_LABEL;
        } else if (data.hasDisease) {
            hint.textContent = PLANT_SICK_LABEL;
        } else if (data.stage === 1) {
            hint.textContent = 'Росток';
        } else if (data.stage >= 2) {
            hint.textContent = 'Цветёт!';
        }
    }
}

function updateGrowthTimer(data) {
    if (!data || !data.plant || !data.plantedAt || isPlantDead(data) || data.stage >= 2) {
        const timerBox = document.getElementById('growthTimerBox');
        if (timerBox) timerBox.style.display = 'none';
        return;
    }

    if (data.hasDisease && data.stage === 1) {
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
    if (!data || !data.plant || isPlantDead(data)) {
        const timerBox = document.getElementById('waterTimerBox');
        if (timerBox) timerBox.style.display = 'none';
        return;
    }

    const plant = PLANTS[data.plant];
    if (!plant) return;

    const minMs = getWaterMinMs(plant);
    const maxMs = getWaterMaxMs(plant);
    const sinceMs = msSinceLastWater(data);
    let timerText = '';

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

    if (isPlantDead(data)) {
        diseaseText.textContent = 'Растение погибло. Выбросите горшок, чтобы посадить новое.';
        diseaseBox.style.display = 'block';
    } else if (data.hasDisease && data.disease && data.stage >= 1) {
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

    if (isPlantDead(data)) {
        fixBox.style.display = 'none';
    } else if (data.hasDisease && data.disease && data.stage >= 1) {
        let advice = '';
        const norm = normalizePlantText(data.disease);
        if (norm.includes('ожог') || norm.includes('пятна') || norm.includes('свет')) {
            advice = '💡 Решение: Убери с подоконника — слишком яркий свет. Переставь горшок через «Переставить горшок».';
        } else if (norm.includes('недостаток полива') || norm.includes('сохнут кончики')) {
            advice = '💧 Решение: Полей растение. Следи, чтобы полив был регулярным.';
        } else if (norm.includes('перелив') || norm.includes('увядание')) {
            const plant = PLANTS[data.plant];
            const dryMs = plant ? getOverwaterHealDryMs(plant) : 0;
            const dryHint = WATER_TIMING_TEST
                ? `${Math.ceil(dryMs / 1000)} сек.`
                : `${Math.round(dryMs / 3600000)} ч.`;
            advice = `💧 Решение: Не поливай ${dryHint} — дай почве просохнуть. После этого растение выздоровеет.`;
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
    const sel = devStateSelect;
    if (!sel) return;

    const currentVal = sel.value;
    const plantKey = resolveSpeciesId(plant?.id, plant);

    Array.from(sel.options).filter(o => !['sprout', 'healthy', 'dead'].includes(o.value))
        .forEach(o => sel.removeChild(o));

    const deadOption = Array.from(sel.options).find(o => o.value === 'dead');
    const diseases = PLANT_DISEASES[plantKey];
    const typeMap = PLANT_DISEASE_TO_IMAGE_KEY[plantKey];

    if (diseases && typeMap) {
        for (const [type, imageKey] of Object.entries(typeMap)) {
            const msg = diseases[type];
            if (!msg) continue;
            const opt = document.createElement('option');
            opt.value = `disease:${type}`;
            opt.textContent = `🤒 ${msg.replace(/^[^\s]+\s/, '').slice(0, 42)}`;
            if (deadOption) sel.insertBefore(opt, deadOption);
            else sel.appendChild(opt);
        }
    }

    if (Array.from(sel.options).some(o => o.value === currentVal)) sel.value = currentVal;
    else sel.value = 'healthy';
}

function applyDevPlantState(slotName, state) {
    const data = slotData[slotName];
    if (!data?.plant) return false;

    const plant = PLANTS[data.plant];
    const plantKey = resolveSpeciesId(data.plant, plant);

    data.hasDisease = false;
    data.disease = null;
    data.diseaseType = null;
    data.diseaseSource = null;
    data.diseaseStartTime = null;
    data.devManualState = true;

    if (state === 'sprout') {
        data.stage = 1;
    } else if (state === 'healthy') {
        data.stage = 2;
        data.devManualState = false;
    } else if (state === 'dead') {
        data.stage = 2;
        data.hasDisease = true;
        data.disease = '__dead__';
        data.diseaseType = 'dead';
        data.diseaseSource = 'dev';
    } else if (state.startsWith('disease:')) {
        const diseaseType = state.slice('disease:'.length);
        const msg = PLANT_DISEASES[plantKey]?.[diseaseType];
        if (!msg) return false;
        data.stage = Math.max(data.stage, 1);
        data.hasDisease = true;
        data.disease = msg;
        data.diseaseType = diseaseType;
        data.diseaseSource = diseaseType === 'big_pot' ? 'pot' : (
            WATER_DISEASE_TYPES.includes(diseaseType) ? 'water' : 'location'
        );
        data.diseaseStartTime = Date.now();
        recordPlantMistakeCategory(data, data.diseaseSource);
        scheduleSicknessDeathCheck(slotName);
    } else {
        return false;
    }

    saveState();
    const slotEl = document.querySelector(`[data-slot="${slotName}"]`) || zoomedSlot?.slotEl;
    if (slotEl) renderSlot(slotEl, data);
    if (zoomedSlot?.name === slotName) {
        openZoom(slotEl, slotName, data);
    }
    return true;
}

function openZoom(slotEl, name, data) {
    zoomedSlot = { slotEl, name };
    currentZoomedPlantId = name;
    if (devStatePanel) devStatePanel.style.display = 'block';
    resetZoomButtonDisabledState();

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
        populateDevPanel(plant);

        if (plantImg) {
            updateZoomPlantVisual(data);
        }

        const zoomPlantName = document.getElementById('zoomPlantName');
        if (zoomPlantName) zoomPlantName.textContent = `${plant.name} — ${plant.nickname}`;

        const zoomStageLabel = document.getElementById('zoomStageLabel');
        if (zoomStageLabel) {
            if (isPlantDead(data)) {
                zoomStageLabel.textContent = PLANT_DEAD_LABEL;
            } else if (data.stage === 0) {
                zoomStageLabel.textContent = 'Семечко посажено';
            } else if (data.hasDisease) {
                zoomStageLabel.textContent = PLANT_SICK_LABEL;
            } else if (data.stage === 1) {
                zoomStageLabel.textContent = 'Росток';
            } else if (data.stage >= 2) {
                zoomStageLabel.textContent = 'Расцвёл';
            } else {
                zoomStageLabel.textContent = STAGE_NAMES[data.stage] || STAGE_NAMES[0];
            }
        }

        if (waterBtn) waterBtn.style.display = 'block';
        if (descBtn) descBtn.style.display = 'block';
        if (repotBtn) repotBtn.style.display = 'block';
        if (moveBtn) moveBtn.style.display = 'block';
        if (removeBtn) removeBtn.style.display = 'block';
        if (plantBtn) plantBtn.style.display = 'none';
        if (descriptionBox) descriptionBox.style.display = 'none';

        setZoomControlsForPlantState(data);
        updateDiseaseInfo(data);
        showFixAdvice(data);
        updateGrowthTimer(data);
        updateNextWateringTimer(data);
        if (!isPlantDead(data)) {
            startZoomTimerTick();
        } else {
            stopZoomTimerTick();
        }
    } else {
        if (plantImg) plantImg.style.display = 'none';

        const zoomPlantName = document.getElementById('zoomPlantName');
        if (zoomPlantName) zoomPlantName.textContent = 'Пустой горшок';

        const zoomStageLabel = document.getElementById('zoomStageLabel');
        if (zoomStageLabel) zoomStageLabel.textContent = 'Посади цветок!';

        if (waterBtn) {
            waterBtn.disabled = true;
            waterBtn.style.display = 'none';
        }
        if (descBtn) descBtn.style.display = 'none';
        if (repotBtn) repotBtn.style.display = 'none';
        if (moveBtn) moveBtn.style.display = 'none';
        if (removeBtn) {
            removeBtn.style.display = 'block';
            removeBtn.disabled = false;
        }
        if (plantBtn) {
            plantBtn.style.display = 'block';
            plantBtn.disabled = false;
        }
        if (descriptionBox) descriptionBox.style.display = 'none';

        const growthTimerBox = document.getElementById('growthTimerBox');
        if (growthTimerBox) growthTimerBox.style.display = 'none';

        const waterTimerBox = document.getElementById('waterTimerBox');
        if (waterTimerBox) waterTimerBox.style.display = 'none';

        const diseaseBox = document.getElementById('diseaseBox');
        if (diseaseBox) diseaseBox.style.display = 'none';

        const fixBox = document.getElementById('fixAdviceBox');
        if (fixBox) fixBox.style.display = 'none';

        stopZoomTimerTick();
    }

    const wateringAnim = document.getElementById('wateringAnim');
    if (wateringAnim) wateringAnim.classList.remove('active');

    openModal(zoomOverlay);
}

const zoomClose = document.getElementById('zoomClose');
if (zoomClose) zoomClose.addEventListener('click', () => { closeModal(zoomOverlay); if (devStatePanel) devStatePanel.style.display = 'none'; });

if (zoomOverlay) zoomOverlay.addEventListener('click', e => { if (e.target === zoomOverlay) { closeModal(zoomOverlay); if (devStatePanel) devStatePanel.style.display = 'none'; } });

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
        div.innerHTML = buildChoiceCardInnerHTML({
            imgSrc: cfg.img,
            imgAlt: cfg.name,
            title: cfg.name,
            extraHtml: locked ? `<span class="unlock-hint">🔒 ур.${cfg.unlockLevel}</span>` : '',
            imgStyle: locked ? 'filter:grayscale(1) opacity(0.5)' : ''
        });
        if (!locked && !isCurrent) {
            div.addEventListener('click', () => {
                if (!zoomedSlot) return;
                const name = zoomedSlot.name;
                const data = slotData[name];
                if (!data || isPlantDead(data)) return;
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

const plantBtnLeft = document.getElementById('plantBtnLeft');
if (plantBtnLeft) {
    plantBtnLeft.addEventListener('click', () => {
        if (!zoomedSlot) return;
        const data = slotData[zoomedSlot.name];
        if (data?.plant && isPlantDead(data)) return;
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
        if (isPlantDead(slotData[zoomedSlot.name])) return;
        closeModal(zoomOverlay);
        renderRepotChoices();
        setTimeout(() => openModal(modalRepot), 100);
    });
}

const moveBtnLeft = document.getElementById('moveBtnLeft');
if (moveBtnLeft) {
    moveBtnLeft.addEventListener('click', () => {
        if (!zoomedSlot) return;
        if (isPlantDead(slotData[zoomedSlot.name])) return;

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
        if (!data?.plant || !PLANTS[data.plant] || isPlantDead(data)) return;

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
            data.devManualState = false;
            recordWateringGap(data, now);
            data.lastWateredAt = now;
            data.totalWaterings = (data.totalWaterings || 0) + 1;

            const globalTotal = getTotalWaterings() + 1;
            localStorage.setItem(`totalWaterings_${currentUser}`, String(globalTotal));

            tryHealUnderwaterOnWater(data);
            checkWateringHealth(name, data);
            applyGrowthFromTime(name);

            if (!data.hasDisease) showPositiveTip('idealWater');

            renderSlot(slotEl, data);
            updateNextWateringTimer(data);
            updateGrowthTimer(data);

            updateZoomPlantVisual(data);

            const zoomStageLabel = document.getElementById('zoomStageLabel');
            if (zoomStageLabel) {
                const stage = resolvePlantStage(data);
                if (stage === 0) {
                    zoomStageLabel.textContent = STAGE_NAMES[0];
                } else if (stage === 1) {
                    zoomStageLabel.textContent = data.hasDisease ? PLANT_SICK_LABEL : STAGE_NAMES[1];
                } else if (stage >= 2) {
                    zoomStageLabel.textContent = data.hasDisease ? PLANT_SICK_LABEL : STAGE_NAMES[2];
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
    for (let i = 0; i < 10; i++) {
        const drop = document.createElement('div');
        drop.className = 'drop';
        drop.style.left = `${28 + Math.random() * 44}%`;
        drop.style.animationDelay = `${(Math.random() * 0.45).toFixed(2)}s`;
        drop.style.animationDuration = `${(0.45 + Math.random() * 0.35).toFixed(2)}s`;
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
            }).finally(() => { window.location.href = 'register.html'; });
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

function loadState() {
    try {
        const raw = localStorage.getItem(`garden_${currentUser}`);
        if (raw) {
            const parsed = JSON.parse(raw);
            if (parsed?.slotData && typeof parsed.slotData === 'object') {
                Object.assign(slotData, parsed.slotData);
                if (parsed.currentWateringCan != null) {
                    pendingWateringCanFromGame = normalizeWateringCanId(parsed.currentWateringCan);
                }
            } else if (parsed && typeof parsed === 'object') {
                Object.assign(slotData, parsed);
            }
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
                        if (slotData[name].hasDisease || isPlantDead(slotData[name])) {
                            scheduleSicknessDeathCheck(name);
                        }
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
    if (!data || !data.plant || !data.plantedAt || isPlantDead(data)) return;

    const msSincePlanted = Date.now() - data.plantedAt;

    if (msSincePlanted >= BLOOM_MS && data.stage < 2) {
        syncSlotHealthChecks(slotName);
        const dataAfter = slotData[slotName];
        const plant = PLANTS[dataAfter.plant];
        const bloomBlock = getBloomBlockReason(dataAfter, plant);
        if (!bloomBlock && dataAfter.stage >= 1) {
            clearBloomBlockNotified(dataAfter);
            const oldStage = dataAfter.stage;
            dataAfter.stage = 2;
            dataAfter.bloomedAt = dataAfter.bloomedAt || (dataAfter.plantedAt + BLOOM_MS);
            const slotEl = document.querySelector(`[data-slot="${slotName}"]`);
            if (slotEl) renderSlot(slotEl, dataAfter);

            if (oldStage !== 2) {
                showPositiveTip('bloomed');
                checkAllAchievementsOnBloom(slotName, dataAfter);
            }
            saveState();
            checkQuestsAfterAction();
        } else if (bloomBlock) {
            notifyBloomBlockedOnce(dataAfter, bloomBlock);
        } else {
            clearBloomBlockNotified(dataAfter);
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
                notifyBloomBlockedOnce(fresh, bloomBlock);
                return;
            }
            clearBloomBlockNotified(fresh);
            fresh.stage = 2;
            fresh.bloomedAt = Date.now();
            const slotEl = document.querySelector(`[data-slot="${slotName}"]`);
            if (slotEl) renderSlot(slotEl, fresh);
            showPositiveTip('bloomed');
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

updateRoomScale();
window.addEventListener('resize', updateRoomScale);

const DEV_MAX_LEVEL = 6;

function applyUnlocksForLevel(level, { markNotified = false } = {}) {
    Object.entries(POT_CONFIG).forEach(([num, cfg]) => {
        POT_CONFIG[num].isUnlocked = (cfg.unlockLevel || 1) <= level;
        if (markNotified && POT_CONFIG[num].isUnlocked && currentUser) {
            localStorage.setItem(`potUnlockNotified_${currentUser}_${num}`, '1');
        }
    });
    Object.entries(WATERING_CAN_CONFIG).forEach(([id, cfg]) => {
        WATERING_CAN_CONFIG[id].isUnlocked = (cfg.unlockLevel || 1) <= level;
        if (markNotified && WATERING_CAN_CONFIG[id].isUnlocked && currentUser) {
            localStorage.setItem(`wateringCanUnlockNotified_${currentUser}_${id}`, '1');
        }
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

document.getElementById('zoomOverlay')?.addEventListener('transitionend', () => {
    if (devStatePanel) {
        devStatePanel.style.display = zoomedSlot ? 'block' : 'none';
    }
});

if (devApplyStateBtn) {
    devApplyStateBtn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (!zoomedSlot) {
            alert('Сначала открой слот (кликни на горшок)');
            return;
        }
        const name = zoomedSlot.name;
        const state = devStateSelect?.value;
        if (!state) return;

        if (!applyDevPlantState(name, state)) {
            alert('Не удалось применить состояние');
            return;
        }

        const data = slotData[name];
        if (devStatePanel) devStatePanel.style.display = 'block';
    });
}
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

    loadLevel();

    const results = await Promise.all([
        loadPlantsCatalog(),
        loadPots(),
        loadWateringCans()
    ]);

    if (!results[0] || Object.keys(PLANTS).length === 0) {
        console.error('КРИТИЧЕСКАЯ ОШИБКА: Не удалось загрузить растения с сервера');
        showNotification('Ошибка загрузки данных. Попробуйте обновить страницу.', true);
    }

    if (!results[1] || Object.keys(POT_CONFIG).length === 0) {
        console.warn('Не удалось загрузить горшки, использую стандартные');
        showNotification('Ошибка загрузки данных. Попробуйте обновить страницу.', true);
    }

    if (!results[2] || Object.keys(WATERING_CAN_CONFIG).length === 0) {
        console.warn('Не удалось загрузить лейки, использую стандартные');
        showNotification('Ошибка загрузки данных. Попробуйте обновить страницу.', true);
    }

    applyUnlocksForLevel(currentLevel, { markNotified: true });
    const loadedFromServer = await loadStateFromServer();
    if (!loadedFromServer) {
        loadState();
    }
    await loadAchievementsFromServer();
    applyUnlocksForLevel(currentLevel, { markNotified: true });
    renderQuests();
    renderPotChoices();
    renderFlowerChoices();
    renderWateringCanChoices();
    updateAchievementsDisplay();
    initAchievementsClick();
    scheduleOverwateringCheck();

    restoreWateringCanSelection();

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

    loadingOverlay.remove();

    if (typeof window.tryOpenFirstTimeTutorial === 'function') {
        window.tryOpenFirstTimeTutorial();
    }
})();

(function initTutorial() {
    const TUTORIAL_ARROW_SRC = 'images/button/кнопка-стрелка обучения.png';
    const FIRST_TIME_ACHIEVEMENTS_STEP = 5;
    const FIRST_TIME_FINALE_STEP = 6;

    const TUTORIAL_CONFIG = {
        firstTime: {
            totalSteps: 7,
            textWrapperId: 'firstTimeTutorial',
            dotsId: 'firstTimeDots',
            hasSkipButton: true
        },
        short: {
            totalSteps: 6,
            textWrapperId: 'shortTutorial',
            dotsId: 'shortDots',
            hasSkipButton: false
        }
    };

    let currentMode = 'short';
    let tutorialCurrentStep = 0;

    const tutorialOverlay = document.getElementById('tutorialOverlay');
    const firstTimeWrapper = document.getElementById('firstTimeTutorial');
    const shortWrapper = document.getElementById('shortTutorial');
    const firstTimeDotsEl = document.getElementById('firstTimeDots');
    const shortDotsEl = document.getElementById('shortDots');
    const tutorialDotsWrapper = document.querySelector('.tutorial-dots-wrapper');
    const skipWrapper = document.getElementById('tutorialSkipWrapper');
    const tutorialBackBtn = document.getElementById('tutBackBtn');
    const tutorialNextBtn = document.getElementById('tutNextBtn');
    const tutorialNextBtnImg = document.getElementById('tutNextBtnImg');
    const tutorialNextBtnLabel = document.getElementById('tutNextBtnLabel');
    const tutorialSkipBtn = document.getElementById('tutSkipBtn');
    const tutorialSkipBtnImg = document.getElementById('tutSkipBtnImg');
    const tutorialSkipBtnLabel = document.getElementById('tutSkipBtnLabel');
    const tutorialCloseBtn = document.getElementById('closeTutorialBtn');
    const tutorialWindow = tutorialOverlay?.querySelector('.tutorial-window');

    function setTutorialClosableUi(isClosable) {
        if (tutorialWindow) {
            tutorialWindow.classList.toggle('tutorial-window--closable', isClosable);
        }
        if (tutorialCloseBtn) {
            tutorialCloseBtn.hidden = !isClosable;
        }
    }

    function getCurrentDots() {
        return currentMode === 'firstTime'
            ? document.querySelectorAll('#firstTimeDots .tut-dot')
            : document.querySelectorAll('#shortDots .tut-dot');
    }

    function getCurrentSteps() {
        return currentMode === 'firstTime'
            ? document.querySelectorAll('#firstTimeTutorial .tutorial-step')
            : document.querySelectorAll('#shortTutorial .tutorial-step');
    }

    function setNextButtonNormal() {
        if (tutorialNextBtnImg) {
            tutorialNextBtnImg.hidden = false;
            tutorialNextBtnImg.src = TUTORIAL_ARROW_SRC;
            tutorialNextBtnImg.alt = 'Далее';
        }
        if (tutorialNextBtnLabel) {
            tutorialNextBtnLabel.hidden = true;
        }
        if (tutorialNextBtn) {
            tutorialNextBtn.classList.remove('tut-next-btn--start-game');
        }
    }

    function setNextButtonStartGame() {
        if (tutorialNextBtnImg) {
            tutorialNextBtnImg.hidden = true;
        }
        if (tutorialNextBtnLabel) {
            tutorialNextBtnLabel.hidden = false;
        }
        if (tutorialNextBtn) {
            tutorialNextBtn.classList.add('tut-next-btn--start-game');
        }
    }

    function setSkipButtonNormal() {
        if (tutorialSkipBtnImg) {
            tutorialSkipBtnImg.hidden = false;
        }
        if (tutorialSkipBtnLabel) {
            tutorialSkipBtnLabel.hidden = true;
        }
        if (tutorialSkipBtn) {
            tutorialSkipBtn.classList.remove('tut-skip-btn--complete');
        }
    }

    function setSkipButtonComplete() {
        if (tutorialSkipBtnImg) {
            tutorialSkipBtnImg.hidden = true;
        }
        if (tutorialSkipBtnLabel) {
            tutorialSkipBtnLabel.hidden = false;
        }
        if (tutorialSkipBtn) {
            tutorialSkipBtn.classList.add('tut-skip-btn--complete');
        }
    }

    function updateTutorialChrome() {
        if (currentMode === 'firstTime') {
            const isFinale = tutorialCurrentStep === FIRST_TIME_FINALE_STEP;
            const isAchievementsStep = tutorialCurrentStep === FIRST_TIME_ACHIEVEMENTS_STEP;

            if (tutorialDotsWrapper) {
                tutorialDotsWrapper.style.display = isFinale ? 'none' : 'flex';
            }
            if (tutorialBackBtn) {
                tutorialBackBtn.style.visibility = 'visible';
                tutorialBackBtn.disabled = false;
                tutorialBackBtn.classList.remove('is-disabled');
                tutorialBackBtn.setAttribute('aria-disabled', 'false');
                tutorialBackBtn.style.pointerEvents = 'auto';
            }
            if (skipWrapper) {
                skipWrapper.style.display = 'flex';
                skipWrapper.classList.toggle('is-hidden', isFinale);
            }
            setTutorialClosableUi(false);
            if (isFinale) {
                setNextButtonStartGame();
            } else {
                setNextButtonNormal();
            }
            if (isAchievementsStep) {
                setSkipButtonNormal();
            } else if (!isFinale) {
                setSkipButtonNormal();
            }
            document.body.classList.add('first-time-onboarding');
            return;
        }

        document.body.classList.remove('first-time-onboarding');
        setSkipButtonNormal();
        if (tutorialDotsWrapper) {
            tutorialDotsWrapper.style.display = 'flex';
        }
        if (tutorialBackBtn) {
            const onFirstStep = tutorialCurrentStep === 0;
            tutorialBackBtn.style.visibility = 'visible';
            tutorialBackBtn.disabled = onFirstStep;
            tutorialBackBtn.classList.toggle('is-disabled', onFirstStep);
            tutorialBackBtn.setAttribute('aria-disabled', onFirstStep ? 'true' : 'false');
            tutorialBackBtn.style.pointerEvents = onFirstStep ? 'none' : 'auto';
        }
        if (skipWrapper) {
            skipWrapper.style.display = 'none';
            skipWrapper.classList.remove('is-hidden');
        }
        setTutorialClosableUi(true);
        setNextButtonNormal();
    }

    function showTutorialStep(step) {
        const config = TUTORIAL_CONFIG[currentMode];
        if (step < 0) step = 0;
        if (step >= config.totalSteps) step = config.totalSteps - 1;
        tutorialCurrentStep = step;

        const steps = getCurrentSteps();
        const dots = getCurrentDots();

        steps.forEach((stepEl, index) => {
            stepEl.classList.toggle('active', index === tutorialCurrentStep);
        });

        dots.forEach((dot, index) => {
            dot.classList.toggle('active', index === tutorialCurrentStep);
        });

        updateTutorialChrome();
    }

    function finishFirstTimeTutorial() {
        if (currentUser) {
            localStorage.setItem(`tutorialDone_${currentUser}`, '1');
        }
        localStorage.setItem('isReturningUser', 'true');
        localStorage.removeItem('pendingFirstTimeTutorial');
        markTutorialCompleteOnServer();
        closeTutorial(false);
    }

    function nextTutorialStep() {
        const config = TUTORIAL_CONFIG[currentMode];
        if (currentMode === 'firstTime' && tutorialCurrentStep === FIRST_TIME_FINALE_STEP) {
            finishFirstTimeTutorial();
            return;
        }
        if (tutorialCurrentStep < config.totalSteps - 1) {
            showTutorialStep(tutorialCurrentStep + 1);
        } else {
            closeTutorial(true);
        }
    }

    function goBackToWelcomeFromTutorial() {
        sessionStorage.setItem('showWelcomeAfterRegister', '1');
        sessionStorage.setItem('welcomeResumeStep', '1');
        localStorage.setItem('isReturningUser', 'false');
        localStorage.removeItem('pendingFirstTimeTutorial');
        closeTutorial(false);
        window.location.href = 'welcome.html';
    }

    function prevTutorialStep() {
        if (currentMode === 'firstTime' && tutorialCurrentStep === 0) {
            goBackToWelcomeFromTutorial();
            return;
        }
        if (tutorialCurrentStep > 0) {
            showTutorialStep(tutorialCurrentStep - 1);
        }
    }

    function skipTutorial() {
        if (currentMode === 'firstTime') {
            showTutorialStep(FIRST_TIME_FINALE_STEP);
            return;
        }
        closeTutorial(true);
    }

    function openTutorial(mode = 'short') {
        currentMode = mode;
        tutorialCurrentStep = 0;
        setTutorialClosableUi(mode === 'short');

        if (firstTimeWrapper) firstTimeWrapper.style.display = mode === 'firstTime' ? 'flex' : 'none';
        if (shortWrapper) shortWrapper.style.display = mode === 'short' ? 'flex' : 'none';
        if (firstTimeDotsEl) firstTimeDotsEl.style.display = mode === 'firstTime' ? 'flex' : 'none';
        if (shortDotsEl) shortDotsEl.style.display = mode === 'short' ? 'flex' : 'none';

        showTutorialStep(0);
        if (tutorialOverlay) {
            tutorialOverlay.style.display = 'flex';
            tutorialOverlay.classList.add('active');
        }
    }

    function closeTutorial(markFirstTimeDone = false) {
        if (tutorialOverlay) {
            tutorialOverlay.style.display = 'none';
            tutorialOverlay.classList.remove('active');
        }
        if (markFirstTimeDone && currentUser && currentMode === 'firstTime') {
            localStorage.setItem(`tutorialDone_${currentUser}`, '1');
            localStorage.setItem('isReturningUser', 'true');
            localStorage.removeItem('pendingFirstTimeTutorial');
            markTutorialCompleteOnServer();
        }
        document.body.classList.remove('first-time-onboarding');
        setTutorialClosableUi(false);
        tutorialCurrentStep = 0;
        setNextButtonNormal();
    }

    function goToTutorialStep(step) {
        const config = TUTORIAL_CONFIG[currentMode];
        const targetStep = parseInt(step, 10);
        if (currentMode === 'firstTime' && targetStep === FIRST_TIME_FINALE_STEP) {
            showTutorialStep(FIRST_TIME_FINALE_STEP);
            return;
        }
        if (targetStep >= 0 && targetStep < config.totalSteps) {
            showTutorialStep(targetStep);
        }
    }

    if (tutorialBackBtn) {
        tutorialBackBtn.addEventListener('click', (e) => {
            e.preventDefault();
            prevTutorialStep();
        });
    }

    if (tutorialNextBtn) {
        tutorialNextBtn.addEventListener('click', (e) => {
            e.preventDefault();
            nextTutorialStep();
        });
    }

    if (tutorialSkipBtn) {
        tutorialSkipBtn.addEventListener('click', (e) => {
            e.preventDefault();
            skipTutorial();
        });
    }

    if (tutorialCloseBtn) {
        tutorialCloseBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            closeTutorial(false);
        });
    }

    function bindDotEvents() {
        const dots = document.querySelectorAll('.tut-dot');
        dots.forEach(dot => {
            dot.removeEventListener('click', dot._handler);
            dot._handler = () => {
                const step = dot.getAttribute('data-tut-step');
                if (step !== null) goToTutorialStep(step);
            };
            dot.addEventListener('click', dot._handler);
        });
    }

    const observer = new MutationObserver(() => bindDotEvents());
    observer.observe(document.body, { childList: true, subtree: true });
    bindDotEvents();

    if (tutorialOverlay) {
        tutorialOverlay.addEventListener('click', (e) => {
            if (e.target === tutorialOverlay && currentMode !== 'firstTime') {
                closeTutorial(false);
            }
        });
    }

    window.openTutorial = openTutorial;
    window.closeTutorialGlobal = () => closeTutorial(false);
    window.nextTutorialGlobal = nextTutorialStep;
    window.prevTutorialGlobal = prevTutorialStep;
    window.goToTutorialStep = goToTutorialStep;

    function tryOpenFirstTimeTutorial() {
        const pendingTutorial = localStorage.getItem('pendingFirstTimeTutorial') === '1';
        const isReturning = localStorage.getItem('isReturningUser') === 'true';
        const tutDone = currentUser ? localStorage.getItem(`tutorialDone_${currentUser}`) : null;

        if (!currentUser || isReturning || tutDone) {
            return false;
        }

        if (pendingTutorial || localStorage.getItem('isReturningUser') === 'false') {
            openTutorial('firstTime');
            return true;
        }

        return false;
    }

    window.tryOpenFirstTimeTutorial = tryOpenFirstTimeTutorial;

    const helpBtn = document.getElementById('helpBtn');
    if (helpBtn) {
        helpBtn.addEventListener('click', () => {
            openTutorial('short');
        });
    }
})();