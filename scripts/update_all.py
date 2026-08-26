"""Run the whole pipeline: fetch everything new, reparse, rebuild the page."""

import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent

STEPS = [
    "sweep_polnews.py",
    "sweep_topics.py",
    "fetch_forum.py",
    "fetch_legacy.py",
    "parse_polnews.py",
    "parse_forum.py",
    "parse_legacy.py",
    "build.py",
]


def main():
    for step in STEPS:
        print(f"=== {step} ===", flush=True)
        result = subprocess.run([sys.executable, str(SCRIPTS / step)])
        if result.returncode != 0:
            print(f"{step} failed ({result.returncode}); fix or rerun.", flush=True)
            sys.exit(result.returncode)


if __name__ == "__main__":
    main()
