const API_BASE_URL = 'http://localhost:5000/api';

const ROOM_DESIGN_WIDTH = 1280;
const ROOM_DESIGN_HEIGHT = 720;
const ZOOM_DESIGN_WIDTH = 780;
const ZOOM_DESIGN_HEIGHT = 500;
const ZOOM_VIEWPORT_FILL = 0.75;
const LETTERBOX_LOGO_MIN_HEIGHT = 88;

const MODAL_VIEWPORT_FILL = 0.75;
const MODAL_MIN_SCALE = 0.28;
const TUTORIAL_DESIGN_W = 550;
const TUTORIAL_DESIGN_H = 620;
const TUTORIAL_SIZE_BOOST = 1.05;
const TUTORIAL_MAX_SCALE = 1.15;
const TUTORIAL_VIEWPORT_FILL = 0.82;
const PLANT_DESC_DESIGN_W = 500;
const PLANT_DESC_DESIGN_H = 580;
const ACHIEVEMENTS_DESIGN_W = 1000;
const ACHIEVEMENTS_DESIGN_H = 780;
const ACHIEVEMENTS_VIEWPORT_FILL = 0.88;
const ACHIEVEMENTS_MAX_SCALE = 1.45;
const ACHIEVEMENTS_SIZE_BOOST = 1.18;
const CHOICE_PICKER_DESIGN_W = 580;
const CHOICE_PICKER_DESIGN_H = 460;
const MOVE_MODAL_DESIGN_W = 1100;
const MOVE_MODAL_DESIGN_H = 500;

function modalViewportScale(designW, designH, fill = MODAL_VIEWPORT_FILL, maxScale = 1) {
    const raw = Math.min(
        (window.innerWidth * fill) / designW,
        (window.innerHeight * fill) / designH
    );
    return Math.max(MODAL_MIN_SCALE, Math.min(raw, maxScale));
}

function computeTutorialScale() {
    const fitScale = modalViewportScale(
        TUTORIAL_DESIGN_W,
        TUTORIAL_DESIGN_H,
        TUTORIAL_VIEWPORT_FILL,
        999
    );
    return Math.max(MODAL_MIN_SCALE, Math.min(fitScale * TUTORIAL_SIZE_BOOST, TUTORIAL_MAX_SCALE));
}

function computeAchievementsScale() {
    const fitScale = modalViewportScale(
        ACHIEVEMENTS_DESIGN_W,
        ACHIEVEMENTS_DESIGN_H,
        ACHIEVEMENTS_VIEWPORT_FILL,
        ACHIEVEMENTS_MAX_SCALE
    );
    return Math.max(
        MODAL_MIN_SCALE,
        Math.min(fitScale * ACHIEVEMENTS_SIZE_BOOST, ACHIEVEMENTS_MAX_SCALE)
    );
}

function updateModalScales() {
    const root = document.documentElement;
    root.style.setProperty('--tutorial-scale', String(computeTutorialScale()));
    root.style.setProperty('--plant-desc-scale', String(
        modalViewportScale(PLANT_DESC_DESIGN_W, PLANT_DESC_DESIGN_H)
    ));
    root.style.setProperty('--achievements-scale', String(computeAchievementsScale()));
    root.style.setProperty('--choice-picker-scale', String(
        modalViewportScale(CHOICE_PICKER_DESIGN_W, CHOICE_PICKER_DESIGN_H)
    ));
    root.style.setProperty('--move-modal-scale', String(
        modalViewportScale(MOVE_MODAL_DESIGN_W, MOVE_MODAL_DESIGN_H)
    ));
}

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
    updateModalScales();
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

const ACHIEVEMENT_BACK_TO_FRONT = {
    grow_to_maturity_perfect: 'caring_parent',
    first_wither: 'all_lost',
    first_negative_effect: 'oops_error',
    grow_all_species: 'collector',
    daily_streak: 'patient_gardener',
    reach_level: 'flora_guard'
};

const ACHIEVEMENT_NAMES = {
    caring_parent: 'Заботливый родитель',
    collector: 'Коллекционер',
    flora_guard: 'Страж флоры',
    patient_gardener: 'Терпеливый садовод',
    oops_error: 'Упс, ошибка',
    all_lost: 'Ой, всё пропало'
};

let serverQuests = [];
let serverQuestLevel = 1;
let serverQuestsAllCompleted = false;

async function postGameAction(path, body = {}) {
    const response = await fetch(`${API_BASE_URL}/game/${path}`, {
        method: 'POST',
        headers: getAuthHeaders(),
        credentials: 'include',
        body: JSON.stringify(body)
    });
    return response.json();
}

function applyServerAchievements(newAchievements = []) {
    if (!Array.isArray(newAchievements) || !newAchievements.length) return;

    newAchievements.forEach((ach) => {
        const frontId = ACHIEVEMENT_BACK_TO_FRONT[ach.requirement_type]
            || ach.requirement_type
            || ach.id;
        if (!frontId || localStorage.getItem(`achievement_unlocked_${currentUser}_${frontId}`) === 'true') {
            return;
        }
        localStorage.setItem(`achievement_unlocked_${currentUser}_${frontId}`, 'true');
        enqueuePopup('achievement', {
            name: ach.name || ACHIEVEMENT_NAMES[frontId] || ach.name,
            id: frontId
        });
    });
    updateAchievementsDisplay();
}

function applyServerLevelUp(levelUp) {
    if (!levelUp?.newLevel) return;
    currentLevel = levelUp.newLevel;
    localStorage.setItem(`currentLevel_${currentUser}`, String(currentLevel));
    updateLevelCircle(currentLevel);
    applyUnlocksForLevel(currentLevel);
    checkAndUnlockPots();
    checkAndUnlockWateringCans();
    renderPotChoices();
    renderFlowerChoices();
    renderWateringCanChoices();
    const rewardText = levelUp.rewardText || LEVEL_REWARDS[levelUp.newLevel];
    if (rewardText) enqueuePopup('level', { level: levelUp.newLevel, rewardText });
}

function applyServerGameResponse(result, { refreshSlotName = null } = {}) {
    if (!result?.success) return false;

    if (result.slotName && result.slotData) {
        slotData[result.slotName] = result.slotData;
    }
    if (result.updatedSlots) {
        Object.assign(slotData, result.updatedSlots);
    }
    if (result.slotData && typeof result.slotData === 'object' && !result.slotName && !result.updatedSlots) {
        Object.assign(slotData, result.slotData);
    }
    if (result.currentLevel) {
        currentLevel = result.currentLevel;
        localStorage.setItem(`currentLevel_${currentUser}`, String(currentLevel));
        updateLevelCircle(currentLevel);
        applyUnlocksForLevel(currentLevel);
        checkAndUnlockPots();
        checkAndUnlockWateringCans();
        renderPotChoices();
        renderFlowerChoices();
        renderWateringCanChoices();
        checkAchievement_level(currentLevel);
    }

    if (result.levelUp) {
        const rewardText = result.levelUp.rewardText || LEVEL_REWARDS[result.levelUp.newLevel];
        if (rewardText) {
            enqueuePopup('level', { level: result.levelUp.newLevel, rewardText });
        }
    }

    applyServerAchievements(result.newAchievements);

    if (refreshSlotName) {
        refreshPlantVisual(refreshSlotName);
        if (zoomedSlot?.name === refreshSlotName) {
            const data = slotData[refreshSlotName];
            updateZoomPlantVisual(data);
            updateDiseaseInfo(data);
            showFixAdvice(data);
            setZoomControlsForPlantState(data);
            updateZoomStageLabel(data);
            updateNextWateringTimer(data);
            updateGrowthTimer(data);
        }
    }

    return true;
}

function handleServerGameEvents(result, slotName) {
    const data = slotData[slotName];
    const plant = data?.plant ? PLANTS[data.plant] : null;

    (result.events || []).forEach((event) => {
        switch (event.type) {
            case 'overwater_warning':
                showNotification(
                    `Слишком рано! Лучше поливать через ${formatWaitDuration(event.waitMs || 0)} Растение может заболеть.`,
                    false,
                    { warning: true }
                );
                break;
            case 'watered':
                if (event.onTime) showWateringDoneNotification(plant);
                else showNotification(`💧 ${plant?.name || 'Растение'} полито!`, false);
                break;
            case 'disease':
                if (event.diseaseType) showDiseaseAdvice(event.diseaseType);
                break;
            case 'death':
                showPlantDeathNotification(data, event.cause);
                break;
            case 'sprout':
                showNotification(`🌱 ${plant?.name || 'Растение'} дало росток!`, false);
                break;
            case 'bloom':
                showBloomDoneNotification(plant);
                break;
            case 'bloom_blocked':
                notifyBloomBlockedOnce(data, event.reason);
                break;
            case 'healed':
                if (event.fromLocation) showPositiveTip('goodLocation');
                else showPositiveTip('recovered');
                break;
            default:
                break;
        }
    });
}

async function loadQuestsFromServer() {
    if (!currentUser) return false;
    try {
        const response = await fetch(`${API_BASE_URL}/game/quests/progress`, {
            method: 'GET',
            headers: getAuthHeaders(),
            credentials: 'include'
        });
        const data = await response.json();
        if (!data.success) return false;

        serverQuests = data.quests || [];
        serverQuestLevel = data.level || currentLevel;
        serverQuestsAllCompleted = !!data.allCompleted;

        if (serverQuestLevel !== currentLevel) {
            currentLevel = serverQuestLevel;
            localStorage.setItem(`currentLevel_${currentUser}`, String(currentLevel));
            updateLevelCircle(currentLevel);
            applyUnlocksForLevel(currentLevel);
            checkAndUnlockPots();
            checkAndUnlockWateringCans();
            renderPotChoices();
            renderFlowerChoices();
            renderWateringCanChoices();
            checkAchievement_level(currentLevel);
        }

        renderQuests();
        return true;
    } catch (error) {
        console.error('Ошибка загрузки заданий:', error);
        return false;
    }
}

