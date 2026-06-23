# 小米动态照片转 Apple Live Photo 工具

这个工具用于将小米 / HyperOS 导出的动态照片转换为 Apple Photos 可以识别的 Live Photo 配对文件。

近期的小米和 HyperOS 设备可能会把静态照片和短视频封装在同一个 `.jpg` 文件中，并使用 Google Motion Photo 元数据记录视频位置。Apple Photos 通常需要一组共享 Apple 元数据标识的静态图和视频文件。本工具会从小米动态照片中拆出内嵌视频，生成干净的静态图，并写入 Apple Photos 识别 Live Photo 所需的配对标识。

## 输出结构

每一张可转换的小米动态照片会生成一个独立文件夹：

```text
<output-dir>/
  MVIMG_20260510_214740/
    MVIMG_20260510_214740.jpg
    MVIMG_20260510_214740.mov
```

文件夹名称取自原始文件名，不包含扩展名。文件夹主要用于整理和避免配对文件混淆；Apple Photos 是否识别为 Live Photo，关键取决于 `.jpg` 和 `.mov` 内部的配对元数据。

## 必备工具

必需：

- macOS
- Python 3.9 或更高版本
- Swift 命令行工具，用于通过 Apple ImageIO 写入照片侧元数据
- `exiftool`，用于读取小米 / Google Motion Photo 元数据，以及写入视频侧 QuickTime 元数据

使用 Homebrew 安装 `exiftool`：

```bash
brew install exiftool
```

检查工具是否可用：

```bash
python3 --version
swift --version
exiftool -ver
```

当前流程不依赖 `ffmpeg`。

## 为什么需要 Apple ImageIO

最初只写入通用 XMP 元数据时，Apple Photos 会把导入结果显示成一张普通照片和一个普通视频。实际测试确认，JPG 侧需要写入 Apple MakerNote 中的 `ContentIdentifier`。本工具使用 macOS 自带的 ImageIO 完成这一步。

成功转换后，元数据应类似：

```text
JPG: [Apple] ContentIdentifier = <UUID>
MOV: [Keys]  ContentIdentifier = <same UUID>
```

## 图形界面用法

启动 GUI：

```bash
python3 gui.py
```

GUI 支持：

- 通过系统文件夹选择器选择源目录
- 通过系统文件夹选择器选择输出目录
- 选择“只预览，不写入文件”
- 显示转换进度
- 转换完成后显示总数、成功、跳过、失败统计

## 命令行用法

转换某个目录中的所有 JPEG 文件：

```bash
python3 convert_xiaomi_motion_photo.py \
  --input-dir "<input-dir>" \
  --out "<output-dir>" \
  --report "<output-dir>/conversion_report.jsonl"
```

转换指定文件：

```bash
python3 convert_xiaomi_motion_photo.py \
  /path/to/MVIMG_20260510_214740.jpg \
  /path/to/MVIMG_20251216_214653.jpg \
  --out "<output-dir>"
```

只预览，不写出 Live Photo 配对文件：

```bash
python3 convert_xiaomi_motion_photo.py \
  --input-dir "<input-dir>" \
  --out "<output-dir>" \
  --dry-run
```

## 推荐流程

1. 先复制 3 到 5 张有代表性的小米动态照片到测试目录。
2. 对测试目录运行转换。
3. 将生成的文件夹导入 Apple Photos。
4. 确认 Apple Photos 将每组文件识别为一张 Live Photo，而不是两个独立项目。
5. 再对完整目录执行转换。
6. 检查报告文件。
7. 如果照片库很大，建议分批导入 Apple Photos。

## 报告文件

转换器会在标准输出打印 JSON 结果，也可以通过 `--report` 写入 JSONL 报告文件，每行对应一个源文件。

常见状态：

- `converted`：检测到内嵌动态视频，并已成功转换。
- `skipped`：没有检测到内嵌动态视频元数据，通常可作为普通静态图片处理。
- `failed`：该文件转换失败。

报告示例：

```json
{"source":"MVIMG_20260510_214740.jpg","status":"converted","folder":"<output-dir>/MVIMG_20260510_214740","jpg":"<output-dir>/MVIMG_20260510_214740/MVIMG_20260510_214740.jpg","mov":"<output-dir>/MVIMG_20260510_214740/MVIMG_20260510_214740.mov","image_bytes":2269272,"video_bytes":2828502,"asset_id":"DADB133D-0826-462D-9686-3397F1144A66"}
```

## 归档被跳过的静态图片

如果有文件被跳过，它们通常是普通静态 JPEG，或者动态照片中的视频部分已经不存在。可以将这些源文件复制到单独目录：

```bash
python3 scripts/archive_skipped_static_images.py \
  --source-dir "<input-dir>" \
  --skipped-list "<output-dir>/skipped_files.txt" \
  --out "<static-archive-dir>"
```

## 注意事项

- 工具不会覆盖原始小米照片文件。
- 仅处理 `exiftool` 能识别出小米 / Google Motion Photo 元数据的文件。
- 生成的 `.mov` 文件在一些媒体工具中可能仍显示为 MP4 内部格式；实际测试中，只要 JPG 和 MOV 的 Apple 配对标识一致，Apple Photos 可以正确识别。
- 不要把个人照片、样本文件或转换输出提交到 Git。`.gitignore` 已默认忽略常见输出目录。

## 项目文件

- `convert_xiaomi_motion_photo.py`：主转换脚本。
- `gui.py`：可选图形界面，用于选择源目录和输出目录。
- `live_photo_metadata.swift`：通过 Apple ImageIO 写入 JPG 侧 Apple 配对标识。
- `scripts/archive_skipped_static_images.py`：将被跳过的静态图片复制到单独归档目录。
- `docs/workflow.md`：完整流程和排错说明。
