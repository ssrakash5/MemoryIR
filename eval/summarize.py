from __future__ import annotations

from run_eval import load_cases


def main() -> None:
    cases = load_cases(__import__("pathlib").Path(__file__).parent / "cases")
    print(f"Loaded {len(cases)} controlled evaluation cases.")


if __name__ == "__main__":
    main()
