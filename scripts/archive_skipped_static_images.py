#!/usr/bin/env python3
import argparse
import shutil
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Copy skipped static source images into a separate archive folder.")
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--skipped-list", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    missing = []
    copied = 0

    for name in args.skipped_list.read_text(encoding="utf-8").splitlines():
        name = name.strip()
        if not name:
            continue
        src = args.source_dir / name
        dst = args.out / name
        if not src.exists():
            missing.append(name)
            continue
        shutil.copy2(src, dst)
        copied += 1

    report = args.out / "archive_report.txt"
    report.write_text(
        f"copied={copied}\nmissing={len(missing)}\n"
        + "".join(f"missing: {name}\n" for name in missing),
        encoding="utf-8",
    )
    print(f"copied={copied}")
    print(f"missing={len(missing)}")
    print(f"report={report}")


if __name__ == "__main__":
    main()
