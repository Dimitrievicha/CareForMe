const API_BASE_URL = 'http://localhost:5000/api';

async function checkAuth() {
    try {
        const response = await fetch(`${API_BASE_URL}/auth/verify`, {
            method: 'GET',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' }
        });

        if (!response.ok) {
            window.location.href = 'unauthorized.html';
            return false;
        }

        const data = await response.json();
        if (!data.success) {
            window.location.href = 'unauthorized.html';
            return false;
        }

        // Обновляем userId и username из сервера (всегда актуально)
        localStorage.setItem('username', data.username);
        localStorage.setItem('userId', data.user_id);

        return true;
    } catch (error) {
        console.error('Ошибка проверки авторизации:', error);
        window.location.href = 'unauthorized.html';
        return false;
    }
}

// Запускаем проверку сразу
checkAuth().then(isAuth => {
    if (!isAuth) return;

    const username = localStorage.getItem('username') || 'садовод';
    const welcomeMessage = document.getElementById('welcomeMessage');
    if (welcomeMessage) {
        welcomeMessage.textContent = `Рады тебя видеть, ${username}! 🌿`;
    }

    createConfetti();
});

// Создаем конфетти
function createConfetti() {
    const confettiContainer = document.querySelector('.confetti');
    if (!confettiContainer) return;
    const colors = ['#4CAF50', '#8BC34A', '#CDDC39', '#FFEB3B', '#FF9800', '#FF5722'];

    for (let i = 0; i < 150; i++) {
        const confetti = document.createElement('div');
        confetti.classList.add('confetti-piece');

        const color = colors[Math.floor(Math.random() * colors.length)];
        const size = Math.random() * 10 + 5;
        const left = Math.random() * 100;
        const duration = Math.random() * 2 + 2;
        const delay = Math.random() * 1;

        confetti.style.backgroundColor = color;
        confetti.style.width = size + 'px';
        confetti.style.height = size + 'px';
        confetti.style.left = left + '%';
        confetti.style.animationDuration = duration + 's';
        confetti.style.animationDelay = delay + 's';

        if (Math.random() > 0.5) confetti.style.borderRadius = '50%';

        confettiContainer.appendChild(confetti);
        setTimeout(() => confetti.remove(), (duration + delay) * 1000 + 500);
    }
}

// Обработчик кнопки «Войти в сад»
const continueBtn = document.getElementById('continueBtn');
if (continueBtn) {
    continueBtn.addEventListener('click', () => {
        continueBtn.style.transform = 'scale(0.98)';
        setTimeout(() => { continueBtn.style.transform = ''; }, 100);
        window.location.href = 'room.html';
    });
}
