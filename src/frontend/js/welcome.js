const API_BASE_URL = '/api';
const WELCOME_ARROW_SRC = 'images/button/кнопка-стрелка обучения.png';
const WELCOME_LAST_STEP = 1;

const TUTORIAL_DESIGN_W = 550;
const TUTORIAL_DESIGN_H = 620;
const TUTORIAL_SIZE_BOOST = 1.05;
const TUTORIAL_MAX_SCALE = 1.15;
const TUTORIAL_VIEWPORT_FILL = 0.82;
const TUTORIAL_MIN_SCALE = 0.28;

function updateWelcomeTutorialScale() {
    const raw = Math.min(
        (window.innerWidth * TUTORIAL_VIEWPORT_FILL) / TUTORIAL_DESIGN_W,
        (window.innerHeight * TUTORIAL_VIEWPORT_FILL) / TUTORIAL_DESIGN_H
    );
    const fitScale = Math.max(TUTORIAL_MIN_SCALE, raw);
    const scale = Math.max(TUTORIAL_MIN_SCALE, Math.min(fitScale * TUTORIAL_SIZE_BOOST, TUTORIAL_MAX_SCALE));
    document.documentElement.style.setProperty('--tutorial-scale', String(scale));
}

updateWelcomeTutorialScale();
window.addEventListener('resize', updateWelcomeTutorialScale);

let welcomeStep = 0;
let consumedResumeStep = null;

function consumeWelcomeResumeStep() {
    const raw = sessionStorage.getItem('welcomeResumeStep');
    if (raw === null) return null;
    sessionStorage.removeItem('welcomeResumeStep');
    const step = parseInt(raw, 10);
    if (Number.isNaN(step)) return 0;
    return Math.max(0, Math.min(step, WELCOME_LAST_STEP));
}

async function checkAuth() {
    try {
        const response = await fetch(`${API_BASE_URL}/auth/verify`, {
            method: 'GET',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' }
        });

        if (!response.ok) {
            window.location.href = 'register.html';
            return null;
        }

        const data = await response.json();
        if (!data.success) {
            window.location.href = 'register.html';
            return null;
        }

        localStorage.setItem('username', data.username);
        localStorage.setItem('userId', data.user_id);

        return data;
    } catch (error) {
        console.error('Ошибка проверки авторизации:', error);
        window.location.href = 'register.html';
        return null;
    }
}

function showWelcomeStep(step) {
    if (step < 0) step = 0;
    if (step > WELCOME_LAST_STEP) step = WELCOME_LAST_STEP;
    welcomeStep = step;

    document.querySelectorAll('.welcome-step').forEach((el, index) => {
        el.classList.toggle('active', index === welcomeStep);
    });

    document.querySelectorAll('.welcome-dot').forEach((dot, index) => {
        dot.classList.toggle('active', index === welcomeStep);
    });

    document.documentElement.classList.remove('welcome-resume-step-1');
    updateWelcomeNav();
}

function updateWelcomeNav() {
    const backBtn = document.getElementById('welcomeBackBtn');
    const nextBtn = document.getElementById('welcomeNextBtn');
    const nextBtnImg = document.getElementById('welcomeNextBtnImg');
    const nextBtnLabel = document.getElementById('welcomeNextBtnLabel');
    const isLastStep = welcomeStep === WELCOME_LAST_STEP;

    if (backBtn) {
        const onFirstStep = welcomeStep === 0;
        backBtn.disabled = onFirstStep;
        backBtn.classList.toggle('is-disabled', onFirstStep);
        backBtn.setAttribute('aria-disabled', onFirstStep ? 'true' : 'false');
    }

    if (nextBtn) {
        nextBtn.classList.toggle('welcome-next-btn--action', isLastStep);
    }

    if (nextBtnImg) {
        nextBtnImg.hidden = isLastStep;
        if (!isLastStep) {
            nextBtnImg.src = WELCOME_ARROW_SRC;
            nextBtnImg.alt = 'Далее';
        }
    }

    if (nextBtnLabel) {
        nextBtnLabel.hidden = !isLastStep;
    }
}

function startTutorial() {
    localStorage.setItem('pendingFirstTimeTutorial', '1');
    window.location.href = 'room.html';
}

function isEditableTarget(el) {
    if (!el) return false;
    const tag = el.tagName;
    return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || el.isContentEditable;
}

function welcomeGoNext() {
    if (welcomeStep < WELCOME_LAST_STEP) {
        showWelcomeStep(welcomeStep + 1);
        return;
    }
    startTutorial();
}

let welcomeNavEnabled = false;

checkAuth().then((data) => {
    if (!data) return;

    const showWelcome = sessionStorage.getItem('showWelcomeAfterRegister') === '1';
    if (!showWelcome) {
        window.location.href = 'room.html';
        return;
    }

    sessionStorage.removeItem('showWelcomeAfterRegister');
    localStorage.setItem('isReturningUser', 'false');
    welcomeNavEnabled = true;
    showWelcomeStep(consumedResumeStep !== null ? consumedResumeStep : 0);
});

document.getElementById('welcomeBackBtn')?.addEventListener('click', () => {
    if (welcomeStep > 0) {
        showWelcomeStep(welcomeStep - 1);
    }
});

document.getElementById('welcomeNextBtn')?.addEventListener('click', () => {
    if (welcomeStep < WELCOME_LAST_STEP) {
        showWelcomeStep(welcomeStep + 1);
        return;
    }
    startTutorial();
});

document.querySelectorAll('.welcome-dot').forEach(dot => {
    dot.addEventListener('click', () => {
        const step = parseInt(dot.getAttribute('data-welcome-step'), 10);
        if (!Number.isNaN(step)) {
            showWelcomeStep(step);
        }
    });
});

consumedResumeStep = consumeWelcomeResumeStep();
if (consumedResumeStep !== null) {
    welcomeNavEnabled = true;
    showWelcomeStep(consumedResumeStep);
} else {
    updateWelcomeNav();
}

document.addEventListener('keydown', (e) => {
    if (!welcomeNavEnabled) return;
    if (isEditableTarget(document.activeElement)) return;
    const focusedTag = document.activeElement?.tagName;
    if (focusedTag === 'BUTTON' || focusedTag === 'A') return;

    if (e.key === 'ArrowLeft' || e.code === 'ArrowLeft') {
        e.preventDefault();
        if (welcomeStep > 0) {
            showWelcomeStep(welcomeStep - 1);
        }
        return;
    }

    if (e.key === 'ArrowRight' || e.code === 'ArrowRight' || e.key === ' ' || e.code === 'Space') {
        e.preventDefault();
        welcomeGoNext();
    }
});
