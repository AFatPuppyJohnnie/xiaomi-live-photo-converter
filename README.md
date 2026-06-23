# Xiaomi Motion Photo to Apple Live Photo Converter

[English](README.md) | [简体中文](README_zh-CN.md) 

Convert Xiaomi/HyperOS Motion Photo JPEG files into Apple Photos-compatible Live Photo pairs.

This project was built from a real Xiaomi photo export workflow. Recent Xiaomi and HyperOS devices can store a still image and its short motion clip inside one `.jpg` file, using Google Motion Photo metadata. Apple Photos expects a paired still image and video with matching Apple metadata. This tool extracts the embedded video, creates a clean still image, and writes the identifiers Apple Photos needs to import the pair as one Live Photo.

## What It Produces

For each convertible Xiaomi Motion Photo:

```text
<output-dir>/
  MVIMG_20260510_214740/
    MVIMG_20260510_214740.jpg
    MVIMG_20260510_214740.mov
```

The folder name is the original file name without extension. The folder is mainly for human organization. Apple Photos recognition depends on metadata inside the `.jpg` and `.mov` files.

## Requirements

Required:

- macOS
- Python 3.9+
- Swift command line tools, for Apple ImageIO metadata writing
- `exiftool`, for reading Xiaomi/Google Motion Photo metadata and writing QuickTime metadata

Install `exiftool` with Homebrew:

```bash
brew install exiftool
```

Check tools:

```bash
python3 --version
swift --version
exiftool -ver
```

`ffmpeg` is not required for the current workflow.

## Why Apple ImageIO Is Needed

Apple Photos did not merge the first test output when the JPEG only had generic XMP metadata. The working version writes the JPEG-side Apple MakerNote content identifier with ImageIO. The MOV side receives the same content identifier with `exiftool`.

Successful metadata shape:

```text
JPG: [Apple] ContentIdentifier = <UUID>
MOV: [Keys]  ContentIdentifier = <same UUID>
```

## Basic Usage

Start the optional GUI:

```bash
python3 gui.py
```

The GUI lets users choose the source and output folders with the system folder picker.

Convert all JPEG files in a directory:

```bash
python3 convert_xiaomi_motion_photo.py \
  --input-dir "<input-dir>" \
  --out "<output-dir>" \
  --report "<output-dir>/conversion_report.jsonl"
```

Convert selected files:

```bash
python3 convert_xiaomi_motion_photo.py \
  /path/to/MVIMG_20260510_214740.jpg \
  /path/to/MVIMG_20251216_214653.jpg \
  --out "<output-dir>"
```

Preview without writing output pairs:

```bash
python3 convert_xiaomi_motion_photo.py \
  --input-dir "<input-dir>" \
  --out "<output-dir>" \
  --dry-run
```

## Recommended Workflow

1. Copy 3 to 5 representative Xiaomi Motion Photo files into a small test folder.
2. Run the converter on the test folder.
3. Import the generated folders into Apple Photos.
4. Confirm Apple Photos displays each pair as one Live Photo instead of two separate items.
5. Run the full conversion into a new output directory.
6. Review the report files.
7. Import the converted output into Apple Photos in batches if the library is large.

## Reports

The converter writes JSON results to standard output and can also write one JSON object per line to a report file.

Common statuses:

- `converted`: the file contained embedded motion video and was converted.
- `skipped`: no embedded motion video metadata was detected.
- `failed`: conversion failed for that source file.

Example report line:

```json
{"source":"MVIMG_20260510_214740.jpg","status":"converted","folder":"<output-dir>/MVIMG_20260510_214740","jpg":"<output-dir>/MVIMG_20260510_214740/MVIMG_20260510_214740.jpg","mov":"<output-dir>/MVIMG_20260510_214740/MVIMG_20260510_214740.mov","image_bytes":2269272,"video_bytes":2828502,"asset_id":"DADB133D-0826-462D-9686-3397F1144A66"}
```

## Archiving Skipped Static Images

If some source files are skipped, they are usually ordinary static JPEGs or Motion Photos whose embedded video is no longer present. After conversion, you can copy those skipped source images into a separate folder with:

```bash
python3 scripts/archive_skipped_static_images.py \
  --source-dir "<input-dir>" \
  --skipped-list "<output-dir>/skipped_files.txt" \
  --out "<static-archive-dir>"
```

## Notes and Limitations

- The converter does not overwrite original Xiaomi files.
- It only processes file formats that expose Xiaomi/Google Motion Photo metadata readable by `exiftool`.
- The generated `.mov` file may still be identified internally as MP4 by media tools. Apple Photos accepted this in testing as long as the Apple JPEG identifier and MOV identifier matched.
- Keep conversion output out of Git. Personal photos and generated media are ignored by `.gitignore`.

## Project Files

- `convert_xiaomi_motion_photo.py`: main converter.
- `gui.py`: optional desktop GUI for choosing source and output folders.
- `live_photo_metadata.swift`: writes the Apple JPEG-side content identifier via ImageIO.
- `scripts/archive_skipped_static_images.py`: copies skipped static images into a separate archive folder.
- `docs/workflow.md`: end-to-end conversion checklist and troubleshooting notes.
