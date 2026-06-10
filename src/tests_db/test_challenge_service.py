"""
Автоматизированные тесты ChallengeService.

Проверяем:
- подсчёт выполненных достижений;
- расчёт прогресса по ачивкам;
- регистрацию ошибок пользователя;
- регистрацию идеального выращивания;
- обновление статистики достижений.

Инструменты:
- pytest
- unittest.mock
"""
import sys
from pathlib import Path
from unittest.mock import Mock

SRC_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SRC_DIR))

from backend.database_full.service.challenge_service import ChallengeService


def create_service():
    service = ChallengeService()

    service.challenge_repo = Mock()
    service.mistake_repo = Mock()
    service.user_repo = Mock()
    service.plant_repo = Mock()

    return service


# =========================
# Подсчёт выполненных достижений
# =========================

def test_get_completed_count_empty():
    service = create_service()

    service.challenge_repo.get_completed_achievements.return_value = []

    assert service.get_completed_count("user1") == 0


def test_get_completed_count_success():
    service = create_service()

    service.challenge_repo.get_completed_achievements.return_value = [
        {"id": 1},
        {"id": 2},
        {"id": 3},
    ]

    assert service.get_completed_count("user1") == 3


# =========================
# Получение прогресса по достижению
# =========================

def test_get_progress_perfect_growth():
    service = create_service()

    service.challenge_repo.check_grow_to_maturity_perfect.return_value = 2

    assert service._get_progress("user1", "grow_to_maturity_perfect") == 2


def test_get_progress_first_wither():
    service = create_service()

    service.challenge_repo.check_first_wither.return_value = 1

    assert service._get_progress("user1", "first_wither") == 1


def test_get_progress_first_negative_effect():
    service = create_service()

    service.challenge_repo.check_first_negative_effect.return_value = 5

    assert service._get_progress("user1", "first_negative_effect") == 5


def test_get_progress_species_collected():
    service = create_service()

    service.challenge_repo.check_species_collected.return_value = 3

    assert service._get_progress("user1", "grow_all_species") == 3


def test_get_progress_daily_streak():
    service = create_service()

    service.challenge_repo.get_consecutive_days.return_value = 7

    assert service._get_progress("user1", "daily_streak") == 7


def test_get_progress_level():
    service = create_service()

    service.challenge_repo.get_level.return_value = 4

    assert service._get_progress("user1", "reach_level") == 4


def test_get_progress_unknown_type():
    service = create_service()

    assert service._get_progress("user1", "unknown") == 0


# =========================
# Регистрация ошибки пользователя
# =========================

def test_record_mistake():
    service = create_service()

    service.check_all = Mock(return_value=[{"name": "Achievement"}])

    result = service.record_mistake(
        "user1",
        "plant1",
        "overwater"
    )

    assert result["success"] is True
    assert result["mistake_type"] == "overwater"
    assert len(result["new_achievements"]) == 1

    service.mistake_repo.add_mistake.assert_called_once()
    service.user_repo.increment_stat.assert_called_once()


# =========================
# Регистрация идеального выращивания
# =========================

def test_record_perfect_growth():
    service = create_service()

    service.check_all = Mock(return_value=[])

    result = service.record_perfect_growth(
        "user1",
        "plant1"
    )

    assert result["success"] is True

    service.plant_repo.mark_perfect_growth.assert_called_once_with(
        "plant1"
    )


# =========================
# Регистрация смерти растения
# =========================

def test_record_plant_death():
    service = create_service()

    service.check_all = Mock(return_value=[])

    result = service.record_plant_death(
        "user1",
        "plant1"
    )

    assert result["success"] is True


# =========================
# Регистрация нового вида растения
# =========================

def test_record_species_collected():
    service = create_service()

    service.check_all = Mock(return_value=[])

    result = service.record_species_collected("user1")

    assert result["success"] is True


# =========================
# Обновление ежедневной серии входов
# =========================

def test_record_daily_streak():
    service = create_service()

    service.check_all = Mock(return_value=[])

    result = service.record_daily_streak(
        "user1",
        7
    )

    assert result["success"] is True
    assert result["streak"] == 7


# =========================
# Получение статистики пользователя
# =========================

def test_get_statistics():
    service = create_service()

    service.challenge_repo.check_grow_to_maturity_perfect.return_value = 1
    service.challenge_repo.check_first_wither.return_value = 2
    service.mistake_repo.get_mistakes_count.return_value = 3
    service.challenge_repo.check_species_collected.return_value = 2
    service.challenge_repo.get_consecutive_days.return_value = 5
    service.challenge_repo.get_level.return_value = 4
    service.challenge_repo.get_completed_achievements.return_value = [
        {"id": 1},
        {"id": 2}
    ]

    result = service.get_statistics("user1")

    assert result["plants_grown_to_maturity_perfect"] == 1
    assert result["death_count"] == 2
    assert result["mistake_count"] == 3
    assert result["species_collected"] == 2
    assert result["consecutive_days"] == 5
    assert result["level"] == 4
    assert result["total_achievements"] == 2