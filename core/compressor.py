from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps, features

# Register the JPEG XL codec in Pillow, if the plugin is installed.
try:
    import pillow_jxl  # noqa: F401
    _HAS_JXL = True
except ImportError:
    _HAS_JXL = False

# Extensions the scanner accepts. JXL is added only when the plugin loads.
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
if _HAS_JXL:
    SUPPORTED_EXTENSIONS.add(".jxl")

# Prefix added to outputs that ended up larger than the original.
FAILED_PREFIX = "FAILED_"

# Best quantizer available: libimagequant if Pillow has it, otherwise fast octree.
_QUANT = (
    Image.Quantize.LIBIMAGEQUANT
    if features.check("libimagequant")
    else Image.Quantize.FASTOCTREE
)


# Compression parameters. The defaults are the recommended values.
@dataclass(frozen=True)
class Settings:
    jpeg_quality: int = 85
    webp_quality: int = 85
    jxl_quality: int = 85
    png_level: int = 3
    png_lossy: bool = True


# Keeps the alpha channel when present, otherwise uses plain RGB.
def _alpha_or_rgb(img: Image.Image) -> Image.Image:
    if img.mode in ("RGBA", "LA", "PA") or "transparency" in img.info:
        return img.convert("RGBA")
    return img.convert("RGB")


# Saves a PNG in memory with the given zlib level.
def _save_png(img: Image.Image, level: int) -> bytes:
    buf = BytesIO()
    img.save(buf, "PNG", optimize=True, compress_level=level)
    return buf.getvalue()


# Encodes a PNG, optionally trying the quantized (lossy) version too.
def _encode_png(img: Image.Image, s: Settings) -> bytes:
    lossless = _save_png(img, s.png_level)
    if not s.png_lossy:
        return lossless

    # Use the quantized version only if it is smaller.
    try:
        quantized = _alpha_or_rgb(img).quantize(colors=256, method=_QUANT)
        candidate = _save_png(quantized, s.png_level)
    except Exception:
        # Quantization failed, so fall back to the lossless result.
        return lossless

    return candidate if len(candidate) < len(lossless) else lossless


# Encodes the image in the same format as the source file.
def _encode(img: Image.Image, ext: str, s: Settings) -> bytes:
    if ext == ".png":
        return _encode_png(img, s)

    buf = BytesIO()
    if ext in (".jpg", ".jpeg"):
        # JPEG has no alpha channel, so convert to RGB first.
        img.convert("RGB").save(
            buf, "JPEG", quality=s.jpeg_quality, optimize=True, progressive=True
        )
    elif ext == ".webp":
        _alpha_or_rgb(img).save(buf, "WEBP", quality=s.webp_quality, method=6)
    elif ext == ".jxl":
        _alpha_or_rgb(img).save(buf, "JXL", quality=s.jxl_quality)
    else:
        raise ValueError(f"formato não suportado: {ext}")
    return buf.getvalue()


# Compresses src into dst without metadata.
# Returns the FAILED_ path if the result is larger than the original.
def compress_file(src: Path, dst: Path, s: Settings) -> Path:
    # Remove the FAILED_ file left by a previous run.
    dst.with_name(FAILED_PREFIX + dst.name).unlink(missing_ok=True)

    ext = src.suffix.lower()
    with Image.open(src) as im:
        im.load()
        # Apply the EXIF rotation to the pixels before metadata is dropped.
        img = ImageOps.exif_transpose(im)

    data = _encode(img, ext, s)
    dst.write_bytes(data)

    # Rename the file if it grew, so the user can see it.
    if len(data) > src.stat().st_size:
        failed = dst.with_name(FAILED_PREFIX + dst.name)
        dst.replace(failed)
        return failed
    return dst
