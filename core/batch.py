import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from .compressor import Settings, compress_file


# One file to process: source, output and the path relative to the root folder.
@dataclass(frozen=True)
class Job:
    src: Path
    dst: Path
    rel: Path


# Outcome of one job. Holds sizes on success and the error message on failure.
@dataclass(frozen=True)
class JobResult:
    job: Job
    ok: bool
    original: int = 0
    output: int = 0
    failed: bool = False  # True when the output was larger and got the FAILED_ prefix.
    error: str = ""


# Compresses one file. Errors are returned as a result, so the batch keeps going.
def run_job(job: Job, settings: Settings) -> JobResult:
    try:
        # Make sure the output subfolder exists before writing.
        job.dst.parent.mkdir(parents=True, exist_ok=True)
        original = job.src.stat().st_size
        final = compress_file(job.src, job.dst, settings)
        output = final.stat().st_size
        return JobResult(
            job=job,
            ok=True,
            original=original,
            output=output,
            # compress_file returns a different path when it renamed the file to FAILED_.
            failed=(final != job.dst),
        )
    except Exception as exc:  # one bad file must not stop the whole batch
        return JobResult(job=job, ok=False, error=f"{type(exc).__name__}: {exc}")


# Runs all jobs in a background thread, so the GUI stays responsive.
class BatchWorker(QThread):
    progress = Signal(int, int)    # done, total
    item_done = Signal(object)     # one JobResult, emitted as each file finishes
    finished_batch = Signal(list)  # all JobResults, emitted once at the end

    def __init__(self, jobs: list[Job], settings: Settings, parent=None):
        super().__init__(parent)
        self._jobs = jobs
        self._settings = settings

    # Thread entry point. Runs in the worker thread, not the GUI thread.
    def run(self):
        # Leave one core free for the GUI. Use at least one worker.
        workers = max(1, (os.cpu_count() or 2) - 1)
        results: list[JobResult] = []

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(run_job, j, self._settings) for j in self._jobs]

            # Handle each result as soon as it finishes, not in submission order.
            for done, fut in enumerate(as_completed(futures), 1):
                result = fut.result()
                results.append(result)
                self.item_done.emit(result)
                self.progress.emit(done, len(futures))

        self.finished_batch.emit(results)
