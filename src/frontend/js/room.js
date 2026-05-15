// ─── Данные горшков (пока только горшок1) ───
const availablePots = [
    { id: 1, name: 'Горшок 1', image: 'images/горшок1.png' }
];

// ─── Состояние ───
let activeSlot = null;

// ─── DOM ───
const overlay  = document.getElementById('modalOverlay');
const confirmBtn = document.getElementById('confirmBtn');
const cancelBtn  = document.getElementById('cancelBtn');
const slots = document.querySelectorAll('.pot-slot');

// ─── Открыть модалку ───
function openModal(slotEl) {
    activeSlot = slotEl;
    overlay.classList.add('active');
}

// ─── Закрыть модалку ───
function closeModal() {
    overlay.classList.remove('active');
    activeSlot = null;
}

// ─── Поставить горшок в слот ───
function placePot(slotEl) {
    const pot = availablePots[0]; // пока только горшок1

    // Убираем пунктир, добавляем горшок
    const slotImg = slotEl.querySelector('.slot-img');
    slotImg.style.display = 'none';

    const potImg = document.createElement('img');
    potImg.src = pot.image;
    potImg.alt = pot.name;
    potImg.className = 'slot-placed-pot';
    slotEl.prepend(potImg);

    // Помечаем слот как занятый
    slotEl.classList.add('filled');
    slotEl.style.cursor = 'default';
    slotEl.style.pointerEvents = 'none';

    // Убираем подсказку
    const hint = slotEl.querySelector('.slot-hint');
    if (hint) hint.remove();

    closeModal();
}

// ─── Обработчики слотов ───
slots.forEach(slot => {
    slot.addEventListener('click', () => {
        if (!slot.classList.contains('filled')) {
            openModal(slot);
        }
    });
});

// ─── Кнопки модалки ───
confirmBtn.addEventListener('click', () => {
    if (activeSlot) {
        placePot(activeSlot);
    }
});

cancelBtn.addEventListener('click', closeModal);

// Клик вне модалки — закрыть
overlay.addEventListener('click', (e) => {
    if (e.target === overlay) {
        closeModal();
    }
});

// ESC — закрыть
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
});
