
// ЗАЩИТА - проверка через сервер


const API_BASE_URL = 'http://localhost:5000/api';

// Глобальные данные с сервера
let PLANTS = {};
let POT_CONFIG = {};
let WATERING_CAN_CONFIG = {};
let currentLevel = 1;
let currentUser = null;
let currentZoomedPlantId = null;


// КОНСТАНТЫ ВРЕМЕНИ РОСТА - ТЕСТОВЫЙ РЕЖИМ (ИЗМЕНИТЬ ИХ НА ДНИ)

const SEEDLING_MS = 10 * 1000;   // 10 секунд до ростка
const BLOOM_MS = 30 * 1000;      // 30 секунд до цветения


// НАСТРОЙКИ ПОЛОЖЕНИЯ РАСТЕНИЙ В ГОРШКЕ

const PLANT_OFFSETS = {
    1: { // Спатифиллум
        default: { bottom: '35px', width: '100px', left: '50%' },
        stages: {
            1: { bottom: '35px', width: '100px', left: '50%' },
            2: { bottom: '20px', width: '120px', left: '50%' }
        },
        diseases: {
            'желтение': { bottom: '35px', width: '90px', left: '50%' },
            'не цветет': { bottom: '35px', width: '95px', left: '50%' },
            'сохнут кончики': { bottom: '35px', width: '90px', left: '50%' }
        }
    },
    2: { // Кактус
        default: { bottom: '45px', width: '60px', left: '50%' },
        stages: {
            1: { bottom: '45px', width: '60px', left: '50%' },
            2: { bottom: '40px', width: '70px', left: '50%' }
        },
        diseases: {
            'вытягивание': { bottom: '50px', width: '55px', left: '50%' },
            'не цветет': { bottom: '45px', width: '60px', left: '50%' },
            'сморщенный стебель': { bottom: '45px', width: '55px', left: '50%' }
        }
    },
    3: { // Фикус
        default: { bottom: '40px', width: '75px', left: '50%' },
        stages: {
            1: { bottom: '40px', width: '75px', left: '50%' },
            2: { bottom: '35px', width: '90px', left: '50%' }
        },
        diseases: {
            'желтение': { bottom: '40px', width: '70px', left: '50%' },
            'пятна': { bottom: '40px', width: '70px', left: '50%' },
            'увядание': { bottom: '40px', width: '65px', left: '50%' }
        }
    }
};

// Функция получения смещений
function getPlantOffsets(plantId, stage, diseaseText = null) {
    const plantConfig = PLANT_OFFSETS[plantId];
    if (!plantConfig) return { bottom: '40px', width: '70px', left: '50%' };

    if (diseaseText) {
        for (const [key, offsets] of Object.entries(plantConfig.diseases || {})) {
            if (diseaseText.toLowerCase().includes(key.toLowerCase())) {
                return offsets;
            }
        }
        return plantConfig.default;
    }

    if (plantConfig.stages && plantConfig.stages[stage]) {
        return plantConfig.stages[stage];
    }

    return plantConfig.default;
}


// КОНФИГУРАЦИЯ ДОСТИЖЕНИЙ

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

// Конфигурация наград за уровни
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
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json'
            }
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


// ЗАГРУЗКА ДАННЫХ С СЕРВЕРА


