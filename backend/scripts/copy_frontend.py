from __future__ import annotations

import shutil
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    source = repo_root / "frontend" / "dist"
    target = repo_root / "backend" / "static"
    if not source.exists():
        raise SystemExit("frontend/dist does not exist. Run `npm run build` in frontend first.")
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)
    print(f"Copied {source} -> {target}")


if __name__ == "__main__":
    main()
