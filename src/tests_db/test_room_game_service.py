"""
Автоматизированные тесты RoomGameService.

Проверяем:
- загрузку и сохранение состояния комнаты;
- посадку растения в горшок;
- полив растения;
- перемещение горшка;
- обработку болезней, смерти и лечения;
- рост растения;
- игровые side effects: достижения, задания, повышение уровня.

Инструменты:
- pytest
- unittest.mock
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

SRC_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SRC_DIR))

from backend.database_full.service import room_game_service as room_module
from backend.database_full.service.room_game_service import RoomGameService


NOW = 1_700_000_000_000


def create_service():
    service = RoomGameService()

    service.game_repo = Mock()
    service.plant_repo = Mock()
    service.user_repo = Mock()

    service.plant_repo.get_template_by_species_id.return_value = None
    service._now_ms = Mock(return_value=NOW)

    return service


def make_bundle(slot_data=None, current_level=1, achievements=None):
    return {
        "slotData": slot_data or {},
        "currentLevel": current_level,
        "achievements": achievements or {}
    }


# =========================
# Базовые внутренние методы
# =========================

def test_resolve_species_id_valid():
    service = create_service()

    assert service._resolve_species_id("1") == 1
    assert service._resolve_species_id(2) == 2
    assert service._resolve_species_id("3") == 3


def test_resolve_species_id_invalid_returns_default():
    service = create_service()

    assert service._resolve_species_id(None) == 1
    assert service._resolve_species_id("abc") == 1
    assert service._resolve_species_id(99) == 1


def test_species_intervals_from_template():
    service = create_service()

    service.plant_repo.get_template_by_species_id.return_value = {
        "water_interval_min": 5,
        "water_interval_max": 8
    }

    result = service._species_intervals(1)

    assert result["min"] == 5
    assert result["max"] == 8


def test_species_intervals_fallback():
    service = create_service()

    service.plant_repo.get_template_by_species_id.return_value = None

    result = service._species_intervals(1)

    assert result["min"] == 1
    assert result["max"] == 2


def test_is_plant_dead():
    assert RoomGameService._is_plant_dead(None) is False
    assert RoomGameService._is_plant_dead({}) is False
    assert RoomGameService._is_plant_dead({"disease": "__dead__"}) is True
    assert RoomGameService._is_plant_dead({"diseaseType": "dead"}) is True


def test_ensure_mistake_categories_create_default():
    service = create_service()

    data = {}

    result = service._ensure_mistake_categories(data)

    assert result == {
        "water": False,
        "place": False,
        "pot": False
    }


def test_record_mistake_category_water():
    service = create_service()

    data = {}

    service._record_mistake_category(data, "water")

    assert data["mistakeCategories"]["water"] is True
    assert data["mistakeCategories"]["place"] is False
    assert data["mistakeCategories"]["pot"] is False


def test_ms_since_last_water_without_last_water():
    service = create_service()

    result = service._ms_since_last_water({}, NOW)

    assert result == float("inf")


def test_ms_since_last_water_success():
    service = create_service()

    result = service._ms_since_last_water(
        {"lastWateredAt": NOW - 1000},
        NOW
    )

    assert result == 1000


def test_ms_without_water_from_planted_at():
    service = create_service()

    result = service._ms_without_water(
        {"plantedAt": NOW - 5000},
        NOW
    )

    assert result == 5000


def test_watering_gap_ms_priority_gap_ms():
    service = create_service()

    result = service._watering_gap_ms({
        "gapMs": 100,
        "intervalMs": 200
    })

    assert result == 100


def test_record_watering_gap_keeps_last_five():
    service = create_service()

    data = {
        "lastWateredAt": NOW - 1000,
        "wateringHistory": [
            {"gapMs": 1},
            {"gapMs": 2},
            {"gapMs": 3},
            {"gapMs": 4},
            {"gapMs": 5},
        ]
    }

    service._record_watering_gap(data, NOW)

    assert len(data["wateringHistory"]) == 5
    assert data["wateringHistory"][-1]["gapMs"] == 1000


def test_count_recent_fast_waterings():
    service = create_service()

    data = {
        "wateringHistory": [
            {"gapMs": service.DAY_MS * 2},
            {"gapMs": 100},
            {"gapMs": 200},
        ]
    }

    result = service._count_recent_fast_waterings(data, 1)

    assert result == 2


def test_has_overwater_risk_true():
    service = create_service()

    data = {
        "wateringHistory": [
            {"gapMs": 100},
            {"gapMs": 200},
        ]
    }

    assert service._has_overwater_risk(data, 1) is True


def test_has_overwater_death_risk_true():
    service = create_service()

    data = {
        "wateringHistory": [
            {"gapMs": 100},
            {"gapMs": 200},
            {"gapMs": 300},
        ]
    }

    assert service._has_overwater_death_risk(data, 1) is True


def test_is_watering_on_time_first_watering():
    service = create_service()

    data = {
        "plantedAt": NOW - 1000
    }

    result = service._is_watering_on_time(data, 1, NOW)

    assert result is True


def test_is_watering_on_time_between_min_and_max():
    service = create_service()

    data = {
        "lastWateredAt": NOW - service.DAY_MS
    }

    result = service._is_watering_on_time(data, 1, NOW)

    assert result is True


# =========================
# Болезни, лечение и смерть
# =========================

def test_get_location_disease_big_pot_for_spathiphyllum():
    service = create_service()

    result = service._get_location_disease_for_slot(
        1,
        "desk-left",
        {"pot": 3}
    )

    assert result == service.PLANT_DISEASES[1]["big_pot"]


def test_get_location_disease_too_light():
    service = create_service()

    result = service._get_location_disease_for_slot(
        1,
        "windowsill-1",
        {"pot": 1}
    )

    assert result == service.PLANT_DISEASES[1]["too_light"]


def test_get_location_disease_cactus_too_dark():
    service = create_service()

    result = service._get_location_disease_for_slot(
        2,
        "desk-right-1",
        {"pot": 1}
    )

    assert result == service.PLANT_DISEASES[2]["too_dark"]


def test_apply_plant_disease_success():
    service = create_service()

    data = {
        "plant": "1",
        "stage": 1,
        "hasDisease": False
    }
    events = []

    result = service._apply_plant_disease(
        data,
        1,
        "under_watered",
        "water",
        events
    )

    assert result is True
    assert data["hasDisease"] is True
    assert data["hadMistakes"] is True
    assert data["diseaseType"] == "under_watered"
    assert events[0]["type"] == "disease"


def test_apply_plant_disease_skips_dead_plant():
    service = create_service()

    data = {
        "plant": "1",
        "stage": 1,
        "disease": "__dead__"
    }
    events = []

    result = service._apply_plant_disease(
        data,
        1,
        "under_watered",
        "water",
        events
    )

    assert result is False
    assert events == []


def test_apply_plant_death_success():
    service = create_service()

    data = {
        "plant": "1",
        "stage": 1
    }
    events = []

    service._apply_plant_death(
        data,
        events,
        notification_cause="under_watered"
    )

    assert data["disease"] == "__dead__"
    assert data["diseaseType"] == "dead"
    assert events[0]["type"] == "death"
    assert events[1]["type"] == "achievement_check"


def test_try_heal_underwater_on_water_success():
    service = create_service()

    data = {
        "hasDisease": True,
        "disease": service.PLANT_DISEASES[1]["under_watered"],
        "diseaseType": "under_watered"
    }
    events = []

    result = service._try_heal_underwater_on_water(data, 1, events)

    assert result is True
    assert data["hasDisease"] is False
    assert data["disease"] is None
    assert events[0]["type"] == "healed"


def test_try_heal_overwater_on_dry_success():
    service = create_service()

    data = {
        "hasDisease": True,
        "disease": service.PLANT_DISEASES[1]["overwatered"],
        "diseaseType": "overwatered",
        "lastWateredAt": NOW - service.DAY_MS,
        "wateringHistory": [{"gapMs": 100}]
    }
    events = []

    result = service._try_heal_overwater_on_dry(
        data,
        1,
        NOW,
        events
    )

    assert result is True
    assert data["hasDisease"] is False
    assert data["wateringHistory"] == []
    assert events[0]["type"] == "healed"


# =========================
# Рост растения
# =========================

def test_try_advance_to_sprout_success():
    service = create_service()

    data = {
        "plant": "1",
        "stage": 0,
        "plantedAt": NOW - service.DAY_MS - 1,
        "lastWateredAt": NOW - 1000
    }
    events = []

    result = service._try_advance_to_sprout(
        "slot1",
        data,
        1,
        events
    )

    assert result is True
    assert data["stage"] == 1
    assert events[0]["type"] == "sprout"


def test_apply_growth_to_bloom_success():
    service = create_service()

    data = {
        "plant": "1",
        "stage": 1,
        "plantedAt": NOW - service.DAY_MS * 8,
        "lastWateredAt": NOW - service.DAY_MS,
        "hasDisease": False,
        "wateringHistory": []
    }
    events = []

    service._apply_growth_from_time(
        "slot1",
        data,
        1,
        events
    )

    assert data["stage"] == 2
    assert any(event["type"] == "bloom" for event in events)


def test_apply_growth_bloom_blocked_by_disease():
    service = create_service()

    data = {
        "plant": "1",
        "stage": 1,
        "plantedAt": NOW - service.DAY_MS * 8,
        "lastWateredAt": NOW - service.DAY_MS,
        "hasDisease": True
    }
    events = []

    service._apply_growth_from_time(
        "slot1",
        data,
        1,
        events
    )

    assert data["stage"] == 1
    assert events[0]["type"] == "bloom_blocked"


# =========================
# Side effects
# =========================

def test_collect_side_effects_level_up():
    service = create_service()

    service.user_repo.get_profile.return_value = {
        "current_level": 2
    }

    events = [
        {
            "type": "achievement_check",
            "event": "perfect_growth",
            "plantId": "1"
        }
    ]

    with patch.object(
        room_module.challenge_interface,
        "record_perfect_growth",
        return_value={"new_achievements": [{"id": 1}]}
    ), patch.object(
        room_module.level_quest_interface,
        "check_quests",
        return_value={
            "leveled_up": True,
            "new_level": 2,
            "reward": {"type": "new_pot"}
        }
    ):
        result = service._collect_side_effects("user1", events)

    assert result["newAchievements"] == [{"id": 1}]
    assert result["levelUp"]["newLevel"] == 2
    assert result["currentLevel"] == 2


def test_collect_side_effects_quest_update():
    service = create_service()

    events = []

    with patch.object(
        room_module.level_quest_interface,
        "check_quests",
        return_value={
            "quests_completed": 1
        }
    ):
        result = service._collect_side_effects("user1", events)

    assert result["questUpdate"]["completedQuests"] == 1


# =========================
# Описание и лечение
# =========================

def test_mark_read_description():
    service = create_service()

    service._load_bundle = Mock(return_value=make_bundle())
    service._save_bundle = Mock()

    with patch.object(
        room_module.level_quest_interface,
        "check_quests",
        return_value={"success": True}
    ):
        result = service.mark_read_description("user1")

    assert result["success"] is True
    assert result["questUpdate"] == {"success": True}

    saved_bundle = service._save_bundle.call_args[0][1]
    assert saved_bundle["achievements"]["__readDescriptionDone"] is True


def test_mark_healed():
    service = create_service()

    service._load_bundle = Mock(return_value=make_bundle())
    service._save_bundle = Mock()

    with patch.object(
        room_module.level_quest_interface,
        "trigger_quest_check",
        return_value={"success": True},
        create=True
    ):
        service.mark_healed("user1")

    saved_bundle = service._save_bundle.call_args[0][1]

    assert saved_bundle["achievements"]["__healedPlant"] is True
# =========================
# Посадка растения
# =========================

def test_plant_in_slot_without_pot():
    service = create_service()

    service._load_bundle = Mock(return_value=make_bundle({
        "slot1": {}
    }))

    result = service.plant_in_slot("user1", "slot1", 1)

    assert result["success"] is False
    assert result["error"] == "Сначала поставьте горшок"


def test_plant_in_slot_success():
    service = create_service()

    service._load_bundle = Mock(return_value=make_bundle({
        "slot1": {
            "pot": 1
        }
    }))
    service._save_bundle = Mock()
    service._collect_side_effects = Mock(return_value={
        "newAchievements": [],
        "questUpdate": None,
        "levelUp": None
    })

    result = service.plant_in_slot("user1", "slot1", 1)

    assert result["success"] is True
    assert result["slotName"] == "slot1"
    assert result["slotData"]["plant"] == "1"
    assert result["slotData"]["stage"] == 0
    assert result["events"][0]["type"] == "planted"

    service.user_repo.increment_stat.assert_called_once_with(
        "user1",
        "total_plants_grown"
    )
    service._save_bundle.assert_called_once()


# =========================
# Полив растения
# =========================

def test_water_slot_without_plant():
    service = create_service()

    service._load_bundle = Mock(return_value=make_bundle({
        "slot1": {
            "pot": 1
        }
    }))

    result = service.water_slot("user1", "slot1")

    assert result["success"] is False
    assert result["error"] == "Нельзя полить это растение"


def test_water_slot_dead_plant():
    service = create_service()

    service._load_bundle = Mock(return_value=make_bundle({
        "slot1": {
            "pot": 1,
            "plant": "1",
            "disease": "__dead__"
        }
    }))

    result = service.water_slot("user1", "slot1")

    assert result["success"] is False


def test_water_slot_success():
    service = create_service()

    service._load_bundle = Mock(return_value=make_bundle({
        "slot1": {
            "pot": 1,
            "plant": "1",
            "stage": 0,
            "plantedAt": NOW,
            "lastWateredAt": None,
            "totalWaterings": 0,
            "hasDisease": False,
            "wateringHistory": []
        }
    }))
    service._save_bundle = Mock()
    service._collect_side_effects = Mock(return_value={
        "newAchievements": [],
        "questUpdate": None,
        "levelUp": None
    })

    result = service.water_slot("user1", "slot1")

    assert result["success"] is True
    assert result["slotData"]["totalWaterings"] == 1
    assert result["slotData"]["lastWateredAt"] == NOW
    assert any(event["type"] == "watered" for event in result["events"])

    service.user_repo.increment_stat.assert_called_once_with(
        "user1",
        "total_waterings"
    )
    service._save_bundle.assert_called_once()


def test_water_slot_too_early_warning():
    service = create_service()

    service._load_bundle = Mock(return_value=make_bundle({
        "slot1": {
            "pot": 1,
            "plant": "1",
            "stage": 1,
            "plantedAt": NOW - service.DAY_MS,
            "lastWateredAt": NOW - 1000,
            "totalWaterings": 1,
            "hasDisease": False,
            "wateringHistory": []
        }
    }))
    service._save_bundle = Mock()
    service._collect_side_effects = Mock(return_value={
        "newAchievements": [],
        "questUpdate": None,
        "levelUp": None
    })

    result = service.water_slot("user1", "slot1")

    assert result["success"] is True
    assert any(event["type"] == "overwater_warning" for event in result["events"])


# =========================
# Tick
# =========================

def test_tick_without_slots():
    service = create_service()

    service._load_bundle = Mock(return_value=make_bundle({}))
    service._save_bundle = Mock()
    service._collect_side_effects = Mock(return_value={
        "newAchievements": [],
        "questUpdate": None,
        "levelUp": None
    })

    result = service.tick("user1")

    assert result["success"] is True
    assert result["updatedSlots"] == {}
    assert result["events"] == []
    service._save_bundle.assert_called_once()


def test_tick_updates_sprout():
    service = create_service()

    service._load_bundle = Mock(return_value=make_bundle({
        "slot1": {
            "pot": 1,
            "plant": "1",
            "stage": 0,
            "plantedAt": NOW - service.DAY_MS - 1,
            "lastWateredAt": NOW - 1000,
            "hasDisease": False,
            "wateringHistory": []
        }
    }))
    service._save_bundle = Mock()
    service._collect_side_effects = Mock(return_value={
        "newAchievements": [],
        "questUpdate": None,
        "levelUp": None
    })

    result = service.tick("user1")

    assert result["success"] is True
    assert "slot1" in result["updatedSlots"]
    assert result["updatedSlots"]["slot1"]["stage"] == 1
    assert any(event["type"] == "sprout" for event in result["events"])


# =========================
# Перемещение горшка
# =========================

def test_move_slot_source_not_found():
    service = create_service()

    service._load_bundle = Mock(return_value=make_bundle({}))

    result = service.move_slot(
        "user1",
        "slot1",
        "slot2"
    )

    assert result["success"] is False
    assert result["error"] == "Источник не найден"


def test_move_slot_target_busy():
    service = create_service()

    service._load_bundle = Mock(return_value=make_bundle({
        "slot1": {
            "pot": 1,
            "plant": "1"
        },
        "slot2": {
            "pot": 2
        }
    }))

    result = service.move_slot(
        "user1",
        "slot1",
        "slot2"
    )

    assert result["success"] is False
    assert result["error"] == "Место уже занято"


def test_move_slot_success():
    service = create_service()

    service._load_bundle = Mock(return_value=make_bundle({
        "slot1": {
            "pot": 1,
            "plant": "1",
            "stage": 0,
            "plantedAt": NOW,
            "lastWateredAt": None,
            "hasDisease": False
        }
    }))
    service._save_bundle = Mock()
    service._collect_side_effects = Mock(return_value={
        "newAchievements": [],
        "questUpdate": None,
        "levelUp": None
    })

    result = service.move_slot(
        "user1",
        "slot1",
        "slot2"
    )

    assert result["success"] is True
    assert result["fromSlot"] == "slot1"
    assert result["toSlot"] == "slot2"
    assert "slot1" not in result["slotData"]
    assert "slot2" in result["slotData"]
    assert result["events"][0]["type"] == "moved"

    service._save_bundle.assert_called_once()