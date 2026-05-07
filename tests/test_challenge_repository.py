import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from tests.conftest import DB_PATH
from src.backend.database_full.repository.challenge_repository import ChallengeRepository


class TestChallengeRepository:

    def test_tc_chal_01_import(self):
        assert ChallengeRepository is not None

    def test_tc_chal_02_instantiation(self):
        repo = ChallengeRepository(db_path=DB_PATH)
        assert repo is not None

    def test_tc_chal_03_get_all_achievements(self):
        repo = ChallengeRepository(db_path=DB_PATH)
        achievements = repo.get_all_achievements()
        # Должен вернуть список (с данными или пустой)
        assert isinstance(achievements, list), f"Ожидался list, получен {type(achievements)}"
        print(f"Найдено достижений: {len(achievements)}")

    def test_tc_chal_04_get_user_achievements(self):
        repo = ChallengeRepository(db_path=DB_PATH)
        achievements = repo.get_user_achievements("test-user-id")
        assert isinstance(achievements, list), f"Ожидался list, получен {type(achievements)}"