async function syncGameTick(slotNames = null) {
    if (!currentUser) return null;
    try {
        const result = await postGameAction('tick', slotNames ? { slotNames } : {});
        if (!result.success) return result;

        applyServerGameResponse(result);

        Object.keys(result.updatedSlots || {}).forEach((slotName) => {
            handleServerGameEvents(result, slotName);
            refreshPlantVisual(slotName);
        });

        await loadQuestsFromServer();

        return result;
    } catch (error) {
        console.error('Ошибка tick на сервере:', error);
        return null;
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

function escapePlantDescHtml(text) {
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function splitCharacterAndAdvice(tipsArray) {
    if (!Array.isArray(tipsArray) || !tipsArray.length) {
        return { characterBody: '', advice: [] };
    }
    const cleaned = normalizeTipsLines(tipsArray);
    if (cleaned.length === 1 && !cleaned[0].includes('?')) {
        return { characterBody: cleaned[0], advice: [] };
    }
    if (cleaned.length > 1 && !cleaned[0].includes('?')) {
        return { characterBody: cleaned[0], advice: cleaned.slice(1) };
    }
    return { characterBody: '', advice: cleaned };
}

function getPlantTipsArray(plant) {
    if (Array.isArray(plant.tips_array) && plant.tips_array.length) {
        return normalizeTipsLines(plant.tips_array);
    }
    if (typeof plant.tips === 'string' && plant.tips.trim()) {
        return normalizeTipsLines(plant.tips);
    }
    return [];
}

function getPlantAdviceItems(plant) {
    if (Array.isArray(plant.advice_list) && plant.advice_list.length) {
        return normalizeTipsLines(plant.advice_list);
    }
    const { advice } = splitCharacterAndAdvice(getPlantTipsArray(plant));
    return normalizeTipsLines(advice);
}

function parseSymptomEntries(text) {
    if (!text) return [];
    return text.split('|').map((entry) => entry.trim()).filter(Boolean);
}

function parsePlantFeatureBlocks(text) {
    const value = String(text || '').trim();
    if (!value.startsWith('FEATURES||')) return [];
    return value.slice('FEATURES||'.length).split('||').map((block) => {
        const idx = block.indexOf('::');
        if (idx === -1) return null;
        return {
            title: block.slice(0, idx).trim(),
            text: block.slice(idx + 2).trim()
        };
    }).filter(Boolean);
}

function renderPlantDescExtraFeatures(blocks) {
    if (!plantDescExtraFeatures) return;
    if (!blocks.length) {
        plantDescExtraFeatures.innerHTML = '';
        plantDescExtraFeatures.style.display = 'none';
        return;
    }
    plantDescExtraFeatures.style.display = '';
    plantDescExtraFeatures.innerHTML = blocks.map((block) => (
        `<div class="desc-subsection plant-desc-feature-block">`
        + `<p class="desc-point-title">${escapePlantDescHtml(block.title)}:</p>`
        + `<p class="desc-point-text">${escapePlantDescHtml(block.text)}</p>`
        + `</div>`
    )).join('');
}

function getPlantDescriptionText(plant) {
    const plantId = resolveSpeciesId(plant?.id, plant);
    const extras = PLANT_CATALOG_EXTRAS[plantId];
    if (extras?.description) return extras.description;

    let text = (plant.description || plant.fullDescription || '').trim();
    if (!text) return 'Описание отсутствует';

    const charTailPatterns = [
        /\s*Спатифилл(?:лю|)м\s+очень\s+чувствителен[\s\S]*$/i,
        /\s*Кактус\s+может\s+простить[\s\S]*$/i
    ];
    for (const pattern of charTailPatterns) {
        const match = text.match(pattern);
        if (match) {
            text = text.slice(0, match.index).trim();
            break;
        }
    }

    const charBody = (plant.character_description || '').trim();
    if (charBody && text.includes(charBody)) {
        text = text.replace(charBody, '').trim();
    }

    return text.replace(/\s{2,}/g, ' ').trim() || 'Описание отсутствует';
}

function renderPlantDescCharacter(plant) {
    if (!plantDescCharacterSection) return;
    const trait = (plant.character_trait || '').trim();
    const { characterBody } = splitCharacterAndAdvice(getPlantTipsArray(plant));
    const body = (plant.character_description || characterBody || '').trim();

    if (plantDescCharacterTitle) {
        plantDescCharacterTitle.textContent = trait ? `Характер — ${trait}:` : 'Характер:';
    }

    if (!trait && !body) {
        plantDescCharacterSection.style.display = 'none';
        if (plantDescCharacter) plantDescCharacter.textContent = '';
        return;
    }

    plantDescCharacterSection.style.display = '';
    if (plantDescCharacter) plantDescCharacter.textContent = body;
}

function renderPlantDescNeeds(plant) {
    const water = plant.watering_advice || plant.waterAdvice || '';
    const light = plant.light_advice || plant.lightAdvice || '';
    if (plantDescWater) plantDescWater.textContent = water || '—';
    if (plantDescLight) plantDescLight.textContent = light || '—';
    if (plantDescNeedsSection) {
        plantDescNeedsSection.style.display = (water || light) ? '' : 'none';
    }
}

function renderPlantDescSymptoms(entries) {
    if (!plantDescSymptoms || !plantDescSymptomsBlock) return;
    if (!entries.length) {
        plantDescSymptomsBlock.style.display = 'none';
        plantDescSymptoms.innerHTML = '';
        return;
    }
    plantDescSymptomsBlock.style.display = '';
    plantDescSymptoms.innerHTML = entries.map((entry) => {
        const colonIdx = entry.indexOf(':');
        if (colonIdx === -1) return `<li>${escapePlantDescHtml(entry)}</li>`;
        const title = entry.slice(0, colonIdx).trim();
        const detail = entry.slice(colonIdx + 1).trim();
        return `<li><span class="plant-desc-symptom-title">${escapePlantDescHtml(title)}:</span> ${escapePlantDescHtml(detail)}</li>`;
    }).join('');
}

function parseInlineNumberedFlowering(value) {
    const numberedStart = value.search(/\s1[.)]\s/i);
    if (numberedStart === -1) return null;

    const intro = value.slice(0, numberedStart).trim();
    const body = value.slice(numberedStart).trim();
    const segments = body.split(/\s*(?=\d+[.)]\s*)/).filter(Boolean);
    if (segments.length < 2) return null;

    const items = [];
    let footer = '';

    segments.forEach((segment, index) => {
        let item = segment.replace(/^\d+[.)]\s*/, '').trim().replace(/,\s*$/, '');
        if (index === segments.length - 1) {
            const footerMatch = item.match(/^(.+?\.\s*)(.+)$/);
            if (footerMatch && footerMatch[2].length > 20) {
                item = footerMatch[1].trim();
                footer = footerMatch[2].trim();
            }
        }
        if (item) items.push(item);
    });

    return items.length >= 2 ? { intro, items, footer } : null;
}

function parseFloweringContent(text) {
    const value = String(text || '').replace(/\\n/g, '\n').trim();
    if (!value) return null;

    if (value.includes('|')) {
        const parts = value.split('|').map((part) => part.trim()).filter(Boolean);
        if (parts.length >= 4 && !parts[0].includes(':') && parts[1].includes(':')) {
            return {
                prefix: parts[0],
                intro: parts[1],
                items: parts.slice(2),
                footer: ''
            };
        }
        if (parts.length >= 4 && parts[0].includes(':')) {
            return {
                intro: parts[0],
                items: parts.slice(1, -1),
                footer: parts[parts.length - 1]
            };
        }
        if (parts.length >= 3 && parts[0].includes(':')) {
            return { intro: parts[0], items: parts.slice(1), footer: '' };
        }
    }

    const lines = value.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
    if (lines.length > 1) {
        const intro = lines[0];
        const items = [];
        let footer = '';

        for (let i = 1; i < lines.length; i++) {
            const line = lines[i];
            const isBullet = /^[•\-–—]/.test(line) || /^\d+[.)]\s/.test(line);
            if (isBullet) {
                items.push(line.replace(/^(?:•|[\-–—]|\d+[.)])\s*/, '').trim());
                continue;
            }
            if (items.length) {
                footer = footer ? `${footer} ${line}` : line;
            }
        }

        if (items.length) {
            return { intro, items, footer };
        }
    }

    const inline = parseInlineNumberedFlowering(value);
    if (inline) return inline;

    return { intro: '', items: [], footer: '', plain: value };
}

function renderPlantDescFlowering(text) {
    if (!plantDescFlowering || !plantDescFloweringBlock) return;
    if (parsePlantFeatureBlocks(text).length) {
        plantDescFloweringBlock.style.display = 'none';
        plantDescFlowering.innerHTML = '';
        return;
    }
    const parsed = parseFloweringContent(text);
    if (!parsed) {
        plantDescFloweringBlock.style.display = 'none';
        plantDescFlowering.innerHTML = '';
        return;
    }

    plantDescFloweringBlock.style.display = '';

    if (parsed.plain) {
        plantDescFlowering.innerHTML = `<p class="plant-desc-flowering-plain">${escapePlantDescHtml(parsed.plain)}</p>`;
        return;
    }

    let html = '';
    if (parsed.prefix) {
        html += `<p class="plant-desc-flowering-prefix">${escapePlantDescHtml(parsed.prefix)}</p>`;
    }
    if (parsed.intro) {
        html += `<p class="plant-desc-flowering-intro">${escapePlantDescHtml(parsed.intro)}</p>`;
    }
    if (parsed.items.length) {
        html += `<ol class="plant-desc-numbered-list">${parsed.items.map((item) => `<li>${escapePlantDescHtml(item)}</li>`).join('')}</ol>`;
    }
    if (parsed.footer) {
        html += `<p class="plant-desc-flowering-footer">${escapePlantDescHtml(parsed.footer)}</p>`;
    }
    plantDescFlowering.innerHTML = html;
}

