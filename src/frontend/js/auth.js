const API_BASE_URL = '/api';

const usernameInput = document.getElementById('username');
const passwordInput = document.getElementById('password');
const submitBtn = document.getElementById('submitBtn');
const form = document.getElementById('registerForm');
const usernameError = document.getElementById('usernameError');
const passwordError = document.getElementById('passwordError');

let validation = { username: false, password: false };

function setValidState(input, errorElement) {
    errorElement.textContent = '✅';
    errorElement.style.color = '#4caf50';
    removeErr(input);
}

function setInvalidState(input, errorElement, message = '') {
    errorElement.textContent = message;
    errorElement.style.color = '';
    if (message) {
        addErr(input);
    } else {
        removeErr(input);
    }
}

function validateUsername(value) {
    value = value.trim();
    if (!value) {
        setInvalidState(usernameInput, usernameError);
        return false;
    }
    if (value.length < 3) {
        setInvalidState(usernameInput, usernameError, '❌ Минимум 3 символа');
        return false;
    }
    if (value.length > 50) {
        setInvalidState(usernameInput, usernameError, '❌ Максимум 50 символов');
        return false;
    }
    if (!/^[a-zA-Z0-9а-яА-Я_-]+$/.test(value)) {
        setInvalidState(usernameInput, usernameError, '❌ Только буквы, цифры, _ и -');
        return false;
    }
    setValidState(usernameInput, usernameError);
    return true;
}

function validatePassword(value) {
    if (!value) {
        setInvalidState(passwordInput, passwordError);
        return false;
    }
    if (value.length < 4) {
        setInvalidState(passwordInput, passwordError, '❌ Минимум 4 символа');
        return false;
    }
    if (value.length > 100) {
        setInvalidState(passwordInput, passwordError, '❌ Слишком длинный');
        return false;
    }
    setValidState(passwordInput, passwordError);
    return true;
}

function addErr(el) {
    el.closest('.input-field')?.classList.add('error');
}
function removeErr(el) {
    el.closest('.input-field')?.classList.remove('error');
}
function updateBtn() {
    const ready = validation.username && validation.password;
    submitBtn.classList.toggle('is-inactive', !ready);
    submitBtn.setAttribute('aria-disabled', String(!ready));
}

usernameInput.addEventListener('input', e => {
    validation.username = validateUsername(e.target.value);
    updateBtn();
});
passwordInput.addEventListener('input', e => {
    validation.password = validatePassword(e.target.value);
    updateBtn();
});

const NOTIFICATION_DURATION_MS = 10 * 1000;
let notificationIdSeq = 0;
const activeNotifications = [];

function refreshNotificationLayers() {
    activeNotifications.forEach((entry, index) => {
        const isTop = index === activeNotifications.length - 1;
        entry.element.classList.toggle('is-covered', !isTop);
        entry.element.style.zIndex = String(100 + index);
    });
}

function dismissNotification(id) {
    const index = activeNotifications.findIndex((n) => n.id === id);
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

function showNotification(message, isError = true) {
    const stack = document.getElementById('notificationStack');
    if (!stack) return;

    const id = ++notificationIdSeq;
    const el = document.createElement('div');
    el.className = 'notification-item';
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

async function post(url, body) {
    const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(body)
    });
    let data = {};
    try {
        data = await res.json();
    } catch (e) {
        data = { success: false, error: 'Ошибка парсинга ответа' };
    }
    return { ok: res.ok, status: res.status, data };
}

async function get(url) {
    const res = await fetch(url, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include'
    });
    let data = {};
    try {
        data = await res.json();
    } catch (e) {
        data = { success: false, error: 'Ошибка парсинга ответа' };
    }
    return { ok: res.ok, status: res.status, data };
}

async function checkUserExists(username) {
    try {
        const result = await post(`${API_BASE_URL}/auth/check_user`, { username });
        return result.data.exists === true;
    } catch (err) {
        console.error('checkUserExists error:', err);
        return false;
    }
}

