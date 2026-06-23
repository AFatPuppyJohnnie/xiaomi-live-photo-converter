#!/usr/bin/env python3
import argparse
import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path


def run(cmd, *, capture=True, check=True):
    return subprocess.run(
        cmd,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        check=check,
    )


def swift_env():
    env = None
    if shutil.which("swift"):
        env = dict(**__import__("os").environ)
        env.setdefault("CLANG_MODULE_CACHE_PATH", "/private/tmp/clang-module-cache")
        env.setdefault("SWIFT_MODULE_CACHE_PATH", "/private/tmp/swift-module-cache")
    return env


def run_with_env(cmd, env, *, capture=True, check=True):
    return subprocess.run(
        cmd,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        check=check,
        env=env,
    )


def exif_json(path: Path):
    result = run(["exiftool", "-json", "-a", "-G1", str(path)])
    return json.loads(result.stdout)[0]


def exif_json_batch(paths):
    cmd = ["exiftool", "-json", "-a", "-G1"] + [str(path) for path in paths]
    result = run(cmd)
    by_source = {}
    for item in json.loads(result.stdout):
        source = item.get("SourceFile")
        if source:
            by_source[str(Path(source))] = item
    return by_source


def first_int(meta, names):
    for name in names:
        for key, value in meta.items():
            if key.endswith(name) and value not in (None, ""):
                try:
                    return int(value)
                except (TypeError, ValueError):
                    continue
    return None


def has_motion_photo(meta):
    for key, value in meta.items():
        if key.endswith("MotionPhoto") or key.endswith("MicroVideo"):
            if str(value) == "1":
                return True
    return False


def find_ftyp_offset(data: bytes, start_at: int):
    window_start = max(0, start_at - 64)
    pos = data.find(b"ftyp", window_start)
    if pos < 0:
        return None
    return max(0, pos - 4)


def extract_pair(src: Path, out_dir: Path, dry_run: bool = False, meta=None):
    meta = meta or exif_json(src)
    video_len = first_int(meta, ["DirectoryItemLength", "MicroVideoOffset"])
    if not video_len or not has_motion_photo(meta):
        return {"source": src.name, "status": "skipped", "reason": "no embedded motion video metadata"}

    data = src.read_bytes()
    if video_len >= len(data):
        return {"source": src.name, "status": "failed", "reason": "embedded video length is larger than source file"}

    video_start = len(data) - video_len
    ftyp_start = find_ftyp_offset(data, video_start)
    if ftyp_start is None or abs(ftyp_start - video_start) > 256:
        return {"source": src.name, "status": "failed", "reason": "could not locate MP4 ftyp marker near expected offset"}

    image_bytes = data[:ftyp_start]
    video_bytes = data[ftyp_start:]
    base = src.stem
    asset_id = str(uuid.uuid4()).upper()
    pair_dir = out_dir / base
    final_jpg = pair_dir / f"{base}.jpg"
    final_mov = pair_dir / f"{base}.mov"

    if dry_run:
        return {
            "source": src.name,
            "status": "would_convert",
            "image_bytes": len(image_bytes),
            "video_bytes": len(video_bytes),
            "asset_id": asset_id,
        }

    pair_dir.mkdir(parents=True, exist_ok=True)
    temp_jpg = pair_dir / f"{base}.tmp.jpg"
    temp_jpg.write_bytes(image_bytes)
    final_mov.write_bytes(video_bytes)
    run_with_env([
        "swift",
        "live_photo_metadata.swift",
        str(temp_jpg),
        str(final_jpg),
        asset_id,
    ], swift_env())
    temp_jpg.unlink(missing_ok=True)
    run([
        "exiftool",
        "-overwrite_original",
        "-XMP-GCamera:All=",
        "-XMP-GContainer:All=",
        "-XMP-GContainerItem:All=",
        "-XMP-MiCamera:All=",
        str(final_jpg),
    ])

    run([
        "exiftool",
        "-overwrite_original",
        f"-Keys:ContentIdentifier={asset_id}",
        str(final_mov),
    ])

    probe = run([
        "exiftool",
        "-json",
        "-s",
        "-FileType",
        "-MIMEType",
        "-Duration",
        "-ImageWidth",
        "-ImageHeight",
        "-ContentIdentifier",
        str(final_mov),
    ])
    probe_json = json.loads(probe.stdout)

    return {
        "source": src.name,
        "status": "converted",
        "folder": str(pair_dir),
        "jpg": str(final_jpg),
        "mov": str(final_mov),
        "image_bytes": len(image_bytes),
        "video_bytes": len(video_bytes),
        "asset_id": asset_id,
        "probe": probe_json,
    }


def main():
    parser = argparse.ArgumentParser(description="Convert Xiaomi/Google Motion Photo JPEGs into Apple Live Photo pairs.")
    parser.add_argument("inputs", nargs="*", type=Path)
    parser.add_argument("--input-dir", type=Path, action="append", default=[])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    inputs = list(args.inputs)
    for input_dir in args.input_dir:
        inputs.extend(sorted(input_dir.glob("*.jpg")))
        inputs.extend(sorted(input_dir.glob("*.jpeg")))
        inputs.extend(sorted(input_dir.glob("*.JPG")))
        inputs.extend(sorted(input_dir.glob("*.JPEG")))

    if not inputs:
        parser.error("no input files found")

    meta_by_source = exif_json_batch(inputs)
    results = []
    total = len(inputs)
    report_path = args.report or (args.out / "conversion_report.jsonl")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as report:
        for index, src in enumerate(inputs, start=1):
            if index == 1 or index % 50 == 0 or index == total:
                print(f"processing {index}/{total}: {src.name}", file=sys.stderr, flush=True)
            try:
                result = extract_pair(src, args.out, args.dry_run, meta_by_source.get(str(src)))
            except subprocess.CalledProcessError as exc:
                result = {"source": src.name, "status": "failed", "reason": exc.stderr.strip() or str(exc)}
            except Exception as exc:
                result = {"source": src.name, "status": "failed", "reason": str(exc)}
            results.append(result)
            report.write(json.dumps(result, ensure_ascii=False) + "\n")
            report.flush()

    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 1 if any(item["status"] == "failed" for item in results) else 0


if __name__ == "__main__":
    sys.exit(main())
