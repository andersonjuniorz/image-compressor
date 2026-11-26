# Image Compressor

![Image Compressor](docs/screenshot.png)

A batch image compressor with a graphical interface, written in Python. Choose a folder, adjust the settings, and the compressed images are saved in a separate folder, keeping the original subfolder structure.

## Table of Contents

- [Description](#description)
- [Goal](#goal)
- [Features](#features)
- [Supported Formats](#supported-formats)
- [Installation](#installation)
- [How to Use](#how-to-use)
- [The FAILED_ Rule](#the-failed_-rule)
- [Development](#development)
- [Project Structure](#project-structure)
- [Architecture](#architecture)
- [Build and Releases](#build-and-releases)
- [Technologies](#technologies)
- [Versions](#versions)
- [Known Limitations](#known-limitations)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)
- [Credits](#credits)

## Description

Image Compressor reduces the file size of images in batch, without needing command-line knowledge. The window guides you through three steps: choose a folder, adjust the settings, and start the compression. During the process, each file appears in a colored log with its size before and after. At the end, a summary shows the total savings.

## Goal

Make image compression for the web and general use fast and predictable:

- **Batch compression:** a whole folder, including subfolders, in one run.
- **Same output format:** a PNG stays a PNG, and a WebP stays a WebP. Converting between formats is out of scope.
- **Lighter files:** metadata is removed, and the compression settings can be adjusted.
- **No false positives:** if the result is larger than the original, the file gets the `FAILED_` prefix. This tells you that the current settings did not help for that image.
- **Isolated failures:** a corrupted or unsupported file does not stop the batch.

## Features

- Graphical interface with a dark theme, built with PySide6 (Qt 6).
- Folder selection with the system's native dialog.
- Sliders for quality and compression level, with the recommended value highlighted.
- A button to restore the recommended values.
- Background processing, so the window never freezes.
- Progress bar and a real-time log for each file.
- Final summary with totals, savings, and failure count.
- Text report (`relatorio.txt`) saved in the output folder.
- A button to open the output folder in the file manager.
- Metadata removal (EXIF, XMP, ICC profile) from compressed images.
- Automatic orientation fix (EXIF rotation applied to the pixels before metadata is removed).
- Optional PNG quantization to a 256-color palette. The smaller of the lossy and lossless versions is kept.

## Supported Formats

| Format | Extensions | Compression | Output |
|---|---|---|---|
| PNG | `.png` | Lossless (optimization) or lossy (quantization, optional) | PNG |
| JPEG | `.jpg`, `.jpeg` | Lossy, progressive | JPEG |
| WebP | `.webp` | Lossy | WebP |
| JPEG XL | `.jxl` | Lossy (requires `pillow-jxl-plugin`) | JXL |

The output format is always the same as the input. Files with other extensions are ignored.

## Installation

### Requirements

- Python 3.14 (or a version supported by PySide6 and Pillow).
- Linux (tested on elementary OS). Windows builds are produced by the CI, but they have not been tested by the author.
- `make` (usually already installed on Linux).

### Quick start

```bash
git clone https://github.com/seu-usuario/image-compressor.git
cd image-compressor

make install
```

`make install` creates the `.venv` virtual environment and installs the dependencies from `requirements.txt`.

### Manual installation

```bash
python3.14 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Dependencies (`requirements.txt`)

```text
PySide6>=6.6
pillow>=11.2
pillow-jxl-plugin
```

### Optional: high-quality PNG quantization

When Pillow is built with `libimagequant`, PNG quantization uses that quantizer, which gives better results. Otherwise, the program uses a simpler one. To check:

```bash
.venv/bin/python -c "from PIL import features; print(features.check('libimagequant'))"
```

## How to Use

1. Start the program:

   ```bash
   make run
   ```

2. Click **Buscar pasta** (Choose folder) and select the folder with your images. Subfolders are included.
3. Adjust the settings, or keep the recommended values.
4. Click **Iniciar compressão** (Start compression).
5. When it finishes, click **Abrir pasta de resultados** (Open results folder) to see the output.

Compressed images are saved in a folder called `ImagesCompressed`, created inside the folder you chose. The original files are not changed.

### Settings

| Setting | Range | Recommended | Note |
|---|---|---|---|
| JPEG quality | 60 to 90 | 85 | For websites, 75 to 80 is usually ideal. |
| WebP quality | 60 to 90 | 85 | For websites, 75 to 80 is usually ideal. |
| JPEG XL quality | 60 to 90 | 85 | Scale from 0 to 100. |
| PNG compression level | 0 to 6 | 3 | 0 is faster but larger; 6 is slower but smaller. |
| Lossy PNG | on/off | on | Very effective for screenshots and illustrations. Photos may show banding. |

### Tips for websites

- Use **75** as the default when a site has many images.
- Use **80** for featured images, such as banners and product photos.
- Resize images before compressing. A 4000 px photo shown at 1200 px wastes most of its size. This version does not resize automatically.
- Compress from the original file. Each lossy re-compression lowers the quality.

## The FAILED_ Rule

After each file is written, the program compares its size with the original:

- **Smaller or equal:** the file keeps its original name in `ImagesCompressed`.
- **Larger:** the file gets the `FAILED_` prefix (for example, `FAILED_photo.jpg`). This means the image was already well optimized at that setting. Try again with more aggressive settings.

Before each run, old `FAILED_` files are removed, so the results always match the latest run.

## Development

The Makefile has the main commands:

| Command | What it does |
|---|---|
| `make help` | Lists the available commands |
| `make install` | Creates `.venv` and installs the dependencies |
| `make run` | Opens the application |
| `make test` | Runs the smoke test for the compression engine (no GUI) |
| `make build-local` | Builds the Linux executable with PyInstaller |
| `make check` | Runs `test` and then `build-local`. Use it before every push. |
| `make clean` | Removes build files and `__pycache__` (keeps `.venv` and your images) |

Recommended routine before a push:

```bash
make check
```

## Project Structure

```
image-compressor/
├── main.py              # GUI: window, controls, and log
├── requirements.txt     # Dependencies
├── Makefile             # Development commands
├── README.md
├── docs/
│   └── screenshot.png
├── tests/
│   └── smoke_test.py    # Quick test of the compression engine
├── ui/
│   └── theme.py         # Stylesheet (dark theme)
├── core/
│   ├── __init__.py
│   ├── compressor.py    # Compression rules for each format
│   ├── file_scanner.py  # Recursive search for supported images
│   ├── batch.py         # Background batch processing
│   └── report.py        # Text report generation
└── .github/
    └── workflows/
        └── ci.yml       # Builds for Linux and Windows
```

## Architecture

The project has two layers. The core does not depend on the GUI:

- **`ui/` and `main.py`:** presentation. They handle the window, the controls, and the log, and only call the core.
- **`core/`:** logic. It does not import Qt, except `batch.py`, which uses `QThread` to run the batch outside the main thread.

### Execution flow

1. `scan()` looks through the chosen folder, skips `ImagesCompressed` and `FAILED_` files, and filters by supported extensions.
2. For each file, a `Job` is created with the source, the destination, and the relative path.
3. `BatchWorker` sends the jobs to a `ThreadPoolExecutor` with `cores - 1` workers.
4. Each job calls `compress_file()`, which:
   - opens the image and applies the EXIF rotation to the pixels;
   - encodes it in the original format, without metadata;
   - compares the size with the original and renames the file with `FAILED_` if needed.
5. Each result is sent to the interface through a signal (`item_done`), so the window stays responsive.
6. At the end, the report is saved and the summary is shown.

### Error handling

An error in one file creates a result with `ok = False`. The batch continues, and the error appears in the log and in the report.

## Build and Releases

The CI workflow (`.github/workflows/ci.yml`) runs on GitHub Actions:

- **Push to `main`:** builds the Linux and Windows executables. You can download them from the **Actions** tab, in **Artifacts**.
- **Tag `v*`** (for example, `v2.0.0`): builds both executables and publishes a GitHub Release with the files attached.

To create a release:

```bash
git tag v2.0.0
git push origin v2.0.0
```

The executables are built with PyInstaller as single files, so they do not need Python installed.

## Technologies

| Library | Purpose |
|---|---|
| [PySide6](https://doc.qt.io/qtforpython-6/) | Graphical interface (Qt 6) |
| [Pillow](https://python-pillow.org/) | Reading, converting, and encoding images |
| [pillow-jxl-plugin](https://pypi.org/project/pillow-jxl-plugin/) | JPEG XL support for Pillow |
| `concurrent.futures` | Parallel execution with threads |
| [PyInstaller](https://pyinstaller.org/) | Builds the standalone executables |

## Versions

### v2.0 (Python, current)

- Rewritten in Python, with a graphical interface built with PySide6.
- Dark theme, sliders, and a real-time log.
- Layered structure (`ui` and `core`).
- Text report and a button to open the results folder.
- Makefile commands, smoke test, and CI builds for Linux and Windows.

### v1.0 (Rust, reference)

- Command-line version written in Rust. It is kept under the tag `v1-rust` for reference.
- Interactive questions in the terminal. Press Enter to use the recommended values.
- `ImagesIn` and `ImagesOut` folders.
- Native compression libraries (`oxipng`, `imagequant`, `jpegxl-rs`).

## Known Limitations

- Automatic resizing is not available yet.
- AVIF is not supported as input.
- For photos, PNG quantization may cause banding. Turn off the lossy option in those cases.
- Lossy JPEG, WebP, and JXL remove the ICC profile. Photos with colors outside sRGB may show a color shift.
- The project has only a smoke test for the compression engine. The GUI is tested manually.
- Windows builds are produced by the CI but have not been tested on a real Windows machine by the author.

## Roadmap

- [ ] Resize with a maximum width.
- [ ] Drag and drop a folder into the window.
- [ ] AVIF support as input.
- [ ] More automated tests, with a set of sample images.
- [ ] Integration with other image microservices.

## Contributing

Contributions are welcome. For larger changes, please open an issue first to discuss the idea.

1. Fork the repository.
2. Create a branch for your change: `git checkout -b my-feature`.
3. Commit your work and push the branch: `git push origin my-feature`.
4. Open a Pull Request.

Before opening a PR, run `make check`. Keep the separation between `ui/` and `core/`: the compression logic must not depend on Qt.

## License

The license has not been chosen yet. Common options are MIT, for maximum freedom of use, or GPL-3.0, which requires derivative works to stay open source.

**Note:** `imagequant` (used by Pillow when it is built with `libimagequant`) is licensed under GPL-3.0 or a commercial license. Check this dependency before choosing a permissive license.

## Credits

- Developed by **Tobi**.
- Architecture, code, and documentation developed with the help of **Claude** (Anthropic), which assisted with planning, writing the code, and this README.
