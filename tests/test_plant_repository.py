import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from tests.conftest import DB_PATH
from src.backend.database_full.repository.plant_repository import PlantRepository


class TestPlantRepository:

    def test_tc_plant_01_import(self):
        assert PlantRepository is not None

    def test_tc_plant_02_instantiation(self):
        repo = PlantRepository(db_path=DB_PATH)
        assert repo is not None

    def test_tc_plant_03_get_all_templates(self):
        repo = PlantRepository(db_path=DB_PATH)
        templates = repo.get_all_templates()
        # Должен вернуть список (с данными или пустой)
        assert isinstance(templates, list), f"Ожидался list, получен {type(templates)}"
        print(f"Найдено шаблонов: {len(templates)}")

    def test_tc_plant_04_get_template_by_species_id(self):
        repo = PlantRepository(db_path=DB_PATH)
        template = repo.get_template_by_species_id(1)
        # Должен вернуть словарь или None
        assert template is None or isinstance(template, dict), f"Ожидался dict или None, получен {type(template)}"

    def test_tc_plant_05_get_user_plants(self):
        repo = PlantRepository(db_path=DB_PATH)
        plants = repo.get_user_plants("test-user-id")
        # Должен вернуть список (скорее всего пустой)
        assert isinstance(plants, list), f"Ожидался list, получен {type(plants)}"

    def test_tc_plant_06_get_dead_plants(self):
        repo = PlantRepository(db_path=DB_PATH)
        dead_plants = repo.get_dead_plants("test-user-id")
        assert isinstance(dead_plants, list), f"Ожидался list, получен {type(dead_plants)}"