async function loadPlantsCatalog() {
    try {
        const response = await fetch(`${API_BASE_URL}/plants/catalog`, {
            credentials: 'include'
        });
        const data = await response.json();

        if (data.success && data.plants) {
            const plants = {};
            data.plants.forEach(plant => {
                const plantId = plant.species_id || plant.id;
                const speciesName = (plant.species_name || plant.name || '').toLowerCase();

                let plantFolder = 'default';
                let diseaseImages = {};

                if (speciesName.includes('спатифиллум') || speciesName === 'spathiphyllum') {
                    plantFolder = 'spathiphyllum';
                    diseaseImages = {
                        'желтение': 'images/plant/spathiphyllum/disease/желтение.png',
                        'не цветет': 'images/plant/spathiphyllum/disease/не цветет.png',
                        'сохнут кончики': 'images/plant/spathiphyllum/disease/сохнут кончики.png'
                    };
                } else if (speciesName.includes('кактус') || speciesName === 'cactus') {
                    plantFolder = 'cactus';
                    diseaseImages = {
                        'вытягивание': 'images/plant/cactus/disease/вытягивание.png',
                        'не цветет': 'images/plant/cactus/disease/не цветет.png',
                        'сморщенный стебель': 'images/plant/cactus/disease/сморщенный стебель.png'
                    };
                } else if (speciesName.includes('фикус') || speciesName === 'ficus') {
                    plantFolder = 'ficus';
                    diseaseImages = {
                        'желтение': 'images/plant/ficus/disease/желтение.png',
                        'пятна': 'images/plant/ficus/disease/пятна.png',
                        'увядание': 'images/plant/ficus/disease/увядание.png'
                    };
                }

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
                    deadImage: `images/plant/${plantFolder}/stage/${plantFolder === 'spathiphyllum' ? 'спатифиллум умер.png' : (plantFolder === 'cactus' ? 'кактус умер.png' : 'фикус умер.png')}`
                };
            });
            PLANTS = plants;
            console.log('Загружены растения из БД:', Object.keys(PLANTS).length);
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
            credentials: 'include'
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
            console.log('Загружены горшки:', Object.keys(POT_CONFIG).length);
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
            credentials: 'include'
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
            console.log('Загружены лейки:', Object.keys(WATERING_CAN_CONFIG).length);
            return true;
        }
        return false;
    } catch (error) {
        console.error('Ошибка загрузки леек:', error);
        return false;
    }
}


// ДАННЫЕ ПО УМОЛЧАНИЮ


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


// СОСТОЯНИЕ

const slotData = {};
let activeSlot = null;
let zoomedSlot = null;

const popupQueue = [];
let popupShowing = false;


// DOM

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


// УТИЛИТЫ

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


// ВСПЛЫВАЮЩИЕ УВЕДОМЛЕНИЯ


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


// АЧИВКИ


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


// СИСТЕМА БОЛЕЗНЕЙ


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
        too_light: '🍃 Листья желтеют — солнечный ожог',
        big_pot: '🍃 Не цветёт — слишком большой горшок',
        overwatered: '🍃 Сохнут кончики листьев — перелив'
    },
    2: {
        too_dark: '🌵 Вытягивание и бледность стебля — не хватает света',
        no_flower: '🌵 Нет цветения — причина в нехватке света',
        overwatered: '🌵 Сморщенный стебель — перелив или застой воды'
    },
    3: {
        too_light: '🍂 Пятна на листьях — солнечный ожог',
        overwatered: '🍂 Желтеют листья — перелив',
        under_watered: '🍂 Увядание листьев — недостаток воды'
    }
};

function getDiseaseImage(plant, diseaseText) {
    if (!plant || !plant.diseaseImages || !diseaseText) return null;

    for (const [key, imagePath] of Object.entries(plant.diseaseImages)) {
        if (diseaseText.toLowerCase().includes(key.toLowerCase())) {
            return imagePath;
        }
    }

    const firstImage = Object.values(plant.diseaseImages)[0];
    return firstImage || null;
}

function checkWateringHealth(slotName, data) {
    if (!data || !data.plant) return;
    const plant = PLANTS[data.plant];
    if (!plant) return;

    if (data.stage < 1) return;
    if (!data.lastWateredAt) return;

    const now = Date.now();
    const hoursAgo = (now - data.lastWateredAt) / 3600000;

    if (!data.wateringHistory) {
        data.wateringHistory = [];
    }

    const lastHistoryEntry = data.wateringHistory[data.wateringHistory.length - 1];
    if (!lastHistoryEntry || (now - lastHistoryEntry.time) > 60000) {
        data.wateringHistory.push({
            time: data.lastWateredAt,
            interval: hoursAgo
        });
        if (data.wateringHistory.length > 5) {
            data.wateringHistory.shift();
        }
    }

    const recentWaterings = data.wateringHistory.slice(-3);
    const tooFrequentCount = recentWaterings.filter(w => w.interval < plant.waterIntervalMin).length;

    const hasOverwateringIssue = tooFrequentCount >= 2;
    const timeSinceLastWatering = hoursAgo;
    const shouldGetDisease = hasOverwateringIssue && timeSinceLastWatering >= 6 && !data.hasDisease;

    const isExtendedOverwater = data.wateringHistory.some(w =>
        w.interval < plant.waterIntervalMin && (now - w.time) > (plant.waterIntervalMax * 3600000)
    );

    if ((shouldGetDisease || isExtendedOverwater) && !data.hasDisease && data.stage >= 1) {
        const plantKey = parseInt(data.plant);
        data.hasDisease = true;
        data.hadMistakes = true;
        data.disease = PLANT_DISEASES[plantKey]?.overwatered || '💧 Перелив — корни загнивают из-за слишком частого полива';
        data.diseaseStartTime = now;
        showNotification(`⚠️ ${PLANTS[data.plant]?.name}: ${data.disease}`, true);
        saveState();
        checkAchievement_negativeEffect();

        if (zoomedSlot && zoomedSlot.name === slotName) {
            updateDiseaseInfo(data);
            showFixAdvice(data);
        }
    }

    saveState();
}

