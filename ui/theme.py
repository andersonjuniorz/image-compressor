STYLESHEET = """
QMainWindow { background: #0f1117; }
QWidget#page { background: #0f1117; }
QScrollArea { background: transparent; border: none; }

QWidget {
    color: #e6e8ee;
    font-family: "Inter", "Ubuntu", "Cantarell", "Segoe UI", sans-serif;
    font-size: 13px;
}

QFrame#card {
    background: #171a23;
    border: 1px solid #262b38;
    border-radius: 14px;
}

QFrame#statBox {
    background: #111420;
    border: 1px solid #262b38;
    border-radius: 10px;
}

QLabel#title { font-size: 26px; font-weight: 700; color: #ffffff; }
QLabel#subtitle { color: #9aa3b5; font-size: 13px; }
QLabel#muted { color: #8a93a6; font-size: 12px; }
QLabel#sectionTitle { font-size: 15px; font-weight: 600; color: #ffffff; }
QLabel#fieldName { font-weight: 600; }
QLabel#fieldValue { color: #a5b4fc; font-weight: 600; }
QLabel#statValue { font-size: 22px; font-weight: 700; }

QLabel#badge {
    color: #a5b4fc;
    background: #1e2140;
    border: 1px solid #2f3566;
    border-radius: 10px;
    padding: 4px 10px;
    font-size: 12px;
}

QLabel#path {
    color: #c9cfdc;
    background: #111420;
    border: 1px solid #262b38;
    border-radius: 8px;
    padding: 9px 12px;
}

QPushButton {
    border-radius: 9px;
    padding: 9px 18px;
    font-weight: 600;
}
QPushButton#primary {
    background: #6366f1;
    color: #ffffff;
    border: none;
}
QPushButton#primary:hover { background: #7a7cf7; }
QPushButton#primary:pressed { background: #4f51d6; }
QPushButton#primary:disabled { background: #272c3b; color: #6b7285; }

QPushButton#secondary {
    background: #1f2330;
    border: 1px solid #323a4d;
    color: #e6e8ee;
}
QPushButton#secondary:hover { background: #272c3d; }
QPushButton#secondary:disabled { color: #6b7285; }

QSlider::groove:horizontal {
    height: 6px;
    background: #262b38;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: #6366f1;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #e6e8ee;
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}
QSlider::handle:horizontal:hover { background: #ffffff; }
QSlider::handle:horizontal:disabled { background: #4b5263; }
QSlider::sub-page:horizontal:disabled { background: #3a4050; }

QCheckBox { spacing: 10px; }
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1px solid #3a4258;
    background: #111420;
}
QCheckBox::indicator:checked {
    background: #6366f1;
    border-color: #6366f1;
}

QProgressBar {
    background: #111420;
    border: 1px solid #262b38;
    border-radius: 6px;
}
QProgressBar::chunk {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                stop: 0 #6366f1, stop: 1 #22d3ee);
    border-radius: 5px;
}

QListWidget {
    background: #111420;
    border: 1px solid #262b38;
    border-radius: 10px;
    padding: 6px;
    font-family: "JetBrains Mono", "Ubuntu Mono", monospace;
    font-size: 12px;
}
QListWidget::item { padding: 5px 6px; border-radius: 6px; }

QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 4px;
}
QScrollBar::handle:vertical {
    background: #2b3142;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #3a4258; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QMessageBox { background: #171a23; }

QPushButton#format {
    background: #1f2330;
    border: 1px solid #323a4d;
    border-radius: 9px;
    padding: 12px 22px;
    font-weight: 700;
    letter-spacing: 0.5px;
}
QPushButton#format:hover { border-color: #6366f1; color: #c7d2fe; }
QPushButton#format:pressed { background: #6366f1; color: #ffffff; }
QPushButton#format:disabled { color: #6b7285; border-color: #262b38; }

QLabel#chip {
    color: #a5b4fc;
    background: #1e2140;
    border: 1px solid #2f3566;
    border-radius: 10px;
    padding: 4px 12px;
    font-size: 12px;
    font-weight: 600;
}
    
"""
