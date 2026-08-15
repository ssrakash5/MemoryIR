from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.services.container import build_services


def main() -> None:
    services = build_services(get_settings())
    result = services.store.seed_demo(services.provider)
    print(f"Seeded {len(result['memories'])} demo memories")


if __name__ == "__main__":
    main()
