"""Проверяет, что ветка feat/<ID>-... меняет только файлы из контракта блока <ID>.

Локально:  python scripts/check_paths.py B4            (сравнение с origin/dev)
В CI:      python scripts/check_paths.py --branch "$GITHUB_HEAD_REF" --base "origin/$GITHUB_BASE_REF"
"""

import argparse
import json
import re
import subprocess
import sys
from fnmatch import fnmatch
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATHS = json.loads((ROOT / "docs/contracts/paths.json").read_text(encoding="utf-8"))


def allowed(path: str, patterns: list[str]) -> bool:
    return any(fnmatch(path, p) or fnmatch(path, p.replace("/**", "/*")) for p in patterns)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("block", nargs="?")
    ap.add_argument("--branch", default="")
    ap.add_argument("--base", default="origin/dev")
    args = ap.parse_args()

    block = args.block
    if not block:
        m = re.match(r"feat/([A-Z]\d)-", args.branch)
        if not m:
            print(f"ветка «{args.branch}» не feat/<ID>-… — проверка путей пропущена")
            return 0
        block = m.group(1)
    if block not in PATHS:
        print(f"неизвестный блок {block}; есть: {', '.join(PATHS)}")
        return 1

    diff = subprocess.run(
        ["git", "diff", "--name-only", f"{args.base}...HEAD"], capture_output=True, text=True, check=True, cwd=ROOT
    ).stdout.split()
    outside = [f for f in diff if not allowed(f, PATHS[block])]
    if outside:
        print(f"Блок {block} изменил файлы ВНЕ своего контракта:")
        for f in outside:
            print(f"  - {f}")
        print(f"Разрешено: {PATHS[block]}")
        return 1
    print(f"Блок {block}: {len(diff)} файлов, все в разрешённых путях")
    return 0


if __name__ == "__main__":
    sys.exit(main())
