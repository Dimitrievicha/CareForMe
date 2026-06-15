"""
Игровая логика комнаты (сад DB_TESTING_REPORT.md slotData).

Правила роста, полива, болезней и смерти растений живут здесь,
DB_TESTING_REPORT.md не во frontend/js/room.js.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..interface.challenge_interface import challenge_interface
from ..interface.level_quest_interface import level_quest_interface
from ..repository.game_repository import GameRepository
from ..repository.plant_repository import PlantRepository
from ..repository.user_repository import UserRepository


class RoomGameService:
    DAY_MS = 24 * 60 * 60 * 1000

    OVERWATER_MIN_FAST_POLIVS = 2
    OVERWATER_DEATH_MIN_FAST_POLIVS = 3

    PLANT_GROWTH_DAYS = {
        1: {"seedToSprout": 1, "plantToBloom": 7},
        2: {"seedToSprout": 4, "plantToBloom": 21},
        3: {"seedToSprout": 2, "plantToBloom": 14},
    }

    PLANT_WATER_INTERVALS_DAYS = {
        1: {"min": 1, "max": 2},
        2: {"min": 7, "max": 10},
        3: {"min": 3, "max": 4},
    }

    PLANT_SICK_UNTIL_DEATH_DAYS = {
        1: 3,
        2: 7,
        3: 5,
    }

    SLOT_LIGHT = {
        "windowsill-1": "high",
        "windowsill-2": "high",
        "windowsill-3": "medium",
        "desk-left": "medium",
        "desk-right-1": "low",
        "desk-right-2": "low",
    }

    PLANT_DISEASES = {
        1: {
            "too_light": "🍃 Листья желтеют — солнечный ожог",
            "big_pot": "🍃 Не цветёт — слишком большой горшок",
            "under_watered": "🍃 Сохнут кончики листьев — недостаточный полив",
            "overwatered": "🍃 Листья желтеют — перелив",
        },
        2: {
            "too_dark": "🌵 Вытягивание и бледность стебля — не хватает света",
            "no_flower": "🌵 Нет цветения — причина DB_TESTING_REPORT.md нехватке света",
            "under_watered": "🌵 Сморщенный стебель — недостаточный полив",
            "overwatered": "🌵 Сморщенный стебель — перелив или застой воды",
        },
        3: {
            "too_light": "🍂 Пятна на листьях — солнечный ожог",
            "under_watered": "🍂 Желтеют листья — недостаточный полив",
            "overwatered": "🍂 Увядание листьев — перелив",
        },
    }

    LOCATION_DISEASE_TYPES = {"too_light", "too_dark", "no_flower", "big_pot"}
    WATER_DISEASE_TYPES = {"under_watered", "overwatered"}

    MISTAKE_CATEGORY_BY_SOURCE = {
        "water": "water",
        "location": "place",
        "pot": "pot",
    }

    LEVEL_REWARDS = {
        2: "🎉 Уровень 2! Горшок «С рисунком» теперь доступен!",
        3: "🎉 Уровень 3! Кактус теперь доступен для посадки!",
        4: "🎉 Уровень 4! Лейка «Розовая» теперь доступна!",
        5: "🎉 Уровень 5! Фикус теперь доступен для посадки!",
        6: "🎉 Уровень 6! Горшок «Большой» теперь доступен!",
    }

    ACHIEVEMENT_FRONT_IDS = {
        "grow_to_maturity_perfect": "caring_parent",
        "first_wither": "all_lost",
        "first_negative_effect": "oops_error",
        "grow_all_species": "collector",
        "daily_streak": "patient_gardener",
        "reach_level": "flora_guard",
    }

    def __init__(self) -> None:
        self.game_repo = GameRepository()
        self.plant_repo = PlantRepository()
        self.user_repo = UserRepository()

    def _now_ms(self) -> int:
        return int(datetime.now().timestamp() * 1000)

    def _load_bundle(self, user_id: str) -> Dict[str, Any]:
        state = self.game_repo.load_game_state(user_id) or {}
        profile = self.user_repo.get_profile(user_id) or {}
        return {
            "slotData": deepcopy(state.get("slotData") or {}),
            "currentLevel": state.get("currentLevel") or profile.get("current_level") or 1,
            "achievements": deepcopy(state.get("achievements") or {}),
        }

    def _save_bundle(self, user_id: str, bundle: Dict[str, Any]) -> None:
        self.game_repo.save_game_state(
            user_id,
            bundle["slotData"],
            bundle["currentLevel"],
            bundle["achievements"],
            datetime.now().isoformat(),
        )

    def _resolve_species_id(self, plant_key: Any) -> int:
        try:
            species_id = int(plant_key)
        except (TypeError, ValueError):
            return 1
        return species_id if 1 <= species_id <= 3 else 1

    def _species_intervals(self, species_id: int) -> Dict[str, int]:
        template = self.plant_repo.get_template_by_species_id(species_id)
        fallback = self.PLANT_WATER_INTERVALS_DAYS.get(species_id, {"min": 1, "max": 2})
        if not template:
            return fallback
        return {
            "min": template.get("water_interval_min") or fallback["min"],
            "max": template.get("water_interval_max") or fallback["max"],
        }

    def _get_water_min_ms(self, species_id: int) -> int:
        return self._species_intervals(species_id)["min"] * self.DAY_MS

    def _get_water_max_ms(self, species_id: int) -> int:
        return self._species_intervals(species_id)["max"] * self.DAY_MS

    def _get_seedling_ms(self, species_id: int) -> int:
        growth = self.PLANT_GROWTH_DAYS.get(species_id, self.PLANT_GROWTH_DAYS[1])
        return growth["seedToSprout"] * self.DAY_MS

    def _get_bloom_ms(self, species_id: int) -> int:
        growth = self.PLANT_GROWTH_DAYS.get(species_id, self.PLANT_GROWTH_DAYS[1])
        return growth["plantToBloom"] * self.DAY_MS

    def _get_sick_until_death_ms(self, species_id: int) -> int:
        days = self.PLANT_SICK_UNTIL_DEATH_DAYS.get(species_id, self.PLANT_SICK_UNTIL_DEATH_DAYS[1])
        return days * self.DAY_MS

    @staticmethod
    def _is_plant_dead(data: Optional[Dict[str, Any]]) -> bool:
        if not data:
            return False
        return data.get("disease") == "__dead__" or data.get("diseaseType") == "dead"

    def _ensure_mistake_categories(self, data: Dict[str, Any]) -> Dict[str, bool]:
        if not data.get("mistakeCategories"):
            data["mistakeCategories"] = {"water": False, "place": False, "pot": False}
        return data["mistakeCategories"]

    def _record_mistake_category(self, data: Dict[str, Any], source: str) -> None:
        category_key = self.MISTAKE_CATEGORY_BY_SOURCE.get(source)
        if category_key:
            self._ensure_mistake_categories(data)[category_key] = True

    def _ms_since_last_water(self, data: Dict[str, Any], now: int) -> float:
        last = data.get("lastWateredAt")
        if not last:
            return float("inf")
        return max(0, now - last)

    def _ms_without_water(self, data: Dict[str, Any], now: int) -> int:
        if data.get("lastWateredAt"):
            return max(0, now - data["lastWateredAt"])
        if data.get("plantedAt"):
            return max(0, now - data["plantedAt"])
        return 0

    def _watering_gap_ms(self, entry: Dict[str, Any]) -> float:
        if entry.get("gapMs") is not None:
            return entry["gapMs"]
        if entry.get("intervalMs") is not None:
            return entry["intervalMs"]
        return float("inf")

    def _count_recent_fast_waterings(self, data: Dict[str, Any], species_id: int) -> int:
        history = data.get("wateringHistory") or []
        min_ms = self._get_water_min_ms(species_id)
        return sum(1 for entry in history[-3:] if self._watering_gap_ms(entry) < min_ms)

    def _has_overwater_risk(self, data: Dict[str, Any], species_id: int) -> bool:
        return self._count_recent_fast_waterings(data, species_id) >= self.OVERWATER_MIN_FAST_POLIVS

    def _has_overwater_death_risk(self, data: Dict[str, Any], species_id: int) -> bool:
        recent = (data.get("wateringHistory") or [])[-self.OVERWATER_DEATH_MIN_FAST_POLIVS :]
        if len(recent) < self.OVERWATER_DEATH_MIN_FAST_POLIVS:
            return False
        min_ms = self._get_water_min_ms(species_id)
        return all(self._watering_gap_ms(entry) < min_ms for entry in recent)

    def _is_still_within_min_water_interval(self, data: Dict[str, Any], species_id: int, now: int) -> bool:
        if not data.get("lastWateredAt"):
            return False
        return self._ms_since_last_water(data, now) < self._get_water_min_ms(species_id)

    def _is_watering_on_time(self, data: Dict[str, Any], species_id: int, now: int) -> bool:
        min_ms = self._get_water_min_ms(species_id)
        max_ms = self._get_water_max_ms(species_id)
        if not data.get("lastWateredAt"):
            age_ms = now - (data.get("plantedAt") or now)
            return age_ms <= max_ms
        since_ms = now - data["lastWateredAt"]
        return min_ms <= since_ms <= max_ms

    def _has_regular_watering(self, data: Dict[str, Any], species_id: int, now: int) -> bool:
        if not data.get("lastWateredAt"):
            return False
        return self._ms_since_last_water(data, now) <= self._get_water_max_ms(species_id)

    def _record_watering_gap(self, data: Dict[str, Any], now: int) -> None:
        history = data.setdefault("wateringHistory", [])
        if data.get("lastWateredAt"):
            history.append({"time": now, "gapMs": now - data["lastWateredAt"]})
            if len(history) > 5:
                del history[0]

    def _get_disease_type_from_message(self, species_id: int, disease_msg: Optional[str]) -> Optional[str]:
        diseases = self.PLANT_DISEASES.get(species_id, {})
        if not disease_msg:
            return None
        for disease_type, message in diseases.items():
            if message == disease_msg:
                return disease_type
        return None

    def _is_location_based_disease(self, species_id: int, disease_text: Optional[str]) -> bool:
        if not disease_text or disease_text == "__dead__":
            return False
        disease_type = self._get_disease_type_from_message(species_id, disease_text)
        return disease_type in self.LOCATION_DISEASE_TYPES if disease_type else False

    def _get_location_disease_for_slot(
        self, species_id: int, slot_name: str, data: Dict[str, Any]
    ) -> Optional[str]:
        diseases = self.PLANT_DISEASES.get(species_id, {})
        slot_light = self.SLOT_LIGHT.get(slot_name)

        if species_id == 1 and data.get("pot") == 3:
            return diseases.get("big_pot")

        if not slot_light:
            return None

        if species_id == 1 and slot_light == "high":
            return diseases.get("too_light")
        if species_id == 2:
            if slot_light == "low":
                return diseases.get("too_dark")
            if slot_light != "high":
                return diseases.get("no_flower")
        if species_id == 3 and slot_light == "high":
            return diseases.get("too_light")
        return None

    def _apply_plant_disease(
        self,
        data: Dict[str, Any],
        species_id: int,
        disease_type: str,
        source: str,
        events: List[Dict[str, Any]],
        *,
        trigger_achievement: bool = True,
    ) -> bool:
        message = self.PLANT_DISEASES.get(species_id, {}).get(disease_type)
        if not message or self._is_plant_dead(data) or data.get("hasDisease") or data.get("stage", -1) < 1:
            return False

        data["hasDisease"] = True
        data["hadMistakes"] = True
        data["disease"] = message
        data["diseaseType"] = disease_type
        data["diseaseSource"] = source
        data["diseaseStartTime"] = self._now_ms()
        self._record_mistake_category(data, source)
        events.append({"type": "disease", "diseaseType": disease_type, "message": message})
        if trigger_achievement:
            events.append({"type": "achievement_check", "event": "mistake", "plantId": data.get("plant")})
        return True

    def _apply_plant_death(
        self,
        data: Dict[str, Any],
        events: List[Dict[str, Any]],
        *,
        notification_cause: Optional[str] = None,
    ) -> None:
        if not data.get("plant") or self._is_plant_dead(data):
            return
        data["hasDisease"] = True
        data["hadMistakes"] = True
        data["disease"] = "__dead__"
        data["diseaseType"] = "dead"
        data["diseaseSource"] = "neglect"
        data["devManualState"] = False
        events.append(
            {
                "type": "death",
                "cause": notification_cause,
                "plantId": data.get("plant"),
            }
        )
        events.append({"type": "achievement_check", "event": "death", "plantId": data.get("plant")})

    def _try_heal_underwater_on_water(self, data: Dict[str, Any], species_id: int, events: List[Dict[str, Any]]) -> bool:
        if not data.get("hasDisease") or self._is_plant_dead(data):
            return False
        under_msg = self.PLANT_DISEASES.get(species_id, {}).get("under_watered")
        if not under_msg or data.get("disease") != under_msg:
            return False
        data["hasDisease"] = False
        data["disease"] = None
        data["diseaseType"] = None
        data["diseaseSource"] = None
        data["diseaseStartTime"] = None
        events.append({"type": "healed"})
        return True

    def _try_heal_overwater_on_dry(self, data: Dict[str, Any], species_id: int, now: int, events: List[Dict[str, Any]]) -> bool:
        if not data.get("hasDisease") or self._is_plant_dead(data):
            return False
        if data.get("diseaseType") != "overwatered":
            over_msg = self.PLANT_DISEASES.get(species_id, {}).get("overwatered")
            if not over_msg or data.get("disease") != over_msg:
                return False
        if not data.get("lastWateredAt"):
            return False
        if self._ms_since_last_water(data, now) < self._get_water_min_ms(species_id):
            return False
        data["hasDisease"] = False
        data["disease"] = None
        data["diseaseType"] = None
        data["diseaseSource"] = None
        data["diseaseStartTime"] = None
        data["wateringHistory"] = []
        events.append({"type": "healed"})
        return True

    def _get_bloom_block_reason(self, data: Dict[str, Any], species_id: int, now: int) -> Optional[str]:
        if data.get("hasDisease"):
            return "не может расцвести из-за болезни"
        if self._has_overwater_risk(data, species_id):
            return "не может расцвести — слишком частый полив"
        if not self._has_regular_watering(data, species_id, now):
            return "не может расцвести — нужен регулярный полив"
        return None

    def _try_advance_to_sprout(
        self, slot_name: str, data: Dict[str, Any], species_id: int, events: List[Dict[str, Any]]
    ) -> bool:
        if not data.get("plant") or not data.get("plantedAt") or self._is_plant_dead(data):
            return False
        if data.get("stage", -1) != 0 or not data.get("lastWateredAt"):
            return False
        if self._now_ms() - data["plantedAt"] < self._get_seedling_ms(species_id):
            return False
        data["stage"] = 1
        data["sproutedAt"] = self._now_ms()
        events.append({"type": "sprout", "slotName": slot_name, "speciesId": species_id})
        return True

    def _apply_growth_from_time(
        self, slot_name: str, data: Dict[str, Any], species_id: int, events: List[Dict[str, Any]]
    ) -> None:
        if not data.get("plant") or not data.get("plantedAt") or self._is_plant_dead(data):
            return

        now = self._now_ms()
        ms_since_planted = now - data["plantedAt"]
        bloom_ms = self._get_bloom_ms(species_id)

        if ms_since_planted >= bloom_ms and data.get("stage", -1) < 2:
            bloom_block = self._get_bloom_block_reason(data, species_id, now)
            if not bloom_block and data.get("stage", -1) >= 1:
                data["stage"] = 2
                data["bloomedAt"] = data.get("bloomedAt") or (data["plantedAt"] + bloom_ms)
                events.append({"type": "bloom", "slotName": slot_name, "speciesId": species_id})
                events.append(
                    {
                        "type": "achievement_check",
                        "event": "perfect_growth",
                        "plantId": data.get("plant"),
                    }
                )
                events.append({"type": "achievement_check", "event": "species_collected"})
            elif bloom_block:
                events.append({"type": "bloom_blocked", "reason": bloom_block})
        elif data.get("stage", -1) < 1:
            self._try_advance_to_sprout(slot_name, data, species_id, events)

    def _check_plant_death_from_sickness(
        self, slot_name: str, data: Dict[str, Any], species_id: int, events: List[Dict[str, Any]]
    ) -> None:
        if not data.get("plant") or data.get("stage", -1) < 1:
            return
        if data.get("devManualState") or self._is_plant_dead(data) or not data.get("hasDisease"):
            return
        disease_type = data.get("diseaseType")
        if disease_type in self.WATER_DISEASE_TYPES or disease_type not in self.LOCATION_DISEASE_TYPES:
            return
        if not data.get("diseaseStartTime"):
            data["diseaseStartTime"] = self._now_ms()
            return
        if self._now_ms() - data["diseaseStartTime"] < self._get_sick_until_death_ms(species_id):
            return
        self._apply_plant_death(data, events)

    def _check_watering_health(
        self, slot_name: str, data: Dict[str, Any], species_id: int, events: List[Dict[str, Any]]
    ) -> None:
        if not data.get("plant") or data.get("devManualState") or self._is_plant_dead(data):
            return
        if data.get("stage", -1) < 1:
            return

        now = self._now_ms()
        self._try_heal_overwater_on_dry(data, species_id, now, events)

        max_ms = self._get_water_max_ms(species_id)
        dry_ms = self._ms_without_water(data, now)
        drought_death_ms = max_ms * 2

        if self._has_overwater_death_risk(data, species_id) and self._is_still_within_min_water_interval(
            data, species_id, now
        ):
            self._record_mistake_category(data, "water")
            self._apply_plant_death(data, events, notification_cause="overwatered")
        elif (
            self._has_overwater_risk(data, species_id)
            and self._is_still_within_min_water_interval(data, species_id, now)
            and self.PLANT_DISEASES.get(species_id, {}).get("overwatered")
        ):
            self._apply_plant_disease(data, species_id, "overwatered", "water", events)
        elif dry_ms > drought_death_ms:
            self._record_mistake_category(data, "water")
            self._apply_plant_death(data, events, notification_cause="under_watered")
        elif dry_ms > max_ms and self.PLANT_DISEASES.get(species_id, {}).get("under_watered"):
            self._record_mistake_category(data, "water")
            if not data.get("hasDisease"):
                self._apply_plant_disease(data, species_id, "under_watered", "water", events)

    def _check_location_disease(
        self, slot_name: str, data: Dict[str, Any], species_id: int, events: List[Dict[str, Any]]
    ) -> None:
        if not data.get("plant") or data.get("stage", -1) < 1:
            return
        if data.get("devManualState") or self._is_plant_dead(data):
            return

        disease_msg = self._get_location_disease_for_slot(species_id, slot_name, data)
        if disease_msg:
            mistake_source = (
                "pot"
                if species_id == 1 and data.get("pot") == 3 and disease_msg == self.PLANT_DISEASES[1]["big_pot"]
                else "location"
            )
            self._record_mistake_category(data, mistake_source)
            if not data.get("hasDisease"):
                disease_type = self._get_disease_type_from_message(species_id, disease_msg)
                if disease_type:
                    self._apply_plant_disease(data, species_id, disease_type, mistake_source, events)
        elif (
            data.get("hasDisease")
            and self._is_location_based_disease(species_id, data.get("disease"))
            and data.get("stage", -1) >= 1
        ):
            data["hasDisease"] = False
            data["disease"] = None
            data["diseaseType"] = None
            data["diseaseSource"] = None
            data["diseaseStartTime"] = None
            events.append({"type": "healed", "fromLocation": True})

    def _process_slot(
        self, slot_name: str, data: Dict[str, Any], events: List[Dict[str, Any]], *, include_growth: bool = True
    ) -> None:
        if not data or not data.get("plant"):
            return
        species_id = self._resolve_species_id(data.get("plant"))
        self._check_watering_health(slot_name, data, species_id, events)
        self._check_location_disease(slot_name, data, species_id, events)
        self._check_plant_death_from_sickness(slot_name, data, species_id, events)
        if include_growth:
            self._apply_growth_from_time(slot_name, data, species_id, events)

    def _collect_side_effects(self, user_id: str, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        side_effects: Dict[str, Any] = {
            "newAchievements": [],
            "questUpdate": None,
            "levelUp": None,
        }

        for event in events:
            event_type = event.get("type")
            if event_type == "healed":
                self.mark_healed(user_id)
            if event_type == "achievement_check":
                ach_event = event.get("event")
                plant_id = event.get("plantId")
                # Пропускаем, если plant_id не передан или это 'slot'
                if not plant_id or plant_id == 'slot':
                    continue
                if ach_event == "perfect_growth":
                    result = challenge_interface.record_perfect_growth(user_id, plant_id)
                elif ach_event == "death":
                    result = challenge_interface.record_plant_death(user_id, plant_id)
                elif ach_event == "species_collected":
                    result = challenge_interface.record_species_collected(user_id)
                elif ach_event == "mistake":
                    result = challenge_interface.record_mistake(user_id, plant_id, "game")
                else:
                    result = {"new_achievements": challenge_interface.check_all_achievements(user_id)}
                side_effects["newAchievements"].extend(result.get("new_achievements") or [])

        quest_result = level_quest_interface.check_quests(user_id)
        if quest_result.get("leveled_up"):
            side_effects["levelUp"] = {
                "newLevel": quest_result.get("new_level"),
                "reward": quest_result.get("reward"),
                "rewardText": self.LEVEL_REWARDS.get(quest_result.get("new_level")),
            }
            profile = self.user_repo.get_profile(user_id)
            if profile:
                side_effects["currentLevel"] = profile.get("current_level")
        elif quest_result.get("quests_completed"):
            side_effects["questUpdate"] = {
                "completedQuests": quest_result.get("quests_completed"),
            }

        return side_effects

    def mark_read_description(self, user_id: str) -> Dict[str, Any]:
        bundle = self._load_bundle(user_id)
        bundle["achievements"]["__readDescriptionDone"] = True
        self._save_bundle(user_id, bundle)
        quest_result = level_quest_interface.check_quests(user_id)
        return {"success": True, "questUpdate": quest_result}

    def mark_healed(self, user_id: str) -> None:
        bundle = self._load_bundle(user_id)
        bundle["achievements"]["__healedPlant"] = True
        self._save_bundle(user_id, bundle)
        level_quest_interface.trigger_quest_check(user_id, "heal")

    def plant_in_slot(self, user_id: str, slot_name: str, species_id: int) -> Dict[str, Any]:
        bundle = self._load_bundle(user_id)
        slot = bundle["slotData"].get(slot_name)
        if not slot or not slot.get("pot"):
            return {"success": False, "error": "Сначала поставьте горшок"}

        now = self._now_ms()
        slot.update(
            {
                "plant": str(species_id),
                "stage": 0,
                "plantedAt": now,
                "lastWateredAt": None,
                "totalWaterings": 0,
                "hasDisease": False,
                "hadMistakes": False,
                "disease": None,
                "diseaseType": None,
                "diseaseSource": None,
                "diseaseStartTime": None,
                "mistakeCategories": {"water": False, "place": False, "pot": False},
                "wateringHistory": [],
                "devManualState": False,
            }
        )
        bundle["slotData"][slot_name] = slot

        self.user_repo.increment_stat(user_id, "total_plants_grown")
        events: List[Dict[str, Any]] = [{"type": "planted", "slotName": slot_name, "speciesId": species_id}]
        side_effects = self._collect_side_effects(user_id, events)
        if side_effects.get("currentLevel"):
            bundle["currentLevel"] = side_effects["currentLevel"]
        self._save_bundle(user_id, bundle)

        return {
            "success": True,
            "slotName": slot_name,
            "slotData": slot,
            "events": events,
            **side_effects,
        }

    def water_slot(self, user_id: str, slot_name: str) -> Dict[str, Any]:
        bundle = self._load_bundle(user_id)
        data = bundle["slotData"].get(slot_name)
        if not data or not data.get("plant") or self._is_plant_dead(data):
            return {"success": False, "error": "Нельзя полить это растение"}

        species_id = self._resolve_species_id(data.get("plant"))
        now = self._now_ms()
        events: List[Dict[str, Any]] = []
        watered_too_early = False
        watering_on_time = self._is_watering_on_time(data, species_id, now)

        if data.get("lastWateredAt"):
            since_ms = now - data["lastWateredAt"]
            if since_ms < self._get_water_min_ms(species_id):
                watered_too_early = True
                wait_ms = max(0, self._get_water_min_ms(species_id) - since_ms)
                events.append({"type": "overwater_warning", "waitMs": wait_ms})
                self._record_mistake_category(data, "water")

        data["devManualState"] = False
        self._record_watering_gap(data, now)
        data["lastWateredAt"] = now
        data["totalWaterings"] = (data.get("totalWaterings") or 0) + 1
        self.user_repo.increment_stat(user_id, "total_waterings")

        self._try_heal_underwater_on_water(data, species_id, events)
        self._check_watering_health(slot_name, data, species_id, events)
        self._apply_growth_from_time(slot_name, data, species_id, events)

        if not watered_too_early and not data.get("hasDisease"):
            events.append(
                {
                    "type": "watered",
                    "onTime": watering_on_time,
                    "speciesId": species_id,
                }
            )

        side_effects = self._collect_side_effects(user_id, events)
        if side_effects.get("currentLevel"):
            bundle["currentLevel"] = side_effects["currentLevel"]
        bundle["slotData"][slot_name] = data
        self._save_bundle(user_id, bundle)

        return {
            "success": True,
            "slotName": slot_name,
            "slotData": data,
            "events": events,
            **side_effects,
        }

    def tick(self, user_id: str, slot_names: Optional[List[str]] = None) -> Dict[str, Any]:
        bundle = self._load_bundle(user_id)
        slot_data = bundle["slotData"]
        targets = slot_names or list(slot_data.keys())
        events: List[Dict[str, Any]] = []
        updated_slots: Dict[str, Any] = {}

        for slot_name in targets:
            data = slot_data.get(slot_name)
            if not data or not data.get("plant"):
                continue
            before = deepcopy(data)
            self._process_slot(slot_name, data, events)
            if data != before:
                updated_slots[slot_name] = data
                slot_data[slot_name] = data

        side_effects = self._collect_side_effects(user_id, events)
        if side_effects.get("currentLevel"):
            bundle["currentLevel"] = side_effects["currentLevel"]
        self._save_bundle(user_id, bundle)

        return {
            "success": True,
            "updatedSlots": updated_slots,
            "events": events,
            **side_effects,
        }

    def move_slot(self, user_id: str, from_slot: str, to_slot: str) -> Dict[str, Any]:
        bundle = self._load_bundle(user_id)
        slot_data = bundle["slotData"]
        source = slot_data.get(from_slot)
        target = slot_data.get(to_slot)

        if not source:
            return {"success": False, "error": "Источник не найден"}
        if target and target.get("pot"):
            return {"success": False, "error": "Место уже занято"}

        moved = deepcopy(source)
        moved["devManualState"] = False
        slot_data[to_slot] = moved
        del slot_data[from_slot]

        events: List[Dict[str, Any]] = [{"type": "moved", "from": from_slot, "to": to_slot}]
        self._process_slot(to_slot, slot_data[to_slot], events, include_growth=True)
        side_effects = self._collect_side_effects(user_id, events)
        if side_effects.get("currentLevel"):
            bundle["currentLevel"] = side_effects["currentLevel"]
        self._save_bundle(user_id, bundle)

        return {
            "success": True,
            "fromSlot": from_slot,
            "toSlot": to_slot,
            "slotData": slot_data,
            "events": events,
            **side_effects,
        }


room_game_service = RoomGameService()