"""
Автоматизированные тесты TipsService.

Проверяем:
- получение всех советов;
- получение позитивных советов;
- поиск совета по типу;
- получение советов по растению;
- обработку ошибок парсинга JSON.

Инструменты:
- pytest
- unittest.mock
"""

import sys
from pathlib import Path
from unittest.mock import Mock

SRC_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SRC_DIR))

from backend.database_full.service.tips_service import TipsService


def create_service():
    service = TipsService()
    service._repo = Mock()
    return service


# =========================
# Получение всех советов
# =========================

def test_get_all_tips_empty():
    service = create_service()

    service._repo.get_all_tips.return_value = []

    result = service.get_all_tips()

    assert result == []


def test_get_all_tips_success():
    service = create_service()

    service._repo.get_all_tips.return_value = [
        {
            "id": 1,
            "tip_type": "water",
            "title": "Полив",
            "message": "Поливай чаще",
            "is_positive": 1
        }
    ]

    result = service.get_all_tips()

    assert len(result) == 1
    assert result[0]["is_positive"] is True


# =========================
# Получение позитивных советов
# =========================

def test_get_positive_tips_empty():
    service = create_service()

    service._repo.get_positive_tips.return_value = []

    result = service.get_positive_tips()

    assert result == []


def test_get_positive_tips_success():
    service = create_service()

    service._repo.get_positive_tips.return_value = [
        {
            "id": 1,
            "tip_type": "good",
            "title": "Отлично",
            "message": "Так держать"
        }
    ]

    result = service.get_positive_tips()

    assert len(result) == 1
    assert result[0]["title"] == "Отлично"


# =========================
# Получение совета по типу
# =========================

def test_get_tip_by_type_not_found():
    service = create_service()

    service._repo.get_tip_by_type.return_value = []

    result = service.get_tip_by_type("unknown")

    assert result["id"] is None
    assert result["is_positive"] is True


def test_get_tip_by_type_success():
    service = create_service()

    service._repo.get_tip_by_type.return_value = [
        {
            "id": 5,
            "title": "Полив",
            "message": "Полей цветок",
            "is_positive": 0
        }
    ]

    result = service.get_tip_by_type("water")

    assert result["id"] == 5
    assert result["is_positive"] is False


# =========================
# Получение советов по растению
# =========================

def test_get_plant_tips_not_found():
    service = create_service()

    service._repo.get_plant_template.return_value = []

    result = service.get_plant_tips(1)

    assert result is None


def test_get_plant_tips_json_success():
    service = create_service()

    service._repo.get_plant_template.return_value = [
        {
            "species_name": "Фикус",
            "tips": '["Поливать","Освещать"]',
            "symptoms": ""
        }
    ]

    result = service.get_plant_tips(1)

    assert result["species_name"] == "Фикус"
    assert len(result["tips"]) == 2


def test_get_plant_tips_fallback_parser():
    service = create_service()

    service._repo.get_plant_template.return_value = [
        {
            "species_name": "Кактус",
            "tips": "Поливать редко|Много света",
            "symptoms": ""
        }
    ]

    result = service.get_plant_tips(1)

    assert len(result["tips"]) == 2
    assert result["tips"][0] == "Поливать редко"


def test_get_plant_tips_symptoms_parser():
    service = create_service()

    service._repo.get_plant_template.return_value = [
        {
            "species_name": "Фикус",
            "tips": "[]",
            "symptoms": "Желтые листья:перелив->Уменьшить полив"
        }
    ]

    result = service.get_plant_tips(1)

    assert len(result["symptoms"]) == 1
    assert result["symptoms"][0]["symptom"] == "Желтые листья"
    assert result["symptoms"][0]["cause"] == "перелив"
    assert result["symptoms"][0]["advice"] == "Уменьшить полив"


def test_get_plant_tips_simple_symptom():
    service = create_service()

    service._repo.get_plant_template.return_value = [
        {
            "species_name": "Фикус",
            "tips": "[]",
            "symptoms": "Сухие листья"
        }
    ]

    result = service.get_plant_tips(1)

    assert result["symptoms"][0]["symptom"] == "Сухие листья"
    assert result["symptoms"][0]["cause"] == ""