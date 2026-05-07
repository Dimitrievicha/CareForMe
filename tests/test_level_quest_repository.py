import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from tests.conftest import DB_PATH
from src.backend.database_full.repository.level_quest_repository import LevelQuestRepository


class TestLevelQuestRepository:

    def test_tc_level_01_import(self):
        assert LevelQuestRepository is not None

    def test_tc_level_02_instantiation(self):
        repo = LevelQuestRepository(db_path=DB_PATH)
        assert repo is not None

    def test_tc_level_03_get_max_level(self):
        repo = LevelQuestRepository(db_path=DB_PATH)
        max_level = repo.get_max_level()
        assert isinstance(max_level, int)
        assert max_level >= 1

    def test_tc_level_04_get_level_quests(self):
        repo = LevelQuestRepository(db_path=DB_PATH)
        quests = repo.get_level_quests(1)
        if quests is not None:
            assert isinstance(quests, dict)