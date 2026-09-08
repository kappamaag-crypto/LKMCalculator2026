"""Глобальные стили приложения."""

APP_STYLE = """
QMainWindow, QWidget {
    background-color: #f5f6f8;
    font-family: "Segoe UI", "DejaVu Sans", sans-serif;
    font-size: 13px;
    color: #1a1a2e;
}
QTabWidget::pane {
    border: 1px solid #d0d4dc;
    border-radius: 6px;
    background: #ffffff;
    top: -1px;
}
QTabBar::tab {
    background: #e8eaef;
    border: 1px solid #d0d4dc;
    border-bottom: none;
    padding: 8px 18px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    min-width: 90px;
}
QTabBar::tab:selected {
    background: #ffffff;
    font-weight: 600;
    color: #1a56db;
}
QTabBar::tab:hover:!selected {
    background: #f0f2f5;
}
QGroupBox {
    font-weight: 600;
    border: 1px solid #d0d4dc;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 14px;
    background: #ffffff;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #374151;
}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit {
    border: 1px solid #c5cad3;
    border-radius: 4px;
    padding: 5px 8px;
    background: #ffffff;
    selection-background-color: #1a56db;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border-color: #1a56db;
}
QPushButton {
    background-color: #1a56db;
    color: white;
    border: none;
    border-radius: 5px;
    padding: 7px 16px;
    font-weight: 600;
    min-height: 18px;
}
QPushButton:hover {
    background-color: #1e40af;
}
QPushButton:pressed {
    background-color: #1e3a8a;
}
QPushButton:disabled {
    background-color: #9ca3af;
}
QPushButton[secondary="true"] {
    background-color: #ffffff;
    color: #1a56db;
    border: 1px solid #1a56db;
}
QPushButton[secondary="true"]:hover {
    background-color: #eff6ff;
}
QPushButton[danger="true"] {
    background-color: #dc2626;
}
QTableWidget, QTableView {
    border: 1px solid #d0d4dc;
    border-radius: 4px;
    gridline-color: #e5e7eb;
    background: #ffffff;
    alternate-background-color: #f9fafb;
}
QHeaderView::section {
    background-color: #f3f4f6;
    border: none;
    border-bottom: 1px solid #d0d4dc;
    border-right: 1px solid #e5e7eb;
    padding: 6px 8px;
    font-weight: 600;
}
QStatusBar {
    background: #ffffff;
    border-top: 1px solid #d0d4dc;
}
QLabel[heading="true"] {
    font-size: 16px;
    font-weight: 700;
    color: #111827;
}
QLabel[subheading="true"] {
    font-size: 13px;
    color: #6b7280;
}
QLabel[score="true"] {
    font-size: 18px;
    font-weight: 700;
    color: #059669;
}
QFrame[card="true"] {
    background: #ffffff;
    border: 1px solid #d0d4dc;
    border-radius: 8px;
}
"""