async function register(username, password) {
    try {
        const result = await post(`${API_BASE_URL}/auth/register`, { username, password });

        if (result.ok && result.data.success) {
            showNotification(`Аккаунт создан! Добро пожаловать, ${username}! 🌱`, false);
            // После регистрации сразу логинимся
            await login(username, password, { afterRegister: true });
        } else {
            showNotification(result.data.error || 'Ошибка регистрации');
            return false;
        }
        return true;
    } catch (err) {
        console.error('register error:', err);
        showNotification('Ошибка соединения с сервером');
        return false;
    }
}

async function login(username, password, options = {}) {
    try {
        const result = await post(`${API_BASE_URL}/auth/login`, {
            username,
            password,
            remember_me: true
        });

        if (result.ok && result.data.success) {
            onLoginSuccess(result.data, options);
            return true;
        } else if (result.status === 401) {
            showNotification(result.data.error || 'Неверный пароль');
            resetPassword();
            return false;
        } else {
            showNotification(result.data.error || 'Ошибка авторизации');
            resetPassword();
            return false;
        }
    } catch (err) {
        console.error('login error:', err);
        showNotification('Ошибка соединения с сервером');
        resetPassword();
        return false;
    }
}

async function handleAuth(username, password) {
    const exists = await checkUserExists(username);

    if (!exists) {
        await register(username, password);
    } else {
        await login(username, password);
    }
}

function onLoginSuccess(data, { afterRegister = false } = {}) {
    localStorage.setItem('userId', data.user_id);
    localStorage.setItem('username', data.username);
    localStorage.setItem('session_token', data.session_token);

    if (afterRegister) {
        sessionStorage.setItem('showWelcomeAfterRegister', '1');
        localStorage.setItem('isReturningUser', 'false');
        setTimeout(() => {
            window.location.href = 'welcome.html';
        }, 1000);
        return;
    }

    sessionStorage.removeItem('showWelcomeAfterRegister');
    localStorage.setItem('isReturningUser', 'true');
    localStorage.removeItem('pendingFirstTimeTutorial');
    showNotification(`С возвращением, ${data.username}! 🌿`, false);
    setTimeout(() => {
        window.location.href = 'room.html';
    }, 1000);
}

function resetPassword() {
    passwordInput.value = '';
    validation.password = false;
    updateBtn();
}

function clearForm() {
    usernameInput.value = '';
    passwordInput.value = '';
    validation.username = false;
    validation.password = false;
    updateBtn();
}

form.addEventListener('submit', async e => {
    e.preventDefault();

    const username = usernameInput.value.trim();
    const password = passwordInput.value;

    if (!username || !password) {
        showNotification('Заполните все поля', true);
        return;
    }

    if (!validation.username || !validation.password) {
        showNotification('Проверьте правильность заполнения полей', true);
        return;
    }

    submitBtn.disabled = true;
    submitBtn.style.opacity = '0.7';

    await handleAuth(username, password);

    submitBtn.disabled = false;
    submitBtn.style.opacity = '';
});

clearForm();
usernameInput.focus();

document.addEventListener('click', (e) => {
    if (e.target.id === 'exitBtn' || e.target.closest('#exitBtn')) {
        localStorage.removeItem('userId');
        localStorage.removeItem('username');
        localStorage.removeItem('session_token');
        localStorage.removeItem('isReturningUser');
        clearForm();
    }
});

const REGISTER_DESIGN_W = 600;
const REGISTER_DESIGN_H = 500;
const REGISTER_MIN_SCALE = 0.28;

function updateRegisterScale() {
    const fill = 0.82;
    const raw = Math.min(
        (window.innerWidth * fill) / REGISTER_DESIGN_W,
        (window.innerHeight * fill) / REGISTER_DESIGN_H
    );
    const scale = Math.max(REGISTER_MIN_SCALE, Math.min(raw, 1));
    document.documentElement.style.setProperty('--register-scale', String(scale));
}

updateRegisterScale();
window.addEventListener('resize', updateRegisterScale);
