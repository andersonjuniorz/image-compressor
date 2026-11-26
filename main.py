import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from core.batch import BatchWorker, Job, JobResult
from core.compressor import Settings
from core.file_scanner import OUTPUT_DIR_NAME, scan
from core.report import build_report, save_report
from ui.theme import STYLESHEET

# Default compression settings, used on startup and by the reset button.
DEFAULTS = Settings()

# Colors used in the per-file log.
COLOR_OK = QColor("#34d399")
COLOR_WARN = QColor("#fbbf24")
COLOR_ERR = QColor("#f87171")


# Formats a byte count as KB or MB.
def fmt_size(n: int) -> str:
    if n >= 1024 * 1024:
        return f"{n / (1024 * 1024):.2f} MB"
    return f"{n / 1024:.1f} KB"


# Returns the percentage saved (negative if the file grew).
def saving(original: int, output: int) -> float:
    return (1 - output / original) * 100 if original else 0.0


# Creates a card frame with a vertical layout.
def make_card() -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(24, 22, 24, 22)
    layout.setSpacing(14)
    return frame, layout


# Creates a section title label.
def section(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("sectionTitle")
    return label


# Creates a small, wrapped gray label.
def muted(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("muted")
    label.setWordWrap(True)
    return label


# Slider row with a name, the current value, and a hint.
class ParamRow(QWidget):
    """Slider with label, current value and hint. Marks the recommended value."""

    def __init__(self, label: str, minimum: int, maximum: int, default: int, hint: str):
        super().__init__()
        self.default = default

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Header row: name on the left, value on the right.
        head = QHBoxLayout()
        name = QLabel(label)
        name.setObjectName("fieldName")
        self.value_label = QLabel()
        self.value_label.setObjectName("fieldValue")
        head.addWidget(name)
        head.addStretch()
        head.addWidget(self.value_label)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(minimum, maximum)
        self.slider.setValue(default)
        self.slider.valueChanged.connect(self._refresh_label)

        layout.addLayout(head)
        layout.addWidget(self.slider)
        layout.addWidget(muted(hint))
        self._refresh_label(default)

    # Updates the value text and adds a tag when it is the default.
    def _refresh_label(self, value: int):
        tag = "  · recomendado" if value == self.default else ""
        self.value_label.setText(f"{value}{tag}")

    # Returns the current slider value.
    def value(self) -> int:
        return self.slider.value()

    # Moves the slider back to the default value.
    def reset(self):
        self.slider.setValue(self.default)


# Small box that shows a number and a caption.
class StatBox(QFrame):
    def __init__(self, caption: str):
        super().__init__()
        self.setObjectName("statBox")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)
        self.value = QLabel("0")
        self.value.setObjectName("statValue")
        layout.addWidget(self.value)
        layout.addWidget(muted(caption))

    # Sets the number and an optional color.
    def set_value(self, text: str, color: str | None = None):
        self.value.setText(text)
        self.value.setStyleSheet(f"color: {color};" if color else "")


# Main window with all the sections.
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Compressor")
        self.resize(780, 900)

        # State shared between the UI actions.
        self.root: Path | None = None
        self.files: list[Path] = []
        self.output_dir: Path | None = None
        self.worker: BatchWorker | None = None
        self.current_settings = DEFAULTS
        self.started_at = datetime.now()
        self._busy = False

        # Scroll area, so the page works on small windows.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        page = QWidget()
        page.setObjectName("page")
        scroll.setWidget(page)
        self.setCentralWidget(scroll)

        layout = QVBoxLayout(page)
        layout.setContentsMargins(36, 32, 36, 32)
        layout.setSpacing(18)

        # Add the sections from top to bottom.
        layout.addWidget(self._build_header())
        layout.addWidget(self._build_folder_card())
        layout.addWidget(self._build_settings_card())
        layout.addWidget(self._build_run_card())
        layout.addWidget(self._build_log_card())
        layout.addWidget(self._build_summary_card())
        layout.addStretch()

        self._refresh_state()

    # ---------- UI construction ----------

    # Title, description and format badge.
    def _build_header(self) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        title = QLabel("Image Compressor")
        title.setObjectName("title")

        subtitle = QLabel(
            "Reduza o peso das suas imagens em lote, mantendo a qualidade visível. "
            "Escolha uma pasta, ajuste os parâmetros e as versões comprimidas "
            f"serão salvas em {OUTPUT_DIR_NAME}."
        )
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)

        badge = QLabel("PNG  ·  JPG  ·  WebP  ·  JPEG XL")
        badge.setObjectName("badge")

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(badge, 0, Qt.AlignLeft)
        return box

    # Folder picker and the path/file count labels.
    def _build_folder_card(self) -> QFrame:
        frame, layout = make_card()
        layout.addWidget(section("1. Pasta de imagens"))
        layout.addWidget(
            muted("As imagens dentro da pasta, inclusive em subpastas, serão comprimidas.")
        )

        row = QHBoxLayout()
        self.btn_pick = QPushButton("Buscar pasta")
        self.btn_pick.setObjectName("primary")
        self.btn_pick.setCursor(Qt.PointingHandCursor)
        self.btn_pick.clicked.connect(self.pick_folder)
        row.addWidget(self.btn_pick)
        row.addStretch()
        layout.addLayout(row)

        self.lbl_path = QLabel("Nenhuma pasta selecionada")
        self.lbl_path.setObjectName("path")
        self.lbl_path.setWordWrap(True)
        self.lbl_count = muted("")

        layout.addWidget(self.lbl_path)
        layout.addWidget(self.lbl_count)
        return frame

    # Sliders, PNG lossy checkbox and the reset button.
    def _build_settings_card(self) -> QFrame:
        frame, layout = make_card()
        layout.addWidget(section("2. Parâmetros"))
        layout.addWidget(
            muted("Os valores recomendados já vêm selecionados. Para sites, 75 a 80 costuma ser ótimo.")
        )

        self.jpeg = ParamRow("Qualidade JPEG", 60, 90, DEFAULTS.jpeg_quality,
                             "Escala de 0 a 100. Para sites: 75 a 80.")
        self.webp = ParamRow("Qualidade WebP", 60, 90, DEFAULTS.webp_quality,
                             "Escala de 0 a 100. Para sites: 75 a 80.")
        self.jxl = ParamRow("Qualidade JPEG XL", 60, 90, DEFAULTS.jxl_quality,
                            "Escala de 0 a 100.")
        self.png = ParamRow("Nível de compressão PNG", 0, 6, DEFAULTS.png_level,
                            "0 é mais rápido e pesado; 6 é mais lento e leve.")
        # Keep all sliders in one list, so they can be enabled or reset together.
        self.rows = [self.jpeg, self.webp, self.jxl, self.png]
        for row in self.rows:
            layout.addWidget(row)

        self.chk_lossy = QCheckBox("PNG com perda (quantização para 256 cores)")
        self.chk_lossy.setChecked(DEFAULTS.png_lossy)
        layout.addWidget(self.chk_lossy)
        layout.addWidget(
            muted("Muito eficiente em capturas de tela e ilustrações. "
                  "Em fotos pode aparecer banding; nesse caso, desmarque.")
        )

        self.btn_reset = QPushButton("Restaurar recomendados")
        self.btn_reset.setObjectName("secondary")
        self.btn_reset.setCursor(Qt.PointingHandCursor)
        self.btn_reset.clicked.connect(self.reset_settings)
        layout.addWidget(self.btn_reset, 0, Qt.AlignLeft)
        return frame

    # Start button, progress bar and status line.
    def _build_run_card(self) -> QFrame:
        frame, layout = make_card()
        layout.addWidget(section("3. Compressão"))

        self.btn_start = QPushButton("Iniciar compressão")
        self.btn_start.setObjectName("primary")
        self.btn_start.setMinimumHeight(44)
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.clicked.connect(self.start)
        layout.addWidget(self.btn_start)

        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(12)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.lbl_status = muted("Aguardando pasta.")
        layout.addWidget(self.lbl_status)
        return frame

    # List that shows one line per processed file.
    def _build_log_card(self) -> QFrame:
        frame, layout = make_card()
        layout.addWidget(section("Progresso por arquivo"))

        self.log = QListWidget()
        self.log.setMinimumHeight(220)
        self.log.setSelectionMode(QListWidget.NoSelection)
        self.log.setFocusPolicy(Qt.NoFocus)
        layout.addWidget(self.log)
        return frame

    # Summary card, hidden until the batch finishes.
    def _build_summary_card(self) -> QFrame:
        self.summary = QFrame()
        self.summary.setObjectName("card")
        layout = QVBoxLayout(self.summary)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)

        layout.addWidget(section("Resultado"))

        stats = QHBoxLayout()
        stats.setSpacing(12)
        self.st_ok = StatBox("Comprimidos")
        self.st_failed = StatBox("FAILED_ (maior que o original)")
        self.st_err = StatBox("Erros")
        for box in (self.st_ok, self.st_failed, self.st_err):
            stats.addWidget(box)
        layout.addLayout(stats)

        self.lbl_totals = muted("")
        layout.addWidget(self.lbl_totals)

        self.btn_open = QPushButton("Abrir pasta de resultados")
        self.btn_open.setObjectName("secondary")
        self.btn_open.setCursor(Qt.PointingHandCursor)
        self.btn_open.clicked.connect(self.open_output)
        layout.addWidget(self.btn_open, 0, Qt.AlignLeft)

        self.summary.hide()
        return self.summary

    # ---------- state and actions ----------

    # Enables or disables controls based on whether a batch is running.
    def _refresh_state(self):
        busy = self._busy
        self.btn_pick.setEnabled(not busy)
        self.btn_start.setEnabled(not busy and bool(self.files))
        self.btn_reset.setEnabled(not busy)
        self.chk_lossy.setEnabled(not busy)
        for row in self.rows:
            row.setEnabled(not busy)

    # Reads the current UI values into a Settings object.
    def _read_settings(self) -> Settings:
        return Settings(
            jpeg_quality=self.jpeg.value(),
            webp_quality=self.webp.value(),
            jxl_quality=self.jxl.value(),
            png_level=self.png.value(),
            png_lossy=self.chk_lossy.isChecked(),
        )

    # Restores all sliders and the checkbox to their defaults.
    def reset_settings(self):
        for row in self.rows:
            row.reset()
        self.chk_lossy.setChecked(DEFAULTS.png_lossy)

    # Opens a folder dialog and scans the chosen folder for images.
    def pick_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Selecione a pasta com as imagens", str(Path.home())
        )
        if not folder:
            return

        self.root = Path(folder)
        self.files = scan(self.root)
        self.output_dir = self.root / OUTPUT_DIR_NAME
        self.lbl_path.setText(str(self.root))
        self.log.clear()
        self.summary.hide()
        self.progress.setValue(0)

        if not self.files:
            self.lbl_count.setText("Nenhuma imagem compatível encontrada (PNG, JPG, WebP, JXL).")
            self.lbl_status.setText("Escolha outra pasta.")
        else:
            # Count the files per extension to show in the label.
            counts = Counter(p.suffix.lower().lstrip(".").upper() for p in self.files)
            detail = " · ".join(f"{ext}: {n}" for ext, n in sorted(counts.items()))
            self.lbl_count.setText(f"{len(self.files)} imagens encontradas  ({detail})")
            self.lbl_status.setText("Pronto para iniciar.")

        self._refresh_state()

    # Builds one job per file and starts the background worker.
    def start(self):
        if not self.files or self.root is None or self._busy:
            return

        self.current_settings = self._read_settings()
        # Each job keeps the source path, the output path and the relative path.
        jobs = [
            Job(src=p, dst=self.output_dir / p.relative_to(self.root),
                rel=p.relative_to(self.root))
            for p in self.files
        ]

        self.log.clear()
        self.summary.hide()
        self.progress.setRange(0, len(jobs))
        self.progress.setValue(0)
        self.started_at = datetime.now()
        self.lbl_status.setText("Comprimindo...")

        self._busy = True
        self._refresh_state()

        # Signals update the UI while the worker runs in another thread.
        self.worker = BatchWorker(jobs, self.current_settings)
        self.worker.progress.connect(self._on_progress)
        self.worker.item_done.connect(self._on_item)
        self.worker.finished_batch.connect(self._on_finished)
        self.worker.start()

    # Updates the progress bar and status text.
    def _on_progress(self, done: int, total: int):
        self.progress.setValue(done)
        self.lbl_status.setText(f"Processando {done} de {total}...")

    # Adds one colored line to the log for each finished file.
    def _on_item(self, res: JobResult):
        rel = res.job.rel
        if not res.ok:
            text = f"✖  {rel}   {res.error}"
            color = COLOR_ERR
        elif res.failed:
            # The file was renamed with FAILED_, so the log shows the new name.
            failed_rel = rel.with_name("FAILED_" + rel.name)
            increase = (res.output / res.original - 1) * 100 if res.original else 0.0
            text = (f"⚠  {failed_rel}   {fmt_size(res.original)} → {fmt_size(res.output)}"
                    f"   aumentou {increase:.1f}%")
            color = COLOR_WARN
        else:
            text = (f"✔  {rel}   {fmt_size(res.original)} → {fmt_size(res.output)}"
                    f"   economia {saving(res.original, res.output):.1f}%")
            color = COLOR_OK

        item = QListWidgetItem(text)
        item.setForeground(color)
        self.log.addItem(item)
        self.log.scrollToBottom()

    # Shows the totals, saves the report and displays the summary.
    def _on_finished(self, results: list[JobResult]):
        self._busy = False
        self._refresh_state()
        finished_at = datetime.now()

        # Split the results into three groups.
        ok = [r for r in results if r.ok and not r.failed]
        failed = [r for r in results if r.ok and r.failed]
        errors = [r for r in results if not r.ok]

        # Totals include only the files that got smaller.
        total_original = sum(r.original for r in ok)
        total_output = sum(r.output for r in ok)

        self.st_ok.set_value(str(len(ok)), "#34d399")
        self.st_failed.set_value(str(len(failed)), "#fbbf24" if failed else None)
        self.st_err.set_value(str(len(errors)), "#f87171" if errors else None)
        self.lbl_totals.setText(
            f"Original: {fmt_size(total_original)}  →  Final: {fmt_size(total_output)}  ·  "
            f"economia de {saving(total_original, total_output):.1f}% "
            f"(sem contar os FAILED_)"
        )

        report = build_report(results, self.root, self.current_settings,
                              self.started_at, finished_at)
        elapsed = (finished_at - self.started_at).total_seconds()
        try:
            save_report(report, self.root)
            report_note = f"Relatório salvo em {OUTPUT_DIR_NAME}/relatorio.txt."
        except OSError as exc:
            report_note = f"Não foi possível salvar o relatório: {exc}"

        self.lbl_status.setText(f"Concluído em {elapsed:.1f}s. {report_note}")
        self.summary.show()
        QMessageBox.information(
            self, "Compressão concluída",
            f"{len(ok)} imagens comprimidas, {len(failed)} marcadas como FAILED_."
        )

    # Opens the output folder in the system file manager.
    def open_output(self):
        if self.output_dir and self.output_dir.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.output_dir)))

    # Blocks closing the window while a batch is still running.
    def closeEvent(self, event):
        if self._busy:
            QMessageBox.information(self, "Aguarde", "A compressão ainda está em andamento.")
            event.ignore()
            return
        event.accept()


# Creates the application, applies the theme and starts the event loop.
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
