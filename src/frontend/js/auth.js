const API_BASE_URL = 'http://localhost:5000/api';

// DOM элементы
const usernameInput = document.getElementById('username');
const passwordInput = document.getElementById('password');
const submitBtn = document.getElementById('submitBtn');
const form = document.getElementById('registerForm');
const usernameError = document.getElementById('usernameError');
const passwordError = document.getElementById('passwordError');

let validation = { username: false, password: false };

function setValidState(input, errorElement) {
    errorElement.textContent = '✓';
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

// Валидация
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
    if (value.length > 50) {
        setInvalidState(passwordInput, passwordError, '❌ Максимум 50 символов');
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
    submitBtn.disabled = !(validation.username && validation.password);
}

usernameInput.addEventListener('input', e => {
    validation.username = validateUsername(e.target.value);
    updateBtn();
});
passwordInput.addEventListener('input', e => {
    validation.password = validatePassword(e.target.value);
    updateBtn();
});

// Уведомления
function showNotification(message, isError = true) {
    const n = document.getElementById('notification');
    n.querySelector('.notif-icon').textContent = isError ? '❌' : '✅';
    n.querySelector('.notif-text').textContent = message;
    n.classList.add('show');
    setTimeout(() => n.classList.remove('show'), 3000);
}

// HTTP helper
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

// Проверка существования пользователя
async function checkUserExists(username) {
    try {
        const result = await post(`${API_BASE_URL}/auth/check_user`, { username });
        return result.data.exists === true;
    } catch (err) {
        console.error('checkUserExists error:', err);
        return false;
    }
}

// Регистрация
async function register(username, password) {
    try {
        const result = await post(`${API_BASE_URL}/auth/register`, { username, password });

        if (result.ok && result.data.success) {
            showNotification(`Аккаунт создан! Добро пожаловать, ${username}! 🌱`, false);
            // После регистрации сразу логинимся
            await login(username, password);
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

// Логин
async function login(username, password) {
    try {
        const result = await post(`${API_BASE_URL}/auth/login`, {
            username,
            password,
            remember_me: true
        });

        if (result.ok && result.data.success) {
            onLoginSuccess(result.data);
            return true;
        } else if (result.status === 401) {
            showNotification(result.data.error || '❌ Неверный пароль');
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

// Основная логика
async function handleAuth(username, password) {
    // Проверяем, существует ли пользователь
    const exists = await checkUserExists(username);

    if (!exists) {
        // Новый пользователь - регистрируем
        await register(username, password);
    } else {
        // Существующий - логиним
        await login(username, password);
    }
}

function onLoginSuccess(data) {
    localStorage.setItem('userId', data.user_id);
    localStorage.setItem('username', data.username);
    localStorage.setItem('session_token', data.session_token);

    if (data.need_tutorial) {
        localStorage.setItem('isReturningUser', 'false');
        showNotification(`Добро пожаловать, ${data.username}! 🌱`, false);
        setTimeout(() => {
            window.location.href = '/welcome.html';
        }, 1000);
    } else {
        localStorage.setItem('isReturningUser', 'true');
        showNotification(`С возвращением, ${data.username}! 🌿`, false);
        setTimeout(() => {
            window.location.href = '/room.html';
        }, 1000);
    }
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

// Обработка отправки формы
form.addEventListener('submit', async e => {
    e.preventDefault();
    if (submitBtn.disabled) return;

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

// Инициализация
clearForm();
usernameInput.focus();

// Обработчик выхода
document.addEventListener('click', (e) => {
    if (e.target.id === 'exitBtn' || e.target.closest('#exitBtn')) {
        localStorage.removeItem('userId');
        localStorage.removeItem('username');
        localStorage.removeItem('session_token');
        localStorage.removeItem('isReturningUser');
        clearForm();
    }
});