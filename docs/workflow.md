# Workflow

This document summarizes the tested Xiaomi/HyperOS Motion Photo to Apple Live Photo conversion process.

## Background

Xiaomi Motion Photo files can be single `.jpg` files containing:

- a normal JPEG still image at the front of the file
- an embedded MP4 motion clip at the end of the file
- Google Motion Photo XMP metadata describing the video length or offset

Apple Photos imports Live Photos reliably when it sees a still image and video companion that share the same Apple content identifier.

## Tested Conversion Strategy

1. Read each source JPEG with `exiftool`.
2. Detect Xiaomi/Google Motion Photo fields:
   - `MicroVideo`
   - `MicroVideoOffset`
   - `MotionPhoto`
   - `DirectoryItemLength`
3. Compute the embedded video position from the end of the file.
4. Split the source bytes into:
   - clean JPEG bytes
   - embedded MP4 bytes
5. Generate one UUID per source file.
6. Write the clean JPEG into a per-photo folder.
7. Use `live_photo_metadata.swift` and Apple ImageIO to write the JPEG-side Apple `ContentIdentifier`.
8. Save the embedded video as a same-name `.mov` companion.
9. Use `exiftool` to write the same `ContentIdentifier` into the MOV Keys metadata.
10. Remove old Xiaomi/Google Motion Photo XMP metadata from the clean JPEG to avoid stale trailer references.
11. Write a JSONL report line for each source file.

## Validation Checklist

For a converted pair:

```bash
exiftool -G1 -a -s <output-dir>/MVIMG_xxx/MVIMG_xxx.jpg \
  <output-dir>/MVIMG_xxx/MVIMG_xxx.mov | \
  rg -i 'ContentIdentifier|Apple|Keys|Duration|FileType|MIMEType'
```

Expected:

```text
[Apple] ContentIdentifier : <UUID>
[Keys]  ContentIdentifier : <same UUID>
```

Then import the folder into Apple Photos and confirm it appears as one Live Photo.

## Troubleshooting

### Apple Photos imports two separate items

Likely causes:

- the JPEG does not contain `[Apple] ContentIdentifier`
- the MOV does not contain `[Keys] ContentIdentifier`
- the identifiers do not match

Fix:

- Make sure `live_photo_metadata.swift` can run.
- Check Swift module cache permissions. The converter sets cache paths under `/private/tmp` to avoid common sandbox permission issues.

### Source file is skipped

The source did not expose embedded motion video metadata. Treat it as a static image unless another matching video file exists elsewhere.

### `ffmpeg` is broken or missing

The current workflow does not require `ffmpeg`.

### Large libraries are slow

The converter batch-reads metadata first, then processes files one by one while writing a JSONL report. This is deliberate so progress and partial results survive interruptions.
