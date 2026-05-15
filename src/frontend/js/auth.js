// Конфигурация
const API_BASE_URL = 'http://localhost:5000/api';

// DOM элементы
const usernameInput = document.getElementById('username');
const passwordInput = document.getElementById('password');
const submitBtn = document.getElementById('submitBtn');
const form = document.getElementById('registerForm');

// Элементы ошибок
const usernameError = document.getElementById('usernameError');
const passwordError = document.getElementById('passwordError');

// Состояние валидации
let validation = {
    username: false,
    password: false
};

// Валидация имени пользователя
function validateUsername(value) {
    value = value.trim();

    if (!value) {
        usernameError.textContent = '';
        return false;
    }

    if (value.length < 3) {
        usernameError.textContent = '❌ Минимум 3 символа';
        return false;
    }

    if (value.length > 50) {
        usernameError.textContent = '❌ Максимум 50 символов';
        return false;
    }

    const regex = /^[a-zA-Z0-9а-яА-Я_-]+$/;
    if (!regex.test(value)) {
        usernameError.textContent = '❌ Только буквы, цифры, _ и -';
        return false;
    }

    usernameError.textContent = '✓';
    return true;
}

// Валидация пароля
function validatePassword(value) {
    if (!value) {
        passwordError.textContent = '';
        return false;
    }

    if (value.length < 4) {
        passwordError.textContent = '❌ Минимум 4 символа';
        return false;
    }

    if (value.length > 100) {
        passwordError.textContent = '❌ Слишком длинный';
        return false;
    }

    passwordError.textContent = '✓';
    return true;
}

// Обновление состояния кнопки
function updateSubmitButton() {
    const isValid = validation.username && validation.password;
    submitBtn.disabled = !isValid;
}

// Обработчики ввода
usernameInput.addEventListener('input', (e) => {
    validation.username = validateUsername(e.target.value);
    updateSubmitButton();
});

passwordInput.addEventListener('input', (e) => {
    validation.password = validatePassword(e.target.value);
    updateSubmitButton();
});

// Показ уведомления
function showNotification(message, isError = true) {
    const notification = document.getElementById('notification');
    const icon = notification.querySelector('.notif-icon');
    const text = notification.querySelector('.notif-text');

    if (isError) {
        icon.textContent = '❌';
    } else {
        icon.textContent = '✅';
    }
    text.textContent = message;

    notification.classList.add('show');

    setTimeout(() => {
        notification.classList.remove('show');
    }, 3000);
}

// Регистрация
async function register(username, password) {
    try {
        const response = await fetch(`${API_BASE_URL}/auth/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();

        if (data.success) {
            showNotification(`Добро пожаловать, ${data.username}! 🎉`, false);

            localStorage.setItem('userId', data.user_id);
            localStorage.setItem('username', data.username);

            setTimeout(() => {
                window.location.href = 'welcome.html';
            }, 1500);
        } else {
            showNotification(data.error || 'Ошибка регистрации');
        }
    } catch (error) {
        console.error('Ошибка:', error);
        showNotification('Ошибка соединения с сервером');
    }
}

// Отправка формы
form.addEventListener('submit', async (e) => {
    e.preventDefault();

    if (!submitBtn.disabled) {
        const username = usernameInput.value.trim();
        const password = passwordInput.value;

        await register(username, password);
    }
});

usernameInput.focus();