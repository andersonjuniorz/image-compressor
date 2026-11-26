# image-compress

Batch image compressor written in Rust. It reads images from one folder, compresses them, and saves the results in another folder, keeping the original input format.

## Compatibility

- Linux
- Windows (coming soon)

## Supported Formats

| Input | Compression | Output |
|---|---|---|
| PNG | Lossless (`oxipng`), with optional palette quantization (`imagequant`) | PNG |
| JPG / JPEG | Lossy (`jpeg-encoder`) | JPG |
| WebP | Lossy (`webp`) | WebP |
| JPEG XL (`.jxl`) | Lossy (`jpegxl-rs`, using `libjxl`) | JXL |

The output format is always the same as the input format. There is no format conversion.

Metadata (EXIF, XMP, etc.) is stripped from compressed images. For PNGs, the color profile is kept only when it affects the color (`StripChunks::Safe`).

## Folder Structure

```text
image-compress/
├── Cargo.toml
├── Makefile
├── src/
│   └── main.rs
├── ImagesIn/     <- put your original images here
└── ImagesOut/    <- results (created automatically)
```

- `ImagesIn` can contain subfolders. The folder structure is preserved inside `ImagesOut`.
- If `ImagesIn` does not exist, the program creates it and asks you to place your images inside.
- Existing files in `ImagesOut` with the same name are overwritten.

## How to Use

Put your images in `ImagesIn` and run:

```bash
make run
```

The program asks for each parameter in turn. Press Enter to use the recommended value:

| Prompt | Min | Med | Max | Recommended |
|---|---|---|---|---|
| JPEG quality (0-100) | 60 | 75 | 90 | 85 |
| WebP quality (0-100) | 60 | 75 | 90 | 85 |
| JPEG XL quality (0-100) | 60 | 75 | 90 | 85 |
| PNG compression level (0-6) | 0 | 3 | 6 | 3 |
| Lossy PNG (quantization)? (y/n) | | | | y |

At the end, the program shows a summary with the total space saved.

### The `FAILED_` Rule

After compressing, the program compares the file size in `ImagesIn` with the file in `ImagesOut`:

- If the compressed file is **smaller than or equal to** the original, the file in `ImagesOut` keeps its original name.
- If the compressed file is **larger**, the file in `ImagesOut` gets the `FAILED_` prefix (for example, `FAILED_photo.jpg`). This means the image was already well optimized at that level, and it may be worth trying another setting.

Before each run, any previous `FAILED_` file is removed, so the results always reflect the latest run.

## Recommended Settings for Websites

Websites load faster with lightweight images. For the web, you do not need print-quality files. Here are the recommendations for images going into client websites:

| Format | Recommended Value | Note |
|---|---|---|
| WebP (lossy) | 75 to 80 | Great balance. Use 80 for photos with fine details. |
| JPEG (lossy) | 75 to 80 | Same range as WebP. |
| JPEG XL | See note below | `libjxl`'s scale is not 0-100. |
| AVIF | Quality between 50 and 60 | This version **does not compress AVIF**. Use a conversion tool and adjust the setting there. |

**Rule of thumb:**
- Use **75** as a default when a website has many images.
- Use **80** for featured images, such as banners and product photos.
- Prefer **WebP** or **AVIF** for final delivery, since they are usually much lighter than JPEG at a similar visual quality.

In the table above, the default prompt value (85) is heavier than needed for websites.

### Before Compressing

- **Resize the image.** A 4000 px camera photo displayed at 1200 px wastes most of its file size. As a rough guide, use 1920 px width for banners and 1200 px for content. This version of the program **does not resize** images yet.
- **Compress from the original.** Each lossy re-compression degrades the image. If you convert to WebP and then compress the WebP again, the quality loss stacks up. Do the conversion and final compression once, starting from the original file.

## Makefile Commands

```bash
make help   # shows available commands
make run    # runs ./target/release/image-compress
```

`make run` executes the already compiled binary. Build it first with `cargo build --release`.

## Installation

### 1. Rust

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source ~/.cargo/env
```

### 2. System Dependencies (Linux)

This project uses the `libjxl` library (through `jpegxl-rs`). `oxipng` and `imagequant` also rely on native code:

```bash
sudo apt update
sudo apt install build-essential cmake pkg-config libjxl-dev
```

### 3. Build

```bash
cargo build --release
```

The first build may take a few minutes.

## Technical Notes

- **Lossy PNG:** quantization reduces the image to up to 256 colors. On screenshots and illustrations, the difference is usually small. On photos, artifacts such as color banding can appear, so answer `n` in those cases. If the quantized version is not smaller than the lossless one, the program keeps the lossless version.
- **Lossy JPEG, WebP, and JXL:** images are re-encoded from pixel data, so ICC color profiles may be removed. Photos with colors outside sRGB may show slight color shifts.
- **JPEG XL quality:** `libjxl` does not use the 0-100 scale shown in the prompt. It uses a *distance* scale (lower is better, and 1.0 is nearly lossless). Whether the entered value is converted correctly has not been confirmed yet. Before using it on websites, test a few images and compare the results.
- **AVIF:** not supported for input or output in this version. Decoding requires the C library `dav1d`.
- **Parallel processing:** files are processed in parallel with Rayon, using all available CPU cores.

## Credits & License

This project uses the **JPEG XL (`libjxl`)** library for JPEG XL support, along with other third-party crates and libraries that have their own licenses.

- libjxl: https://github.com/libjxl/libjxl

Third-party crates have their own licenses. Pay special attention to `imagequant`, which is licensed under GPL-3.0 or a commercial license. Use of this program is currently for personal and non-commercial purposes. If you distribute or sell the program, check the licenses first.

- Architecture, code, and documentation developed with the help of **Claude** (Anthropic), which assisted with planning, writing the code, and this README.