function checkLocationDisease(slotName) {
    const data = slotData[slotName];
    if (!data || !data.plant) return;

    if (data.stage < 1) return;

    const plantKey = parseInt(data.plant);
    const slotLight = SLOT_LIGHT[slotName];
    const plantReq = PLANT_LIGHT_REQ[plantKey];

    let diseaseMsg = null;

    if (slotLight && plantReq && slotLight !== plantReq) {
        const diseases = PLANT_DISEASES[plantKey];
        if (!diseases) return;

        if (slotLight === 'high' && plantReq === 'low') {
            diseaseMsg = diseases.too_light || 'Слишком много света — растение болеет';
        } else if (slotLight === 'low' && plantReq === 'high') {
            diseaseMsg = diseases.too_dark || diseases.no_flower || 'Слишком мало света';
        } else if (slotLight !== plantReq) {
            diseaseMsg = diseases.no_flower || 'Не подходящее место для растения';
        }
    }

    if (plantKey === 1 && data.pot === 3 && data.stage >= 1) {
        const diseases = PLANT_DISEASES[1];
        diseaseMsg = diseases.big_pot;
    }

    if (diseaseMsg && !data.hasDisease && data.stage >= 1) {
        data.hasDisease = true;
        data.hadMistakes = true;
        data.disease = diseaseMsg;
        saveState();
        showNotification(`🤒 ${PLANTS[data.plant]?.name}: ${diseaseMsg}`, true);
        checkAchievement_negativeEffect();
    } else if (!diseaseMsg && data.hasDisease && data.disease && !data.disease.includes('Перелив') && data.stage >= 1) {
        data.hasDisease = false;
        data.disease = null;
        saveState();
        markHealedPlant();
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
    setInterval(() => {
        Object.keys(slotData).forEach(slotName => {
            const data = slotData[slotName];
            if (data && data.plant && data.stage < 2 && data.lastWateredAt) {
                checkWateringHealth(slotName, data);
            }
        });
    }, 60000);
}


// ОЧЕРЕДЬ ПОПАПОВ

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


// УРОВЕНЬ

function updateLevelCircle(lvl) {
    currentLevel = lvl;
    const levelNum = document.getElementById('levelNum');
    if (levelNum) levelNum.textContent = lvl;
}


// ЗАДАНИЯ

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

function renderQuests() {
    const list = document.getElementById('questsList');
    if (!list) return;

    const quests = QUESTS_BY_LEVEL[currentLevel] || [];
    const done = getQuestsDoneIds();

    if (quests.length === 0) {
        list.innerHTML = '<div class="quest-item">Все задания выполнены! 🌟</div>';
        return;
    }

    list.innerHTML = quests.map(q => {
        const isDone = done.includes(q.id) || q.check();
        if (isDone && !done.includes(q.id)) markQuestDone(q.id);
        return `<div class="quest-item ${isDone ? 'done' : ''}">
            <span class="quest-check">${isDone ? '✓' : '○'}</span>
            <span class="quest-desc">${q.desc}</span>
        </div>`;
    }).join('');

    const allDone = quests.every(q => done.includes(q.id) || q.check());
    if (allDone) {
        const levelUpKey = `levelUp_${currentLevel}_done_${currentUser}`;
        if (!localStorage.getItem(levelUpKey)) {
            localStorage.setItem(levelUpKey, '1');
            setTimeout(() => {
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


// РАЗБЛОКИРОВКИ


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
            ${isCurrent ? '<span class="current-label">Сейчас</span>' : ''}
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
            headers: { 'Content-Type': 'application/json' },
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


// ПЕРЕСТАНОВКА ГОРШКОВ

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

    if (slotData[slotA] && slotData[slotA].plant) checkLocationDisease(slotA);
    if (slotData[slotB] && slotData[slotB].plant) checkLocationDisease(slotB);

    if (zoomedSlot) {
        if (zoomedSlot.name === slotA) {
            openZoom(slotElA, slotA, slotData[slotA]);
        } else if (zoomedSlot.name === slotB) {
            openZoom(slotElB, slotB, slotData[slotB]);
        }
    }
}


// СЛОТЫ — КЛИК

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
if (modalPlacePot) modalPlacePot.addEventListener('click', e => { if (e.target === modalPlacePot) closeModal(modalPlacePot); });

function placePot(slotEl, potNum) {
    const name = slotEl.dataset.slot;
    slotData[name] = { pot: potNum, plant: null, stage: -1, lastWateredAt: null, totalWaterings: 0, wateringsToNextStage: 3 };
    renderSlot(slotEl, slotData[name]);
    showNotification('Горшок поставлен! Теперь посади цветок 🌱', false);
    saveState();
}


// УДАЛЕНИЕ РАСТЕНИЯ

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


// ОТРИСОВКА СЛОТА

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

        let imageUrl;

        if (data.hasDisease && data.stage >= 1 && data.disease) {
            const diseaseImg = getDiseaseImage(plant, data.disease);
            imageUrl = diseaseImg || plant.stages[data.stage] || plant.stages[1];
        } else {
            imageUrl = plant.stages[data.stage] || plant.stages[1];
        }

        plantImg.src = imageUrl;
        plantImg.className = 'slot-plant-img';
        plantImg.alt = plant.name;

        const offsets = getPlantOffsets(plantId, data.stage, data.hasDisease ? data.disease : null);
        if (offsets) {
            plantImg.style.bottom = offsets.bottom;
            plantImg.style.width = offsets.width;
            plantImg.style.left = offsets.left;
            plantImg.style.transform = 'translateX(-50%)';
        }

        slotEl.appendChild(plantImg);

        if (data.hasDisease && data.stage >= 1) {
            const diseaseEffect = document.createElement('div');
            diseaseEffect.className = 'slot-disease-effect';
            diseaseEffect.textContent = '🤒';
            slotEl.appendChild(diseaseEffect);
        }
    }

    const hint = slotEl.querySelector('.slot-hint');
    if (hint) {
        if (!data.plant) {
            hint.textContent = 'Посадить цветок';
        } else if (data.stage === 0) {
            hint.textContent = '🌱 Прорастает...';
        } else if (data.stage === 1) {
            if (data.hasDisease) {
                hint.textContent = '🤒 Болеет...';
            } else {
                hint.textContent = '🌱 Росток';
            }
        } else if (data.stage === 2) {
            if (data.hasDisease) {
                hint.textContent = '🤒 Цветёт, но болеет';
            } else {
                hint.textContent = '🌸 Цветёт!';
            }
        }
    }
}


// ЗУМ ГОРШКА

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

    if (data.lastWateredAt) {
        const hoursAgo = (now - data.lastWateredAt) / 3600000;
        if (hoursAgo < plant.waterIntervalMin) {
            const hoursLeft = Math.ceil(plant.waterIntervalMin - hoursAgo);
            timerText = `💧 Полив через ${hoursLeft} ч`;
        } else if (hoursAgo <= plant.waterIntervalMax) {
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
        if (data.disease.includes('света')) {
            advice = '💡 Решение: Переставь горшок в другое место. Нажми на кнопку "Переставить горшок" в левой панели.';
        } else if (data.disease.includes('полив') || data.disease.includes('Перелив')) {
            advice = '💧 Решение: Уменьши частоту полива. Дай почве просохнуть.';
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

function openZoom(slotEl, name, data) {
    zoomedSlot = { slotEl, name };
    currentZoomedPlantId = name;

    const zoomPotImg = document.getElementById('zoomPotImg');
    if (zoomPotImg && POT_CONFIG[data.pot]) {
        zoomPotImg.src = POT_CONFIG[data.pot].img;
    }

    const plantImg = document.getElementById('zoomPlantImg');
    const waterBtn = document.getElementById('waterBtnRight');
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

        if (plantImg) {
            if (data.stage >= 1) {
                let imageUrl;
                if (data.hasDisease && data.disease) {
                    const diseaseImg = getDiseaseImage(plant, data.disease);
                    imageUrl = diseaseImg || plant.stages[data.stage] || plant.stages[1];
                } else {
                    imageUrl = plant.stages[data.stage] || plant.stages[1];
                }

                plantImg.src = imageUrl;
                plantImg.style.display = 'block';

                const offsets = getPlantOffsets(plantId, data.stage, data.hasDisease ? data.disease : null);
                if (offsets) {
                    plantImg.style.bottom = offsets.bottom;
                    plantImg.style.width = offsets.width;
                } else {
                    plantImg.style.bottom = '35px';
                    plantImg.style.width = '180px';
                }
            } else {
                plantImg.style.display = 'none';
            }
        }

        const zoomPlantName = document.getElementById('zoomPlantName');
        if (zoomPlantName) zoomPlantName.textContent = `${plant.name} — ${plant.nickname}`;

        const zoomStageLabel = document.getElementById('zoomStageLabel');
        if (zoomStageLabel) {
            if (data.stage === 0) {
                zoomStageLabel.textContent = '🌰 Семечко посажено';
            } else if (data.stage === 1) {
                if (data.hasDisease) {
                    zoomStageLabel.textContent = '🤒 Росток болеет';
                } else {
                    zoomStageLabel.textContent = '🌱 Росток';
                }
            } else if (data.stage === 2) {
                if (data.hasDisease) {
                    zoomStageLabel.textContent = '🤒 Цветёт, но болеет';
                } else {
                    zoomStageLabel.textContent = '🌸 Расцвёл';
                }
            } else {
                zoomStageLabel.textContent = STAGE_NAMES[data.stage] || STAGE_NAMES[0];
            }
        }

        if (waterBtn) waterBtn.disabled = data.stage >= 2;
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

        if (waterBtn) waterBtn.disabled = true;
        if (descBtn) descBtn.style.display = 'none';
        if (repotBtn) repotBtn.style.display = 'none';
        if (moveBtn) moveBtn.style.display = 'none';
        if (removeBtn) removeBtn.style.display = 'none';
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
if (zoomClose) zoomClose.addEventListener('click', () => closeModal(zoomOverlay));
if (zoomOverlay) zoomOverlay.addEventListener('click', e => { if (e.target === zoomOverlay) closeModal(zoomOverlay); });


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
            ${isCurrent ? '<span class="current-label">Сейчас</span>' : ''}
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


// КНОПКИ В ЗУМЕ


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
        if (confirm('Вы уверены, что хотите выбросить растение? Горшок освободится.')) {
            removePlantFromSlot(zoomedSlot.name);
            closeModal(zoomOverlay);
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

const waterBtnRight = document.getElementById('waterBtnRight');
if (waterBtnRight) {
    waterBtnRight.addEventListener('click', () => {
        if (!zoomedSlot) return;
        const { slotEl, name } = zoomedSlot;
        const data = slotData[name];
        if (!data?.plant || data.stage >= 2 || !PLANTS[data.plant]) return;

        const plant = PLANTS[data.plant];
        const now = Date.now();

        if (data.lastWateredAt) {
            const hoursAgo = (now - data.lastWateredAt) / 3600000;
            if (hoursAgo < plant.waterIntervalMin) {
                const hoursLeft = Math.ceil(plant.waterIntervalMin - hoursAgo);
                showNotification(`⚠️ Слишком рано! Лучше поливать через ${hoursLeft} ч. Растение может заболеть.`, true);
            }
        }

        startWateringAnimation();

        setTimeout(() => {
            data.lastWateredAt = now;
            data.totalWaterings = (data.totalWaterings || 0) + 1;

            const globalTotal = getTotalWaterings() + 1;
            localStorage.setItem(`totalWaterings_${currentUser}`, String(globalTotal));

            checkWateringHealth(name, data);

            showNotification('Полито! 💧 Растение радуется', false);

            renderSlot(slotEl, data);
            updateWateringInfo(data);
            updateNextWateringTimer(data);

            const zoomPlantImg = document.getElementById('zoomPlantImg');
            if (zoomPlantImg && data.plant && data.stage >= 1 && PLANTS[data.plant]) {
                zoomPlantImg.src = PLANTS[data.plant].stages[data.stage];
                zoomPlantImg.style.display = 'block';
            }

            const zoomStageLabel = document.getElementById('zoomStageLabel');
            if (zoomStageLabel && STAGE_NAMES[data.stage]) {
                zoomStageLabel.textContent = STAGE_NAMES[data.stage];
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
    if (waterBtnRight) waterBtnRight.disabled = true;
}

function stopWateringAnimation() {
    const anim = document.getElementById('wateringAnim');
    if (anim) anim.classList.remove('active');
    if (waterBtnRight) waterBtnRight.disabled = false;
}


// МУЗЫКА

let musicPlaying = false;
const musicBtnEl = document.getElementById('musicBtn');
const bgMusic = document.getElementById('bgMusic');

if (bgMusic) bgMusic.src = 'music/модный поп.mp3';

function tryAutoplay() {
    if (!bgMusic) return;
    bgMusic.play().then(() => {
        musicPlaying = true;
        if (musicBtnEl) musicBtnEl.textContent = '🔇';
    }).catch(() => {});
}

window.addEventListener('load', () => { setTimeout(tryAutoplay, 500); });

if (musicBtnEl) {
    musicBtnEl.addEventListener('click', () => {
        if (!bgMusic) return;
        if (musicPlaying) {
            bgMusic.pause();
            musicBtnEl.textContent = '🎵';
            musicPlaying = false;
        } else {
            bgMusic.play().catch(() => showNotification('Не удалось воспроизвести музыку', true));
            musicBtnEl.textContent = '🔇';
            musicPlaying = true;
        }
    });
}


// КНОПКИ УПРАВЛЕНИЯ

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
            localStorage.removeItem('isReturningUser');
            fetch('http://localhost:5000/api/auth/logout', {method:'POST', credentials:'include'})
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


// СОХРАНЕНИЕ / ЗАГРУЗКА

function saveState() {
    localStorage.setItem(`garden_${currentUser}`, JSON.stringify(slotData));
}

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
        if (!data.hasDisease && data.stage >= 1) {
            const oldStage = data.stage;
            data.stage = 2;
            data.bloomedAt = data.bloomedAt || (data.plantedAt + BLOOM_MS);
            const slotEl = document.querySelector(`[data-slot="${slotName}"]`);
            if (slotEl) renderSlot(slotEl, data);

            if (oldStage !== 2) {
                showNotification(`🌸 ${PLANTS[data.plant]?.name} расцвело!`, false);
                checkAllAchievementsOnBloom(slotName, data);
            }
            saveState();
            checkQuestsAfterAction();
        } else if (data.hasDisease) {
            data.stage = Math.min(data.stage, 1);
            showNotification(`⚠️ ${PLANTS[data.plant]?.name} не может расцвести из-за болезни!`, true);
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
            if (d.hasDisease) {
                showNotification(`⚠️ ${PLANTS[d.plant]?.name} не может расцвести из-за болезни!`, true);
                return;
            }
            d.stage = 2;
            d.bloomedAt = Date.now();
            const slotEl = document.querySelector(`[data-slot="${slotName}"]`);
            if (slotEl) renderSlot(slotEl, d);
            showNotification(`🌸 ${PLANTS[d.plant]?.name} расцвело!`, false);
            checkAllAchievementsOnBloom(slotName, d);
            saveState();
            checkQuestsAfterAction();
        }, msUntilBloom);
    }
}

function loadLevel() {
    const lvl = parseInt(localStorage.getItem(`currentLevel_${currentUser}`) || '1');
    updateLevelCircle(lvl);
}


// ОБУЧАЛКА

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


// ИНИЦИАЛИЗАЦИЯ

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
    loadState();
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