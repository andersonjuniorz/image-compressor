from datetime import datetime
from pathlib import Path

from .batch import JobResult
from .compressor import Settings
from .file_scanner import OUTPUT_DIR_NAME


# Builds the text report shown in the output folder.
def build_report(
    results: list[JobResult],
    root: Path,
    settings: Settings,
    started: datetime,
    finished: datetime,
) -> str:
    # Split the results into three groups.
    ok = [r for r in results if r.ok and not r.failed]
    failed = [r for r in results if r.ok and r.failed]
    errors = [r for r in results if not r.ok]

    lines = [
        "Relatório de compressão",
        f"Pasta: {root}",
        f"Início: {started:%d/%m/%Y %H:%M:%S}",
        f"Fim: {finished:%d/%m/%Y %H:%M:%S}",
        "",
        # Settings used in this run, so the report can be compared later.
        "Parâmetros:",
        f"  JPEG: {settings.jpeg_quality}",
        f"  WebP: {settings.webp_quality}",
        f"  JPEG XL: {settings.jxl_quality}",
        f"  PNG nível: {settings.png_level}",
        f"  PNG com perda: {'sim' if settings.png_lossy else 'não'}",
        "",
        f"Total: {len(results)}",
        f"Comprimidos: {len(ok)}",
        f"FAILED_ (maiores que o original): {len(failed)}",
        f"Erros: {len(errors)}",
    ]

    # List the files that grew, so the user knows what to retry.
    if failed:
        lines += ["", "Arquivos FAILED_:"]
        lines += [f"- {r.job.rel}" for r in failed]

    # List the files that could not be processed, with the error message.
    if errors:
        lines += ["", "Erros:"]
        lines += [f"- {r.job.rel}: {r.error}" for r in errors]

    return "\n".join(lines)


# Writes the report to relatorio.txt inside the output folder.
def save_report(text: str, root: Path) -> Path:
    out = root / OUTPUT_DIR_NAME / "relatorio.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    return out
