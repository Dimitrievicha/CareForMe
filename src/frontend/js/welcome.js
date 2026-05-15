// Получаем username из localStorage
const username = localStorage.getItem('username') || 'новый садовод';
const welcomeMessage = document.getElementById('welcomeMessage');

// Персонализированное приветствие
welcomeMessage.textContent = `Рады тебя видеть, ${username}! 🌿`;

// Создаем конфетти
function createConfetti() {
    const confettiContainer = document.querySelector('.confetti');
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

        if (Math.random() > 0.5) {
            confetti.style.borderRadius = '50%';
        }

        confettiContainer.appendChild(confetti);

        setTimeout(() => {
            confetti.remove();
        }, duration * 1000);
    }
}

// Запускаем конфетти при загрузке
createConfetti();

// Обработчик кнопки "Войти в сад"
const continueBtn = document.getElementById('continueBtn');
continueBtn.addEventListener('click', () => {
    continueBtn.style.transform = 'scale(0.98)';
    setTimeout(() => {
        continueBtn.style.transform = '';
    }, 100);

    // ПЕРЕХОД НА ROOM (НЕ НА LOGIN!)
    window.location.href = 'room.html';
});

// Дополнительная проверка: если пользователь не авторизован, то на login
// Но так как мы пришли с регистрации, данные в localStorage есть
if (!localStorage.getItem('username')) {
    // Если нет username, значит пользователь пришел напрямую
    window.location.href = 'register.html';
}