function renderPlantDescAdvice(plant) {
    if (!plantDescAdvice || !plantDescAdviceSection) return;
    const items = getPlantAdviceItems(plant);
    if (!items.length) {
        plantDescAdviceSection.style.display = 'none';
        plantDescAdvice.innerHTML = '';
        return;
    }
    plantDescAdviceSection.style.display = '';
    plantDescAdvice.innerHTML = items.map((item) => `<li>${escapePlantDescHtml(item)}</li>`).join('');
}

function renderPlantDescFeatures(plant) {
    const symptoms = parseSymptomEntries(plant.why_disease);
    const featureBlocks = parsePlantFeatureBlocks(plant.flowering_conditions);
    renderPlantDescSymptoms(symptoms);
    renderPlantDescExtraFeatures(featureBlocks);
    renderPlantDescFlowering(plant.flowering_conditions);
    if (plantDescFeaturesSection) {
        const hasFlowering = !!(plant.flowering_conditions || '').trim() && !featureBlocks.length;
        const hasFeatures = symptoms.length > 0 || featureBlocks.length > 0 || hasFlowering;
        plantDescFeaturesSection.style.display = hasFeatures ? '' : 'none';
    }
}

function getPlantDescIcon(name) {
    const normalized = (name || '').toLowerCase();
    if (normalized.includes('спатиф')) return '🌸';
    if (normalized.includes('кактус')) return '🌵';
    if (normalized.includes('фикус')) return '🌳';
    return '🌿';
}

async function markDescriptionQuestDone() {
    if (!currentUser || localStorage.getItem(`readDescriptionDone_${currentUser}`)) return;
    localStorage.setItem(`readDescriptionDone_${currentUser}`, '1');
    try {
        const result = await postGameAction('read_description');
        applyServerGameResponse(result);
        applyServerLevelUp(result.levelUp);
        await loadQuestsFromServer();
        renderQuests();
    } catch (error) {
        console.error('Ошибка отметки прочтения описания:', error);
    }
}

function resolvePlantForDescription(plantKey) {
    let plant = PLANTS[plantKey];
    if (plant) return plant;
    const numericKey = parseInt(plantKey, 10);
    if (Number.isFinite(numericKey)) {
        plant = PLANTS[numericKey];
        if (plant) return plant;
        return Object.values(PLANTS).find((entry) => Number(entry.id) === numericKey) || null;
    }
    return null;
}

async function openPlantDescription(plantKey) {
    let plant = resolvePlantForDescription(plantKey);
    if (!plant) {
        await loadPlantsCatalog();
        plant = resolvePlantForDescription(plantKey);
    }
    if (!plant) {
        showNotification('Ошибка: данные о растении не найдены', true);
        return;
    }

    if (plantDescIcon) plantDescIcon.textContent = getPlantDescIcon(plant.name);
    if (plantDescTitle) {
        plantDescTitle.textContent = plant.nickname ? `${plant.name} - ${plant.nickname}` : plant.name;
    }
    if (plantDescDescription) plantDescDescription.textContent = getPlantDescriptionText(plant);
    renderPlantDescCharacter(plant);
    renderPlantDescNeeds(plant);
    renderPlantDescFeatures(plant);
    renderPlantDescAdvice(plant);

    const scrollEl = modalPlantDescription?.querySelector('.plant-desc-text-wrapper');
    if (scrollEl) scrollEl.scrollTop = 0;
    openModal(modalPlantDescription);
    markDescriptionQuestDone();
}

