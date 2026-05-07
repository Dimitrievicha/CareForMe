import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from tests.conftest import DB_PATH


class TestBaseRepository:

    def test_tc_base_01_import(self):
        from src.backend.database_full.repository.base_repository import BaseRepository
        assert BaseRepository is not None

    def test_tc_base_02_instantiation(self):
        from src.backend.database_full.repository.base_repository import BaseRepository
        repo = BaseRepository(db_path=DB_PATH)
        assert repo is not None

    def test_tc_base_03_count_method(self):
        from src.backend.database_full.repository.base_repository import BaseRepository
        repo = BaseRepository(db_path=DB_PATH)
        count = repo.count("sqlite_master")
        assert isinstance(count, int)
        assert count >= 0

    def test_tc_base_04_exists_method(self):
        from src.backend.database_full.repository.base_repository import BaseRepository
        repo = BaseRepository(db_path=DB_PATH)
        exists = repo.exists("sqlite_master", "type='table'")
        assert isinstance(exists, bool)