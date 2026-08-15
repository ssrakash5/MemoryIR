from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.db import execute_sql_file


def main() -> None:
    settings = get_settings()
    migrations = sorted((settings.repo_root / "db" / "migrations").glob("*.sql"))
    for migration in migrations:
        print(f"Applying {migration.name}")
        execute_sql_file(settings, migration)


if __name__ == "__main__":
    main()
