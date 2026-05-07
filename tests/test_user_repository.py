import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from tests.conftest import DB_PATH
from src.backend.database_full.repository.user_repository import UserRepository


class TestUserRepository:

    def test_tc_user_01_import(self):
        assert UserRepository is not None

    def test_tc_user_02_instantiation(self):
        repo = UserRepository(db_path=DB_PATH)
        assert repo is not None

    def test_tc_user_03_user_exists(self):
        repo = UserRepository(db_path=DB_PATH)
        exists = repo.user_exists("non_existent_user_12345")
        assert isinstance(exists, bool)

    def test_tc_user_04_get_user_by_username(self):
        repo = UserRepository(db_path=DB_PATH)
        user = repo.get_user_by_username("non_existent_user_12345")
        assert user is None

    def test_tc_user_05_get_profile(self):
        repo = UserRepository(db_path=DB_PATH)
        profile = repo.get_profile("non-existent-user-id")
        assert profile is None or isinstance(profile, dict)