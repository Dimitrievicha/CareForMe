import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

DB_PATH = str(Path(__file__).parent.parent / "careforme.db")


def reset_db_manager():
    """Сбрасывает глобальный синглтон db_manager"""
    import src.backend.database_full.database.db_manager as db_manager_module
    if hasattr(db_manager_module, '_db_manager'):
        db_manager_module._db_manager = None


# Автоматически сбрасываем при импорте
reset_db_manager()