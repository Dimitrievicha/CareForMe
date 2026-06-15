# Care For Me

Веб-приложение в формате виртуального тамагочи для ухода за комнатными растениями. Игрок выращивает цветы, следит за поливом и освещением, учится на ошибках с помощью подсказок и открывает новый контент через уровни, задания и достижения.

**Цель проекта** — спокойный игровой опыт без жёстких временных ограничений и формирование базовых навыков ухода за растениями через практику.

---

## Возможности

- Регистрация и авторизация с сохранением прогресса
- Игровая комната с 6 слотами (подоконник и стол, разная освещённость)
- 3 вида растений: Спатифиллум, Кактус, Фикус
- Уход: посадка, полив, пересадка, перестановка, удаление
- Стадии роста и система болезней с рекомендациями
- Уровни, задания и достижения
- Обучение для новых пользователей
- Система уведомлений
- Фоновая музыка с возможностью отключения

---

## Технологии

| Часть | Стек |
|-------|------|
| Frontend | HTML, CSS, JavaScript |
| Backend | Python 3, Flask |
| База данных | SQLite |
| Контейнеризация | Docker, Docker Compose |
| Тестирование | pytest, pytest-cov |

---

## Быстрый старт (Docker)

**Требования:** [Docker](https://www.docker.com/) и Docker Compose.

1. Клонируйте репозиторий:

```bash
git clone https://github.com/Dimitrievicha/CareForMe.git
```

2. Соберите и запустите контейнеры:

Если вы планируете запускать проект на **Windows**, то выполните сначала следующую команду в powershell:
```powershell
(Get-Content docker-entrypoint.sh -Raw) -replace "`r`n", "`n" | Set-Content -NoNewline docker-entrypoint.sh
```

```bash
docker-compose build --no-cache app
docker compose up --build -d
```

3. Откройте в браузере:

**http://localhost/register.html**

4. Остановить проект:

```bash
docker compose down
```

---

## Структура проекта

```
CareForMe/
├── README.md
├──  src/
│     ├── requirements.txt
│     ├── frontend/          # HTML, CSS, JS, изображения
│     │   ├── register.html
│     │   ├── room.html
│     │   ├── welcome.html
│     │   └── js/
│     ├── backend/           # Flask API и игровая логика
│     │     ├── app.py
│     │     ├── config.py
│     │     ├── database_full/ # БД, репозитории, сервисы
│     │     ├── web/           # REST API
│     │     └──  scripts/       # Инициализация и загрузка данных
│     ├── test_api/
│     └── test_db/
├── .dockerignore
├── docker-compose.yml
├── docker-entrypoint.sh
└── Dockerfile****

```

---

## Основные страницы

| URL | Описание                      |
|-----|-------------------------------|
| `/register.html` | Регистрация и вход            |
| `/welcome.html` | Приветствие (после входа)     |
| `/room.html` | Игровая комната (после входа) |
| `/unauthorized.html` | Доступ закрыт                 |

---

## API

Backend предоставляет REST API с префиксом `/api`:

- `/api/auth` — авторизация
- `/api/game` — сохранение, полив, посадка, игровые действия
- `/api/plants` — каталог растений
- `/api/quests` — задания
- `/api/achievements` — достижения
- `/api/user` — профиль
- `/api/tips` — советы

---

## Тестирование

Запуск автотестов backend (из папки `src/backend`):

```bash
pip install -r ../requirements.txt
pytest
```

С отчётом о покрытии:

```bash
pytest --cov=.
```

Подробный отчёт: [`src/tests_api/TESTING_REPORT.md`](src/tests_api/TESTING_REPORT.md) и [`src/tests_db/DB_TESTING_REPORT.md`](src/tests_db/DB_TESTING_REPORT.md)

- **80%** покрытие

---

## Команда

| Участник | Роль |
|----------|------|
| Федотова София | Менеджер, Frontend-разработчик |
| Волкова София | Дизайнер |
| Лепехина Алена | Аналитик, Game-дизайнер |
| Шматурин Дмитрий | Full-stack-разработчик |
| Осипов Иван | Backend-разработчик |
| Цветкова Марина | Тестировщик, DevOps-инженер |

---

## Сроки

Сдача проекта: **10.06.2026**

---

## Лицензия

Учебный проект. Курс «Программная инженерия». 2026 г.
