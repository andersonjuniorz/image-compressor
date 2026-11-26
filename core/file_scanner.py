from pathlib import Path

from .compressor import FAILED_PREFIX, SUPPORTED_EXTENSIONS

# Output folder, created inside the chosen folder. It is skipped during the scan.
OUTPUT_DIR_NAME = "ImagesCompressed"


# Recursively finds the supported images in root.
# Skips the output folder and files already marked with FAILED_.
def scan(root: Path) -> list[Path]:
    files: list[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        # Ignore anything inside the output folder, so results are not compressed again.
        if rel.parts[0] == OUTPUT_DIR_NAME:
            continue
        # Ignore files from a previous run that were marked as FAILED_.
        if p.name.startswith(FAILED_PREFIX):
            continue
        if p.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(p)
    return sorted(files)
