import random
import sys
import tempfile
from pathlib import Path

from PIL import Image

# Lets the script import the core package from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.compressor import (  # noqa: E402
    FAILED_PREFIX,
    SUPPORTED_EXTENSIONS,
    Settings,
    compress_file,
)


# Creates one noisy image (hard to compress) and one flat image with alpha.
def make_images(folder: Path) -> None:
    random.seed(1)
    width, height = 400, 300
    noise = Image.new("RGB", (width, height))
    noise.putdata([
        (random.randrange(256), random.randrange(256), random.randrange(256))
        for _ in range(width * height)
    ])
    noise.save(folder / "noise.png")
    noise.save(folder / "noise.jpg", quality=95)
    noise.save(folder / "noise.webp", quality=95)

    flat = Image.new("RGBA", (width, height), (30, 120, 200, 255))
    flat.save(folder / "flat_alpha.png")
    flat.save(folder / "flat_alpha.webp", lossless=True)

    # Add a JPEG XL file only when the plugin is installed.
    if ".jxl" in SUPPORTED_EXTENSIONS:
        flat.save(folder / "flat_alpha.jxl", quality=90)


# Checks that the output opens and has no EXIF metadata.
def check_output(path: Path) -> None:
    assert path.exists(), f"missing output: {path.name}"
    with Image.open(path) as im:
        im.load()
        assert "exif" not in im.info, f"EXIF left in {path.name}"


def main() -> int:
    settings = Settings()
    failures = 0

    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        make_images(folder)
        out_dir = folder / "out"
        out_dir.mkdir()

        for src in sorted(folder.iterdir()):
            if src.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            dst = out_dir / src.name
            try:
                result = compress_file(src, dst, settings)
                # A FAILED_ result must really be larger than the source.
                if result.name.startswith(FAILED_PREFIX):
                    assert result.stat().st_size > src.stat().st_size
                check_output(result)
                print(f"[OK]   {src.name}")
            except Exception as exc:
                failures += 1
                print(f"[ERRO] {src.name}: {type(exc).__name__}: {exc}")

    print(f"\nFalhas: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
