"""Run the whole pipeline: fetch everything new, reparse, rebuild the page."""

import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent

STEPS = [
    "sweep_polnews.py",
    ["sweep_polnews.py", "ja"],
    "sweep_topics.py",
    "fetch_forum.py",
    "fetch_legacy.py",
    "fetch_attachments.py",
    "parse_polnews.py",
    "parse_forum.py",
    "parse_legacy.py",
    "combine.py",
    "build.py",
]


def main():
    for step in STEPS:
        if isinstance(step, str):
            step = [step]
        print(f"=== {' '.join(step)} ===", flush=True)
        result = subprocess.run([sys.executable, str(SCRIPTS / step[0])] + step[1:])
        if result.returncode != 0:
            print(f"{' '.join(step)} failed ({result.returncode}); fix or rerun.", flush=True)
            sys.exit(result.returncode)


if __name__ == "__main__":
    main()
