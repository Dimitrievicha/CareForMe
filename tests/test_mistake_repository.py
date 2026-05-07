import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from tests.conftest import DB_PATH
from src.backend.database_full.repository.mistake_repository import MistakeRepository


class TestMistakeRepository:

    def test_tc_mist_01_import(self):
        assert MistakeRepository is not None

    def test_tc_mist_02_instantiation(self):
        repo = MistakeRepository(db_path=DB_PATH)
        assert repo is not None

    def test_tc_mist_03_get_mistakes_count(self):
        repo = MistakeRepository(db_path=DB_PATH)
        count = repo.get_mistakes_count("test-user-id")
        assert isinstance(count, int), f"Ожидался int, получен {type(count)}"
        assert count >= 0

    def test_tc_mist_04_get_mistakes_by_type(self):
        repo = MistakeRepository(db_path=DB_PATH)
        stats = repo.get_mistakes_by_type("test-user-id")
        assert isinstance(stats, dict), f"Ожидался dict, получен {type(stats)}"
        expected_types = ['overwater', 'drought', 'light', 'cold']
        for mistake_type in expected_types:
            assert mistake_type in stats, f"Тип {mistake_type} отсутствует в словаре"