function closePlantDescription() {
    closeModal(modalPlantDescription);
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
                checkAchievement_level(currentLevel);
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
                    renderSlot(slot, slotData[name]);
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

const DAY_MS = 24 * 60 * 60 * 1000;

const PLANT_GROWTH_DAYS = {
    1: { seedToSprout: 1, plantToBloom: 7 },
    2: { seedToSprout: 4, plantToBloom: 21 },
    3: { seedToSprout: 2, plantToBloom: 14 }
};

const GROWTH_TIMING_TEST = false;

const PLANT_WATER_INTERVALS_DAYS = {
    1: { min: 1, max: 2 },
    2: { min: 7, max: 10 },
    3: { min: 3, max: 4 }
};

const WATER_TIMING_TEST = false;

const OVERWATER_MIN_FAST_POLIVS = 2;
const OVERWATER_DEATH_MIN_FAST_POLIVS = 3;

const PLANT_SICK_UNTIL_DEATH_DAYS = {
    1: 3,
    2: 7,
    3: 5
};

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
        requirement: 'Достигнуть 6 уровня в игре'
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

function plantGrowthDays(plant) {
    const speciesId = resolveSpeciesId(plant?.id, plant);
    return PLANT_GROWTH_DAYS[speciesId] || PLANT_GROWTH_DAYS[1];
}

function getSeedlingMs(plant) {
    if (GROWTH_TIMING_TEST) return TEST_SEEDLING_MS;
    return plantGrowthDays(plant).seedToSprout * DAY_MS;
}

function getBloomMs(plant) {
    if (GROWTH_TIMING_TEST) return TEST_BLOOM_MS;
    return plantGrowthDays(plant).plantToBloom * DAY_MS;
}

function plantSickUntilDeathDays(plant) {
    const speciesId = resolveSpeciesId(plant?.id, plant);
    return PLANT_SICK_UNTIL_DEATH_DAYS[speciesId] ?? PLANT_SICK_UNTIL_DEATH_DAYS[1];
}

function getSickUntilDeathMs(plant) {
    if (WATER_TIMING_TEST) return 45 * 1000;
    return plantSickUntilDeathDays(plant) * DAY_MS;
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

const PLANT_CATALOG_EXTRAS = {
    1: {
        description: 'Нежный тропический гость с темно-зелеными листьями и изящными белыми цветами, напоминающими флаги. Говорят, он приносит в дом гармонию.',
        character_description: 'Спатифиллум очень чувствителен к переменам. Он не прощает грубых ошибок (сквозняков, пересыхания корней), но при этом "кричит" о своих проблемах громче всех. Будь внимательным, ухаживать за ним проще всего.',
        why_disease: 'Сохнут кончики листьев: Слишком сухой воздух или недостаточный полив.|Листья желтеют: Перелив или солнечный ожог.|Листья чернеют: Перелив, холод или неправильно подобранный грунт.|Не цветет: Слишком темное место, большой горшок или нехватка питательных веществ.'
    },
    2: {
        description: 'Пухлый зеленый шар с выраженными ребрами и крепкими колючками. В дикой природе выживает в самых суровых условиях пустыни. В награду за правильный уход дарит ослепительно красивые цветы.',
        character_description: 'Кактус может простить вашу забывчивость. Лучшее, что вы можете сделать для кактуса - иногда оставить его в покое. Он не требует ежедневного внимания, но обожает солнце.',
        why_disease: 'Мягкий и сморщенный стебель: Признак обезвоживания или, чаще, гниения корней из-за перелива.|Желтые или коричневые пятна: Свидетельствуют о солнечном ожоге или грибковом заболевании из-за высокой влажности.|Черные сухие пятна и потеря колючек: Признак черной гнили, поражающей растение при неправильном поливе или инфекции.|Вытягивание и бледность стебля: Растению не хватает света.|Отсутствие роста и цветения: Причина в нарушении периода покоя (зимовки) или нехватке света, полива и питательных веществ.',
        flowering_conditions: 'Цветок появляется на макушке и живет недолго, что создает элемент коллекционирования.|Кактус цветет только при соблюдении трех условий:|Яркий свет|Период "зимней спячки" (снижение полива до минимума)|Достижение зрелого возраста'
    },
    3: {
        description: 'Величественное дерево в миниатюре с плотными, блестящими листьями. Символ стабильности и уюта. В правильных условиях растет очень быстро, радуя глаз новой зеленью. Будет требовать последовательности и предсказуемости.',
        character_description: 'Фикус растет медленно, но верно. Он не любит, когда его тревожат (переставляют с места на место). Если создать ему стабильные условия, он будет расти большим и красивым.',
        why_disease: 'Опадание листьев (листопад): Резкая смена места, сквозняк, перепад температур, недостаток света или стресс.|Желтеют листья: Перелив (корни загнивают) или, наоборот, пересушивание земляного кома.|Пятна на листьях: Коричневые/ржавые пятна: Часто свидетельствуют о солнечном ожоге или избытке удобрений.|Сухие кончики: Недостаточная влажность воздуха, слишком сухо в помещении.|Увядание и поникшие листья: Корневая гниль из-за перелива — корни не дышат и не впитывают воду.|Появление вредителей: Белый рыхлый налет (мучнистый червец) или темный налет.|Новые листья не появляются или мелкие: Недостаток питания.',
        flowering_conditions: 'FEATURES||Стресс от перемещения::Если игрок меняет локацию для фикуса, он впадает в шок на 1-2 игровых дня: начинает сбрасывать листья, даже если полив идеален. Это учит игрока планировать расположение сада.||Рост::Фикус дает новые листья из верхушки. Визуально это выглядит как разворачивающийся красноватый "чехольчик", что создает приятный эффект прогресса.'
    }
};

function mergePlantCatalogExtras(plants) {
    Object.entries(PLANT_CATALOG_EXTRAS).forEach(([id, extras]) => {
        const numericId = Number(id);
        const plant = plants[id] || plants[numericId]
            || Object.values(plants).find((entry) => Number(entry.id) === numericId);
        if (!plant) return;
        if (extras.description) {
            plant.description = extras.description;
            plant.fullDescription = extras.description;
        }
        if (extras.character_description) {
            plant.character_description = extras.character_description;
        }
        if (extras.flowering_conditions) {
            plant.flowering_conditions = extras.flowering_conditions;
        }
        if (extras.why_disease) {
            plant.why_disease = extras.why_disease;
        }
    });
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

                const intervals = PLANT_WATER_INTERVALS_DAYS[sid] || { min: 1, max: 2 };
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
                    waterIntervalMin: plant.water_interval_min ?? intervals.min,
                    waterIntervalMax: plant.water_interval_max ?? intervals.max,
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
            mergePlantCatalogExtras(plants);
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

const ZOOM_STAGE_LABEL = {
    seed: '🌰 Семечко посажено',
    sprout: '🌱 Росток',
    bloom: '🌸 Расцвёл',
    sick: '🤒 Болеет',
    dead: '💀 Умерло'
};

const PLANT_SICK_LABEL = 'Болеет';
const PLANT_DEAD_LABEL = 'Умерло';
const ZOOM_DISEASE_DEAD_TEXT = 'Растение погибло. Выбросите горшок, чтобы посадить новое.';

function getZoomStageLabel(data) {
    if (!data?.plant) return '';
    if (isPlantDead(data)) return ZOOM_STAGE_LABEL.dead;
    if (data.hasDisease) return ZOOM_STAGE_LABEL.sick;
    const stage = resolvePlantStage(data);
    if (stage === 0) return ZOOM_STAGE_LABEL.seed;
    if (stage === 1) return ZOOM_STAGE_LABEL.sprout;
    if (stage >= 2) return ZOOM_STAGE_LABEL.bloom;
    return ZOOM_STAGE_LABEL.seed;
}

function updateZoomStageLabel(data) {
    const el = document.getElementById('zoomStageLabel');
    if (!el) return;
    if (!data?.plant) {
        el.textContent = 'Посади цветок!';
        return;
    }
    el.textContent = getZoomStageLabel(data);
}

function getWaterTimerLabel(data, plant) {
    if (!data || !plant || isPlantDead(data)) return null;

    if (!data.lastWateredAt) {
        return '🌱 Нужен первый полив';
    }

    const minMs = getWaterMinMs(plant);
    const maxMs = getWaterMaxMs(plant);
    const sinceMs = msSinceLastWater(data);

    if (sinceMs < minMs) {
        return `💧 Полив через ${formatWaitDuration(minMs - sinceMs)}`;
    }
    if (sinceMs <= maxMs) {
        return '⏰ Пора поливать!';
    }
    return '⚠️ Срочно полей!';
}

function getDiseaseBlockText(data) {
    if (!data?.plant) return null;
    if (isPlantDead(data)) return ZOOM_DISEASE_DEAD_TEXT;
    if (data.hasDisease && data.disease && data.disease !== '__dead__') {
        return data.disease;
    }
    return null;
}

function getGrowthTimerLabel(data) {
    if (!data?.plant || !data.plantedAt || isPlantDead(data) || data.stage >= 2) {
        return null;
    }
    if (data.hasDisease && data.stage === 1) {
        return null;
    }

    const plant = PLANTS[data.plant];
    if (!plant) return null;

    const msSincePlanted = Date.now() - data.plantedAt;

    if (data.stage === 0) {
        if (!data.lastWateredAt) {
            return null;
        }
        const msLeft = Math.max(0, getSeedlingMs(plant) - msSincePlanted);
        if (msLeft > 0) {
            if (GROWTH_TIMING_TEST) {
                return `🌱 Росток через ${Math.ceil(msLeft / 1000)} сек.`;
            }
            return `🌱 Росток через ${formatWaitDuration(msLeft)}`;
        }
        return '🌱 Росток скоро появится...';
    }
    if (data.stage === 1) {
        const msLeft = Math.max(0, getBloomMs(plant) - msSincePlanted);
        if (msLeft <= 0) return null;
        if (GROWTH_TIMING_TEST) {
            return `🌸 Цветение через ${Math.ceil(msLeft / 1000)} сек.`;
        }
        return `🌸 Цветение через ${formatWaitDuration(msLeft)}`;
    }
    return null;
}

const LEVEL_REWARDS = {
    2: '🎉 Уровень 2! Горшок «С рисунком» теперь доступен!',
    3: '🎉 Уровень 3! Кактус теперь доступен для посадки!',
    4: '🎉 Уровень 4! Лейка «Розовая» теперь доступна!',
    5: '🎉 Уровень 5! Фикус теперь доступен для посадки!',
    6: '🎉 Уровень 6! Горшок «Большой» теперь доступен!'
};

const slotData = {};
let activeSlot = null;
let zoomedSlot = null;
let zoomTimerTickId = null;

const popupQueue = [];
let popupShowing = false;

const slots = document.querySelectorAll('.pot-slot');
const modalPlacePot = document.getElementById('modalPlacePot');
const modalPickFlower = document.getElementById('modalPickFlower');
const zoomOverlay = document.getElementById('zoomOverlay');
const modalAchievements = document.getElementById('modalAchievements');
const tutorialOverlay = document.getElementById('tutorialOverlay');
const modalWaterCan = document.getElementById('modalWaterCan');
const modalRepot = document.getElementById('modalRepot');
const modalMovePlant = document.getElementById('modalMovePlant');
const modalPlantDescription = document.getElementById('modalPlantDescription');
const closePlantDescBtn = document.getElementById('closePlantDescBtn');
const plantDescIcon = document.getElementById('plantDescIcon');
const plantDescTitle = document.getElementById('plantDescTitle');
const plantDescDescription = document.getElementById('plantDescDescription');
const plantDescCharacter = document.getElementById('plantDescCharacter');
const plantDescCharacterTitle = document.getElementById('plantDescCharacterTitle');
const plantDescCharacterSection = document.getElementById('plantDescCharacterSection');
const plantDescWater = document.getElementById('plantDescWater');
const plantDescLight = document.getElementById('plantDescLight');
const plantDescSymptoms = document.getElementById('plantDescSymptoms');
const plantDescSymptomsBlock = document.getElementById('plantDescSymptomsBlock');
const plantDescExtraFeatures = document.getElementById('plantDescExtraFeatures');
const plantDescFlowering = document.getElementById('plantDescFlowering');
const plantDescFloweringBlock = document.getElementById('plantDescFloweringBlock');
const plantDescFeaturesSection = document.getElementById('plantDescFeaturesSection');
const plantDescAdvice = document.getElementById('plantDescAdvice');
const plantDescAdviceSection = document.getElementById('plantDescAdviceSection');
const plantDescNeedsSection = document.getElementById('plantDescNeedsSection');
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

function formatDaysRu(n) {
    const mod10 = n % 10;
    const mod100 = n % 100;
    if (mod10 === 1 && mod100 !== 11) return `${n} день`;
    if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return `${n} дня`;
    return `${n} дней`;
}

function getSeedlingWaitLabel(plant) {
    return formatDaysRu(plantGrowthDays(plant).seedToSprout);
}

function showNotification(message, isError = false, options = {}) {
    const stack = document.getElementById('notificationStack');
    if (!stack) return;

    const isWarning = !!options.warning;
    const isInfo = !!options.info;
    const id = ++notificationIdSeq;
    const el = document.createElement('div');
    el.className = `notification-item light-notification${isError ? ' is-error' : ''}${isWarning ? ' is-warning' : ''}${isInfo ? ' is-info' : ''}`;
    el.dataset.notifId = String(id);
    const icon = isError ? '❌' : (isWarning ? '⚠️' : (isInfo ? 'ℹ️' : '✅'));
    el.innerHTML = `
        <span class="notif-icon">${icon}</span>
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
    if (el === modalAchievements) hideAchievementReasonToast();
}

function closeZoomOverlay() {
    closeModal(zoomOverlay);
    if (devStatePanel) devStatePanel.style.display = 'none';
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
let achievementReasonToastTimer = null;

function hideAchievementReasonToast() {
    const toast = document.getElementById('achievementToast');
    if (achievementReasonToastTimer) {
        clearTimeout(achievementReasonToastTimer);
        achievementReasonToastTimer = null;
    }
    if (toast) toast.classList.remove('show');
}

function showAchievementReasonToast(achievementId) {
    const config = ACHIEVEMENTS_CONFIG[achievementId];
    if (!config) return;

    const unlocked = localStorage.getItem(`achievement_unlocked_${currentUser}_${achievementId}`) === 'true';
    if (!unlocked) return;

    const toast = document.getElementById('achievementToast');
    const toastImg = document.getElementById('achievementToastImg');
    if (!toast || !toastImg) return;

    hideAchievementReasonToast();

    toastImg.src = config.reasonImage;
    toast.classList.add('show');

    achievementReasonToastTimer = setTimeout(() => {
        toast.classList.remove('show');
        achievementReasonToastTimer = null;
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

async function recordMistakeToServer(plantId, mistakeType, { countForAchievement = true } = {}) {
    if (!currentUser) return;
    try {
        await fetch(`${API_BASE_URL}/achievements/event`, {
            method: 'POST',
            credentials: 'include',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                event: 'mistake',
                plant_id: String(plantId),
                mistake_type: mistakeType,
                count_for_achievement: countForAchievement
            })
        });
    } catch (e) {
        console.error('Ошибка записи ошибки на сервер:', e);
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
            'first_wither': 'all_lost',
            'first_negative_effect': 'oops_error',
            'grow_all_species': 'collector',
            'daily_streak': 'patient_gardener',
            'reach_level': 'flora_guard'
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

function checkAchievement_caringParent() {
    return false;
}

function checkAchievement_collector() {
    return false;
}

function checkAchievement_level(level) {
    if (level >= 6) {
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

function checkAchievement_streak() {
    return false;
}

function checkAchievement_death() {
    return false;
}

function checkAchievement_negativeEffect() {
    return false;
}

function checkAllAchievementsOnBloom() {
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
        too_light: '🍃 Листья желтеют — солнечный ожог',
        big_pot: '🍃 Не цветёт — слишком большой горшок',
        under_watered: '🍃 Сохнут кончики листьев — недостаточный полив',
        overwatered: '🍃 Листья желтеют — перелив'
    },
    2: {
        too_dark: '🌵 Вытягивание и бледность стебля — не хватает света',
        no_flower: '🌵 Нет цветения — причина в нехватке света',
        under_watered: '🌵 Сморщенный стебель — недостаточный полив',
        overwatered: '🌵 Сморщенный стебель — перелив или застой воды'
    },
    3: {
        too_light: '🍂 Пятна на листьях — солнечный ожог',
        under_watered: '🍂 Желтеют листья — недостаточный полив',
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
        under_watered: 'Пить хочется... Твой цветок показывает, что пора поливать. Не жди, пока земля превратится в пыль. Одна лейка - и он снова весёлый! 💧',
        too_light: 'Кажется, твоему другу не нравится его место. Попробуй переставить горшок туда, где потемнее. Свет - это важно! ☀️',
        too_dark: 'Кажется, твоему другу не нравится его место. Попробуй переставить горшок туда, где светлее. Свет - это важно! ☀️',
        big_pot: 'Слишком большой горшок мешает зацвести. Пересади в горшок поменьше - цветку будет уютнее! 🪴',
        no_flower: 'Кажется, твоему другу не нравится его место. Попробуй переставить горшок туда, где светлее. Свет - это важно! ☀️'
    },
    death: {
        first: 'Ничего страшного! Даже у настоящих садоводов бывает. Посади новый цветок - он будет рад тебя видеть. А я подскажу, как не повторить ту же ошибку. 💚',
        overwatered: 'Бедняга утонул... В следующий раз проверяй землю: если влажная - лейку в сторону. Попробуем ещё?',
        under_watered: 'Он ждал воды слишком долго... Поставь напоминание в телефоне или просто заглядывай почаще. Ты справишься!',
        too_light: 'Жара сделала своё дело. Но теперь ты знаешь: каждому цветку нужно своё место. Давай посадим новый?',
        too_dark: 'Тень сделала своё дело. Но теперь ты знаешь: каждому цветку нужно своё место. Давай посадим новый?',
        complex: 'Бывает. Не кори себя. Просто начни заново - твой сад никуда не денется. А я всегда рядом с советами. 🌸'
    },
    positive: {
        idealWater: 'Идеально! Ты чувствуешь своего зелёного друга. Так держать!',
        recovered: 'Ура! Снова здоров. Ты быстро научился понимать его сигналы. Горжусь тобой!',
        bloomed: 'Смотри-ка, цветок! Это значит, ты делаешь всё правильно. Красота. 🥰',
        goodLocation: 'Ты выбрал правильное место! Цветочку тут комфортно.'
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
    if (!text) return false;
    if (getPositiveTipsTodayCount() >= POSITIVE_TIP_DAILY_LIMIT) return false;
    showNotification(text, false);
    bumpPositiveTipsTodayCount();
    return true;
}

function getLastEventNotifType(eventKey) {
    if (!currentUser) return null;
    const key = `${eventKey}Notif_${currentUser}_${new Date().toDateString()}`;
    const value = localStorage.getItem(key);
    if (value === 'positive') return 'positive';
    if (value === 'routine' || value === 'watered') return 'routine';
    return null;
}

function setLastEventNotifType(eventKey, type) {
    if (!currentUser) return;
    const key = `${eventKey}Notif_${currentUser}_${new Date().toDateString()}`;
    localStorage.setItem(key, type);
}

function showAlternatingPositiveNotification({ eventKey, tipKey, routineMessage }) {
    const lastType = getLastEventNotifType(eventKey);
    const mayShowPositive = lastType !== 'positive'
        && getPositiveTipsTodayCount() < POSITIVE_TIP_DAILY_LIMIT;

    if (mayShowPositive && showPositiveTip(tipKey)) {
        setLastEventNotifType(eventKey, 'positive');
        return;
    }

    showNotification(routineMessage, false);
    setLastEventNotifType(eventKey, 'routine');
}

function showWateringDoneNotification(plant) {
    const plantName = plant?.name || 'Растение';
    showAlternatingPositiveNotification({
        eventKey: 'watering',
        tipKey: 'idealWater',
        routineMessage: `💧 ${plantName} полито!`
    });
}

function showBloomDoneNotification(plant) {
    const plantName = plant?.name || 'Растение';
    showAlternatingPositiveNotification({
        eventKey: 'bloom',
        tipKey: 'bloomed',
        routineMessage: `🌸 ${plantName} зацвёл!`
    });
}

function showDiseaseAdvice(diseaseType) {
    const text = NOTIFICATION_TEXTS.disease[diseaseType];
    if (!text) return;
    showNotification(text, false, { info: true });
}

function resolveDeathCauseType(data) {
    if (!data) return null;
    if (data.diseaseType && data.diseaseType !== 'dead') return data.diseaseType;
    const plantKey = resolveSpeciesId(data.plant, PLANTS[data.plant]);
    return getDiseaseTypeFromMessage(plantKey, data.disease);
}

function showPlantDeathNotification(data, notificationCause = null) {
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
        const cause = notificationCause || resolveDeathCauseType(data);
        if (cause === 'overwatered') text = NOTIFICATION_TEXTS.death.overwatered;
        else if (cause === 'under_watered') text = NOTIFICATION_TEXTS.death.under_watered;
        else if (cause === 'too_light') text = NOTIFICATION_TEXTS.death.too_light;
        else if (cause === 'too_dark' || cause === 'no_flower') text = NOTIFICATION_TEXTS.death.too_dark;
        else text = NOTIFICATION_TEXTS.death.complex;
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

function applyPlantDeath(slotName, data, { notificationCause = null } = {}) {
    if (!data?.plant || isPlantDead(data)) return false;

    data.hasDisease = true;
    data.hadMistakes = true;
    data.disease = '__dead__';
    data.diseaseType = 'dead';
    data.diseaseSource = 'neglect';
    data.devManualState = false;

    showPlantDeathNotification(data, notificationCause);

    saveState();

    refreshPlantVisual(slotName);
    if (zoomedSlot?.name === slotName) {
        updateZoomPlantVisual(data);
        updateZoomStageLabel(data);
        updateDiseaseInfo(data);
        setZoomControlsForPlantState(data);
        updateNextWateringTimer(data);
        updateGrowthTimer(data);
    }
    return true;
}

function checkPlantDeathFromSickness(slotName) {
    const data = slotData[slotName];
    if (!data?.plant || data.stage < 1) return;
    if (data.devManualState || isPlantDead(data)) return;
    if (!data.hasDisease) return;
    if (data.diseaseType === 'under_watered' || data.diseaseType === 'overwatered') return;
    if (!LOCATION_DISEASE_TYPES.includes(data.diseaseType)) return;

    const plant = PLANTS[data.plant];
    if (!plant) return;

    ensureDiseaseStartTime(data);
    if (Date.now() - data.diseaseStartTime < getSickUntilDeathMs(plant)) return;

    applyPlantDeath(slotName, data);
}

function scheduleSicknessDeathCheck(slotName) {
    syncGameTick([slotName]).catch(console.error);
    setTimeout(() => {
        const data = slotData[slotName];
        if (!data?.plant || isPlantDead(data)) return;
        if (data.hasDisease && !data.devManualState) {
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
    ['waterBtnLeft', 'repotBtnLeft', 'plantBtnLeft'].forEach((id) => {
        const btn = document.getElementById(id);
        if (!btn) return;
        btn.disabled = dead;
    });
    const moveBtn = document.getElementById('moveBtnLeft');
    if (moveBtn) moveBtn.disabled = false;
    const removeBtn = document.getElementById('removeBtnLeft');
    if (removeBtn) removeBtn.disabled = false;

    const growthTimerBox = document.getElementById('growthTimerBox');
    const waterTimerBox = document.getElementById('waterTimerBox');
    if (dead) {
        if (growthTimerBox) growthTimerBox.style.display = 'none';
        if (waterTimerBox) waterTimerBox.style.display = 'none';
    }
}

function formatWaitDuration(ms) {
    if (WATER_TIMING_TEST) {
        return `${Math.ceil(ms / 1000)} сек.`;
    }
    const days = Math.ceil(ms / DAY_MS);
    if (days >= 1) return formatDaysRu(days);
    return `${Math.ceil(ms / 3600000)} ч.`;
}

function plantWaterIntervalDays(plant) {
    const speciesId = resolveSpeciesId(plant?.id, plant);
    const fallback = PLANT_WATER_INTERVALS_DAYS[speciesId] || { min: 1, max: 2 };
    return {
        min: plant?.waterIntervalMin ?? fallback.min,
        max: plant?.waterIntervalMax ?? fallback.max
    };
}

function getWaterMinMs(plant) {
    if (WATER_TIMING_TEST) return TEST_WATER_MIN_MS;
    const { min } = plantWaterIntervalDays(plant);
    return min * DAY_MS;
}

function getWaterMaxMs(plant) {
    if (WATER_TIMING_TEST) return TEST_WATER_MAX_MS;
    const { max } = plantWaterIntervalDays(plant);
    return max * DAY_MS;
}

function msSinceLastWater(data) {
    if (!data?.lastWateredAt) return Infinity;
    return Date.now() - data.lastWateredAt;
}

function getMsWithoutWater(data, now = Date.now()) {
    if (!data?.plant) return 0;
    if (data.lastWateredAt) return Math.max(0, now - data.lastWateredAt);
    if (data.plantedAt) return Math.max(0, now - data.plantedAt);
    return 0;
}

function isWateringOnTime(data, plant, atTime = Date.now()) {
    const minMs = getWaterMinMs(plant);
    const maxMs = getWaterMaxMs(plant);
    if (!data.lastWateredAt) {
        const ageMs = atTime - (data.plantedAt || atTime);
        return ageMs <= maxMs;
    }
    const sinceMs = atTime - data.lastWateredAt;
    return sinceMs >= minMs && sinceMs <= maxMs;
}

function hasRegularWatering(data, plant) {
    if (!data?.lastWateredAt || !plant) return false;
    return msSinceLastWater(data) <= getWaterMaxMs(plant);
}

function wateringGapMs(entry) {
    if (!entry) return Infinity;
    if (entry.gapMs != null) return entry.gapMs;
    if (entry.intervalMs != null) return entry.intervalMs;
    return Infinity;
}

function countRecentFastWaterings(data, plant) {
    if (!data?.wateringHistory?.length) return 0;
    const minMs = getWaterMinMs(plant);
    return data.wateringHistory.slice(-3).filter(w => wateringGapMs(w) < minMs).length;
}

function hasOverwaterRisk(data, plant) {
    return countRecentFastWaterings(data, plant) >= OVERWATER_MIN_FAST_POLIVS;
}

function hasOverwaterDeathRisk(data, plant) {
    const recent = data?.wateringHistory?.slice(-OVERWATER_DEATH_MIN_FAST_POLIVS) || [];
    if (recent.length < OVERWATER_DEATH_MIN_FAST_POLIVS) return false;
    const minMs = getWaterMinMs(plant);
    return recent.every(w => wateringGapMs(w) < minMs);
}

function isStillWithinMinWaterInterval(data, plant) {
    if (!data?.lastWateredAt) return false;
    return msSinceLastWater(data) < getWaterMinMs(plant);
}

function shouldApplyOverwaterDisease(data, plant) {
    if (!hasOverwaterRisk(data, plant)) return false;
    return isStillWithinMinWaterInterval(data, plant);
}

function shouldApplyOverwaterDeath(data, plant) {
    if (!hasOverwaterDeathRisk(data, plant)) return false;
    return isStillWithinMinWaterInterval(data, plant);
}

function handleOverwaterEarlyWarning(data, plant, now = Date.now()) {
    const minMs = getWaterMinMs(plant);
    const sinceMs = data.lastWateredAt ? now - data.lastWateredAt : 0;
    const unit = formatWaitDuration(Math.max(0, minMs - sinceMs));
    showNotification(
        `Слишком рано! Лучше поливать через ${unit} Растение может заболеть.`,
        false,
        { warning: true }
    );
    recordPlantMistakeCategory(data, 'water');
    recordMistakeToServer(data.plant, 'overwater', { countForAchievement: false });
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
    showNotification(`${plantName} ${bloomBlock}!`, false, { warning: true });
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

function applyPlantDisease(slotName, data, diseaseType, source, { triggerAchievement = true } = {}) {
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
    refreshPlantVisual(slotName);

    if (triggerAchievement) {
        checkAchievement_negativeEffect();
    }
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

    const isDiseaseVisible = data.hasDisease;

    if (data.disease === '__dead__' || data.diseaseType === 'dead') {
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

    if (isDiseaseVisible && data.disease) {
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
        updateZoomStageLabel(data);
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
    const dryMs = getMsWithoutWater(data, now);
    const droughtDeathMs = maxMs * 2;

    let diseaseApplied = false;
    let deathApplied = false;

    if (shouldApplyOverwaterDeath(data, plant)) {
        recordPlantMistakeCategory(data, 'water');
        applyPlantDeath(slotName, data, { notificationCause: 'overwatered' });
        deathApplied = true;
    } else if (shouldApplyOverwaterDisease(data, plant) && PLANT_DISEASES[plantKey]?.overwatered) {
        diseaseApplied = applyPlantDisease(slotName, data, 'overwatered', 'water');
    } else if (dryMs > droughtDeathMs) {
        recordPlantMistakeCategory(data, 'water');
        applyPlantDeath(slotName, data, { notificationCause: 'under_watered' });
        deathApplied = true;
    } else if (dryMs > maxMs && PLANT_DISEASES[plantKey]?.under_watered) {
        recordPlantMistakeCategory(data, 'water');
        if (!data.hasDisease) {
            diseaseApplied = applyPlantDisease(slotName, data, 'under_watered', 'water');
        }
    }

    if (!diseaseApplied && !deathApplied) {
        saveState();
    }
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
            const diseaseType = getDiseaseTypeFromMessage(plantKey, diseaseMsg);
            if (diseaseType) {
                data.hasDisease = true;
                data.hadMistakes = true;
                data.disease = diseaseMsg;
                data.diseaseType = diseaseType;
                data.diseaseSource = mistakeSource;
                data.diseaseStartTime = Date.now();
                saveState();
                showDiseaseAdvice(diseaseType);
                refreshPlantVisual(slotName);
            }
        }
    } else if (!diseaseMsg && data.hasDisease && isLocationBasedDisease(plantKey, data.disease) && data.stage >= 1) {
        const clearedType = data.diseaseType || getDiseaseTypeFromMessage(plantKey, data.disease);
        data.hasDisease = false;
        data.disease = null;
        data.diseaseType = null;
        data.diseaseSource = null;
        data.diseaseStartTime = null;
        saveState();

        const isLightRecovery = ['too_light', 'too_dark', 'no_flower'].includes(clearedType);
        markHealedPlant({ showRecoveryTip: !isLightRecovery });
        if (isLightRecovery) {
            showPositiveTip('goodLocation');
        }
        refreshPlantVisual(slotName);
        applyGrowthFromTime(slotName);
    }
}

function scheduleLocationCheck(slotName) {
    syncGameTick([slotName]).catch(console.error);
    setTimeout(() => {
        if (slotData[slotName]?.pot) {
            scheduleLocationCheck(slotName);
        }
    }, 30000);
}

function scheduleOverwateringCheck() {
    const tickMs = WATER_TIMING_TEST ? 10 * 1000 : 60 * 1000;
    setInterval(() => {
        syncGameTick().catch(console.error);
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
    if (rewardText) showNotification(rewardText, false);
    checkAndUnlockPots();
    checkAndUnlockWateringCans();
    renderPotChoices();
    renderFlowerChoices();
    renderWateringCanChoices();
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

const QUEST_COMPLETION_TEXTS = {
    read_tip: '📖 Задание выполнено: описание прочитано!',
    heal_plant: '💚 Задание выполнено: растение выздоровело!',
    plant_first: '🌱 Задание выполнено: первое растение посажено!',
    water_once: '💧 Задание выполнено: растение полито!',
    grow_stage2: '🌿 Задание выполнено: цветок вырос до ростка!',
    login_3days: '🗓️ Задание выполнено: 3 дней в игре подряд!',
    login_5days: '🗓️ Задание выполнено: 5 дней в игре подряд!',
    login_7days: '🗓️ Задание выполнено: 7 дней в игре подряд!',
    login_10days: '🗓️ Задание выполнено: 10 дней в игре подряд!'
};

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

function markQuestDone(id, { notify = true } = {}) {
    const done = getQuestsDoneIds();
    if (done.includes(id)) return false;
    done.push(id);
    localStorage.setItem(`questsDone_${currentUser}`, JSON.stringify(done));
    const text = QUEST_COMPLETION_TEXTS[id];
    if (notify && text) showNotification(text, false);
    return true;
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

    const quests = serverQuests.length ? serverQuests : [];

    if (quests.length === 0) {
        list.innerHTML = '<div class="quest-item">Все задания выполнены! 🌟</div>';
        return;
    }

    const itemsHtml = quests.map((q, index) => {
        const isDone = q.completed === true;
        const progress = q.progress || 0;
        const target = q.target || 1;
        const description = q.description || `Задание ${index + 1}`;
        const progressText = target > 1 ? ` (${progress}/${target})` : '';

        return `<div class="quest-item ${isDone ? 'done' : ''}">
            <span class="quest-check">${isDone ? '✓' : '○'}</span>
            <span class="quest-desc">${description}${progressText}</span>
        </div>`;
    }).join('');

    const allDone = serverQuestsAllCompleted;
    const allDoneBanner = allDone
        ? '<div class="quest-item quest-all-done is-info"><span class="quest-check">ℹ️</span><span class="quest-desc">Все задания выполнены! 🌟</span></div>'
        : '';

    list.innerHTML = itemsHtml + allDoneBanner;
}

async function checkQuestsAfterAction() {
    await loadQuestsFromServer();
    await syncGameTick();
}

function markHealedPlant({ showRecoveryTip = true } = {}) {
    if (showRecoveryTip) showPositiveTip('recovered');
}

function checkAndUnlockPots() {
    const userLevel = currentLevel;
    let unlockedAny = false;

    Object.entries(POT_CONFIG).forEach(([num, cfg]) => {
        const unlockLevel = cfg.unlockLevel || 1;
        if (unlockLevel <= userLevel && !cfg.isUnlocked) {
            POT_CONFIG[num].isUnlocked = true;
            unlockedAny = true;
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
            div.addEventListener('click', () => {
                showNotification('Горшок ещё не открыт', true);
            });
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
            div.addEventListener('click', async () => {
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

                try {
                    const result = await postGameAction('plant', {
                        slotName: name,
                        speciesId: parseInt(plantKey, 10)
                    });
                    if (!result.success) {
                        showNotification(result.error || 'Не удалось посадить растение', true);
                        return;
                    }

                    applyServerGameResponse(result, { refreshSlotName: name });
                    handleServerGameEvents(result, name);
                    renderSlot(activeSlot, slotData[name]);
                    closeModal(modalPickFlower);
                    activeSlot = null;
                    showNotification(
                        `Цветок посажен\n${plant.name} посажен! 🌱 Первый росток появится через ${getSeedlingWaitLabel(plant)}...`,
                        false
                    );
                    saveState();
                    await checkQuestsAfterAction();
                    scheduleGrowth(name);
                    scheduleLocationCheck(name);
                } catch (error) {
                    console.error('Ошибка посадки на сервере:', error);
                    showNotification('Ошибка посадки. Попробуйте снова.', true);
                }
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
            div.addEventListener('click', () => {
                showNotification('Лейка ещё не открыта', true);
            });
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
        'windowsill-1': 'Подоконник слева',
        'windowsill-2': 'Подоконник по центру',
        'windowsill-3': 'Подоконник справа',
        'desk-left': 'Стол слева',
        'desk-right-1': 'Стол справа',
        'desk-right-2': 'Стол справа'
    };

    allSlots.forEach(slotEl => {
        const slotName = slotEl.dataset.slot;
        const targetData = slotData[slotName];
        const isCurrent = slotName === moveFromSlot;

        const isEmpty = !targetData || !targetData.pot;
        const hasPlant = targetData && targetData.plant && targetData.stage >= 1 && PLANTS[targetData.plant];

        const div = document.createElement('div');
        div.className = 'pot-choice';
        if (isCurrent) div.classList.add('pot-choice--source');
        if (isEmpty) div.classList.add('empty-slot');
        else if (hasPlant) div.classList.add('occupied-slot');
        else if (targetData?.pot) div.classList.add('empty-pot-slot');
        div.dataset.slot = slotName;

        let slotDisplayName = slotNamesMap[slotName] || slotName.replace(/-/g, ' ');
        let potImg = '/images/room/пунктир.png';
        let statusHtml = '';

        if (targetData && targetData.pot && POT_CONFIG[targetData.pot]) {
            potImg = POT_CONFIG[targetData.pot].img;
        }

        if (isEmpty) {
            statusHtml = '<span class="free-label">Свободно</span>';
        } else if (hasPlant) {
            const plant = PLANTS[targetData.plant];
            statusHtml = `<span class="occupied-label">${escapeHtml(plant.name)}</span>`;
        } else if (targetData.pot) {
            statusHtml = '<span class="occupied-label">Пустой горшок</span>';
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

        if (!isCurrent) {
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
        }

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

    // Отправляем запрос на сервер
    postGameAction('move', { fromSlot, toSlot }).then((result) => {
        if (!result.success) {
            showNotification(result.error || '❌ Не удалось переместить растение', true);
            return;
        }

        // Обновляем данные из ответа сервера
        if (result.slotData) {
            // Очищаем старый слот и устанавливаем новый
            slotData[toSlot] = result.slotData[toSlot];
            slotData[fromSlot] = result.slotData[fromSlot] || null;
        }

        applyServerGameResponse(result, { refreshSlotName: toSlot });
        handleServerGameEvents(result, toSlot);

        const fromSlotEl = document.querySelector(`[data-slot="${fromSlot}"]`);
        const toSlotEl = document.querySelector(`[data-slot="${toSlot}"]`);

        if (fromSlotEl) renderSlot(fromSlotEl, slotData[fromSlot] || null);
        if (toSlotEl) renderSlot(toSlotEl, slotData[toSlot]);

        saveState();
        showNotification('🪴 Растение перемещено на новое место!', false);
        checkQuestsAfterAction();

        closeModal(zoomOverlay);
        zoomedSlot = null;
    }).catch((error) => {
        console.error('Ошибка перемещения на сервере:', error);
        showNotification('❌ Ошибка перемещения', true);
    });
}
function swapPlants(slotA, slotB) {
    if (!slotData[slotA] || !slotData[slotB]) return;

    // Сохраняем данные для отправки на сервер
    const plantIdA = slotData[slotA]?.plantId;
    const plantIdB = slotData[slotB]?.plantId;

    // Локально меняем местами
    const dataA = { ...slotData[slotA] };
    const dataB = { ...slotData[slotB] };

    if (dataA) dataA.devManualState = false;
    if (dataB) dataB.devManualState = false;

    slotData[slotA] = dataB;
    slotData[slotB] = dataA;

    // Отправляем оба перемещения на сервер
    const promises = [];
    if (plantIdA) {
        promises.push(postGameAction('move', { fromSlot: slotA, toSlot: slotB }));
    }
    if (plantIdB) {
        promises.push(postGameAction('move', { fromSlot: slotB, toSlot: slotA }));
    }

    Promise.all(promises).then((results) => {
        // Обновляем из результатов, если нужно
        for (const result of results) {
            if (result.success && result.slotData) {
                Object.assign(slotData, result.slotData);
            }
        }

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

        closeModal(zoomOverlay);
        zoomedSlot = null;
    }).catch((error) => {
        console.error('Ошибка обмена местами:', error);
        showNotification('❌ Ошибка при обмене', true);
    });
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
    scheduleLocationCheck(name);
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
            hint.textContent = data.lastWateredAt ? 'Прорастает...' : 'Полей!';
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
    const timerBox = document.getElementById('growthTimerBox');
    if (!timerBox) return;

    const timerText = getGrowthTimerLabel(data);
    if (!timerText) {
        timerBox.style.display = 'none';
        return;
    }

    timerBox.textContent = timerText;
    timerBox.style.display = 'block';
}

function updateNextWateringTimer(data) {
    const timerBox = document.getElementById('waterTimerBox');
    if (!timerBox) return;

    const plant = data?.plant ? PLANTS[data.plant] : null;
    const timerText = getWaterTimerLabel(data, plant);

    if (!timerText) {
        timerBox.style.display = 'none';
        return;
    }

    timerBox.textContent = timerText;
    timerBox.style.display = 'block';
}

function updateDiseaseInfo(data) {
    const diseaseBox = document.getElementById('diseaseBox');
    const diseaseTextEl = document.getElementById('diseaseText');
    if (!diseaseBox || !diseaseTextEl) return;

    const text = getDiseaseBlockText(data);
    if (!text) {
        diseaseBox.style.display = 'none';
        return;
    }

    diseaseTextEl.textContent = text;
    diseaseBox.style.display = 'block';
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
        } else if (norm.includes('недостаточный полив') || norm.includes('сохнут кончики') || norm.includes('желтеют листья')) {
            advice = '💧 Решение: Полей растение. Следи, чтобы полив был регулярным.';
        } else if (norm.includes('перелив') || norm.includes('увядание')) {
            const plant = PLANTS[data.plant];
            const dryMs = plant ? getOverwaterHealDryMs(plant) : 0;
            const dryHint = formatWaitDuration(dryMs);
            advice = `💧 Решение: Не поливай ${dryHint} — дай почве просохнуть. После этого растение выздоровеет.`;
        } else if (norm.includes('вытягивание') || norm.includes('нехватк') || norm.includes('нет цветения')) {
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
}

function openZoom(slotEl, name, data) {
    zoomedSlot = { slotEl, name };
    currentZoomedPlantId = name;
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
        if (plantImg) {
            updateZoomPlantVisual(data);
        }

        const zoomPlantName = document.getElementById('zoomPlantName');
        if (zoomPlantName) zoomPlantName.textContent = `${plant.name} — ${plant.nickname}`;

        updateZoomStageLabel(data);

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

        updateZoomStageLabel(data);

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
if (zoomClose) zoomClose.addEventListener('click', closeZoomOverlay);

if (zoomOverlay) zoomOverlay.addEventListener('click', e => { if (e.target === zoomOverlay) closeZoomOverlay(); });

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
                checkLocationDisease(name);
                refreshPlantVisual(name);
                const slotEl = document.querySelector(`[data-slot="${name}"]`);
                if (slotEl) renderSlot(slotEl, slotData[name]);
                closeModal(modalRepot);
                showNotification(`🪴 Растение пересажено в ${cfg.name}!`, false);
                saveState();
                const zoomPotImg = document.getElementById('zoomPotImg');
                if (zoomPotImg && POT_CONFIG[data.pot]) zoomPotImg.src = POT_CONFIG[data.pot].img;
                if (zoomedSlot?.name === name) {
                    updateZoomPlantVisual(slotData[name]);
                    updateZoomStageLabel(slotData[name]);
                    updateDiseaseInfo(slotData[name]);
                    showFixAdvice(slotData[name]);
                }
            });
        } else if (locked) {
            div.title = `Открывается на ${cfg.unlockLevel}-м уровне`;
            div.addEventListener('click', () => {
                showNotification('Горшок ещё не открыт', true);
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

const descBtnRight = document.getElementById('descBtnRight');
if (descBtnRight) {
    descBtnRight.addEventListener('click', () => {
        if (!zoomedSlot) return;
        const data = slotData[zoomedSlot.name];
        if (data?.plant && PLANTS[data.plant]) {
            openPlantDescription(data.plant);
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

        moveFromSlot = zoomedSlot.name;
        closeModal(zoomOverlay);
        zoomedSlot = null;
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

        startWateringAnimation();

        setTimeout(async () => {
            try {
                const result = await postGameAction('water', { slotName: name });
                if (!result.success) {
                    showNotification(result.error || 'Не удалось полить растение', true);
                    stopWateringAnimation();
                    return;
                }

                applyServerGameResponse(result, { refreshSlotName: name });
                handleServerGameEvents(result, name);

                renderSlot(slotEl, slotData[name]);
                updateNextWateringTimer(slotData[name]);
                updateGrowthTimer(slotData[name]);
                updateZoomPlantVisual(slotData[name]);
                updateZoomStageLabel(slotData[name]);
                saveState();
                await checkQuestsAfterAction();
            } catch (error) {
                console.error('Ошибка полива на сервере:', error);
                showNotification('Ошибка полива. Попробуйте снова.', true);
            } finally {
                stopWateringAnimation();
            }
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

if (closePlantDescBtn) {
    closePlantDescBtn.addEventListener('click', closePlantDescription);
}

if (modalPlantDescription) {
    modalPlantDescription.addEventListener('click', (e) => {
        if (e.target === modalPlantDescription) {
            closePlantDescription();
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
                    if (slotData[name].pot) {
                        scheduleLocationCheck(name);
                    }
                    if (slotData[name].plant && (slotData[name].hasDisease || isPlantDead(slotData[name]))) {
                        scheduleSicknessDeathCheck(name);
                    }
                }
            });
        }
    } catch (e) {
        console.warn('Не удалось загрузить состояние комнаты', e);
    }
}

function tryAdvanceToSprout(slotName) {
    const data = slotData[slotName];
    if (!data?.plant || data.stage !== 0 || isPlantDead(data) || !data.plantedAt) return false;
    const plant = PLANTS[data.plant];
    if (!plant) return false;
    if (!data.lastWateredAt) return false;
    if (Date.now() - data.plantedAt < getSeedlingMs(plant)) return false;

    data.stage = 1;
    data.sproutedAt = data.sproutedAt || Date.now();

    const slotEl = document.querySelector(`[data-slot="${slotName}"]`);
    if (slotEl) renderSlot(slotEl, data);

    showNotification(`🌱 ${PLANTS[data.plant]?.name} дало росток!`, false);
    saveState();
    checkQuestsAfterAction();

    setTimeout(() => {
        checkLocationDisease(slotName);
        checkWateringHealth(slotName, slotData[slotName]);
    }, 100);

    scheduleGrowth(slotName);
    return true;
}

function applyGrowthFromTime(slotName) {
    const data = slotData[slotName];
    if (!data || !data.plant || !data.plantedAt || isPlantDead(data)) return;

    const plant = PLANTS[data.plant];
    if (!plant) return;

    const msSincePlanted = Date.now() - data.plantedAt;
    const bloomMs = getBloomMs(plant);

    if (msSincePlanted >= bloomMs && data.stage < 2) {
        syncSlotHealthChecks(slotName);
        const dataAfter = slotData[slotName];
        const bloomBlock = getBloomBlockReason(dataAfter, plant);
        if (!bloomBlock && dataAfter.stage >= 1) {
            clearBloomBlockNotified(dataAfter);
            const oldStage = dataAfter.stage;
            dataAfter.stage = 2;
            dataAfter.bloomedAt = dataAfter.bloomedAt || (dataAfter.plantedAt + bloomMs);
            const slotEl = document.querySelector(`[data-slot="${slotName}"]`);
            if (slotEl) renderSlot(slotEl, dataAfter);

            if (oldStage !== 2) {
                showBloomDoneNotification(plant);
                checkAllAchievementsOnBloom(slotName, dataAfter);
            }
            saveState();
            checkQuestsAfterAction();
        } else if (bloomBlock) {
            notifyBloomBlockedOnce(dataAfter, bloomBlock);
        } else {
            clearBloomBlockNotified(dataAfter);
        }
    } else if (data.stage < 1) {
        tryAdvanceToSprout(slotName);
    }
}

function scheduleGrowth(slotName) {
    const data = slotData[slotName];
    if (!data || !data.plant || !data.plantedAt) return;

    const plant = PLANTS[data.plant];
    if (!plant) return;

    const now = Date.now();
    const msSincePlanted = now - data.plantedAt;
    const seedlingMs = getSeedlingMs(plant);
    const bloomMs = getBloomMs(plant);

    const runServerGrowthTick = () => {
        syncGameTick([slotName]).then((result) => {
            if (result?.success) {
                handleServerGameEvents(result, slotName);
                refreshPlantVisual(slotName);
                saveState();
                checkQuestsAfterAction();
            }
        }).catch(console.error);
    };

    if (data.stage === 0) {
        if (msSincePlanted >= seedlingMs) {
            runServerGrowthTick();
            return;
        }
        const msUntilSeedling = Math.max(0, seedlingMs - msSincePlanted);
        setTimeout(runServerGrowthTick, msUntilSeedling);
    } else if (data.stage === 1 && msSincePlanted < bloomMs) {
        const msUntilBloom = Math.max(0, bloomMs - msSincePlanted);
        setTimeout(runServerGrowthTick, msUntilBloom);
    }
}

function loadLevel() {
    const lvl = parseInt(localStorage.getItem(`currentLevel_${currentUser}`) || '1');
    updateLevelCircle(lvl);
}

updateRoomScale();
window.addEventListener('resize', updateRoomScale);

function applyUnlocksForLevel(level) {
    Object.entries(POT_CONFIG).forEach(([num, cfg]) => {
        if (cfg) {
            cfg.isUnlocked = (cfg.unlockLevel || 1) <= level;
        }
    });
    Object.entries(WATERING_CAN_CONFIG).forEach(([id, cfg]) => {
        if (cfg) {
            cfg.isUnlocked = (cfg.unlockLevel || 1) <= level;
        }
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

    applyUnlocksForLevel(currentLevel);
    const loadedFromServer = await loadStateFromServer();
    if (!loadedFromServer) {
        loadState();
    }
    await syncGameTick();
    await loadAchievementsFromServer();
    applyUnlocksForLevel(currentLevel);
    await loadQuestsFromServer();
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
                await checkQuestsAfterAction();
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
        if (tutorialSkipBtn) {
            tutorialSkipBtn.textContent = 'Пропустить обучение';
        }
    }

    function updateTutorialChrome() {
        if (currentMode === 'firstTime') {
            const isFinale = tutorialCurrentStep === FIRST_TIME_FINALE_STEP;
            const hideSkipLink = isFinale || tutorialCurrentStep === 5;

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
                skipWrapper.classList.toggle('is-hidden', hideSkipLink);
            }
            setTutorialClosableUi(false);
            if (isFinale) {
                setNextButtonStartGame();
            } else {
                setNextButtonNormal();
            }
            if (!hideSkipLink) {
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

    function isTutorialKeyboardTarget(el) {
        if (!el) return false;
        const tag = el.tagName;
        return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || el.isContentEditable;
    }

    function isTutorialOpen() {
        return tutorialOverlay?.classList.contains('active');
    }

    document.addEventListener('keydown', (e) => {
        if (!isTutorialOpen()) return;
        if (e.key === 'Escape') return;

        if (isTutorialKeyboardTarget(document.activeElement)) return;
        const focusedTag = document.activeElement?.tagName;
        if (focusedTag === 'BUTTON' || focusedTag === 'A') return;

        if (e.key === 'ArrowLeft' || e.code === 'ArrowLeft') {
            e.preventDefault();
            prevTutorialStep();
            return;
        }

        if (e.key === 'ArrowRight' || e.code === 'ArrowRight' || e.key === ' ' || e.code === 'Space') {
            e.preventDefault();
            nextTutorialStep();
        }
    });

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

document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;

    if (document.body.classList.contains('first-time-onboarding')) return;

    if (modalPlantDescription?.classList.contains('active')) {
        closePlantDescription();
        e.preventDefault();
        return;
    }

    if (modalAchievements?.classList.contains('active')) {
        closeModal(modalAchievements);
        e.preventDefault();
        return;
    }

    if (modalWaterCan?.classList.contains('active')) {
        closeModal(modalWaterCan);
        e.preventDefault();
        return;
    }

    if (modalMovePlant?.classList.contains('active')) {
        closeModal(modalMovePlant);
        moveFromSlot = null;
        e.preventDefault();
        return;
    }

    if (modalRepot?.classList.contains('active')) {
        closeModal(modalRepot);
        e.preventDefault();
        return;
    }

    if (modalPickFlower?.classList.contains('active')) {
        closeModal(modalPickFlower);
        activeSlot = null;
        e.preventDefault();
        return;
    }

    if (modalPlacePot?.classList.contains('active')) {
        closeModal(modalPlacePot);
        e.preventDefault();
        return;
    }

    if (zoomOverlay?.classList.contains('active')) {
        closeZoomOverlay();
        e.preventDefault();
        return;
    }

    if (tutorialOverlay?.classList.contains('active')) {
        if (typeof window.closeTutorialGlobal === 'function') {
            window.closeTutorialGlobal();
            e.preventDefault();
        }
    }
});