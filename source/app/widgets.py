from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QSlider, QVBoxLayout, QWidget


class SpsLogo(QWidget):
    """SPS wordmark using the supplied light and dark brand assets."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(58)
        self.setAccessibleName("SPS LUT Editor")
        assets = Path(__file__).resolve().parents[1] / "assets"
        self.light_logo = QPixmap(str(assets / "sps-logo-black.png"))
        self.dark_logo = QPixmap(str(assets / "sps-logo-white.png"))

    def sizeHint(self) -> QSize:
        return QSize(180, 58)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        dark = self.palette().window().color().lightness() < 128
        accent = QColor("#66B6FF") if dark else QColor("#1769AA")
        foreground = QColor("#F5F8FF") if dark else QColor("#102A43")
        logo = self.dark_logo if dark else self.light_logo
        # Supplied images include transparent margins; crop only those margins
        # so the mark remains legible at compact sidebar size.
        if not logo.isNull():
            painter.drawPixmap(QRect(6, 3, 30, 52), logo, QRect(273, 76, 454, 849))
        else:
            painter.setPen(QPen(accent, 4.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawLine(8, 18, 32, 18)
            painter.drawLine(8, 29, 28, 29)
            painter.drawLine(12, 40, 32, 40)
        font = QFont(self.font())
        font.setBold(True); font.setPointSize(19)
        painter.setFont(font); painter.setPen(foreground)
        painter.drawText(46, 31, "SPS")
        small = QFont(self.font()); small.setPointSize(8); small.setLetterSpacing(QFont.AbsoluteSpacing, 1.1)
        painter.setFont(small); painter.setPen(accent)
        painter.drawText(48, 47, "LUT EDITOR")


class NumericControl(QWidget):
    changed = Signal(str)

    def __init__(self, label: str, minimum: float = -100, maximum: float = 100, step: float = 1, decimals: int = 0):
        super().__init__()
        self._scale = 100 if decimals else 1
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(round(minimum * self._scale), round(maximum * self._scale))
        self.spin = QDoubleSpinBox()
        self.spin.setRange(minimum, maximum)
        self.spin.setSingleStep(step)
        self.spin.setDecimals(decimals)
        self.spin.setFixedWidth(90)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel(label), 1)
        layout.addWidget(self.slider, 3)
        layout.addWidget(self.spin)
        self.slider.valueChanged.connect(lambda value: self.spin.setValue(value / self._scale))
        self.spin.valueChanged.connect(lambda value: self.slider.setValue(round(value * self._scale)))
        self.spin.valueChanged.connect(lambda value: self.changed.emit(self.text()))

    def text(self) -> str:
        return f"{self.spin.value():.{self.spin.decimals()}f}"

    def set_text(self, value: str) -> None:
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = 0
        self.spin.blockSignals(True)
        self.slider.blockSignals(True)
        self.spin.setValue(number)
        self.slider.setValue(round(number * self._scale))
        self.slider.blockSignals(False)
        self.spin.blockSignals(False)


def controls_panel(items: list[tuple[str, NumericControl]], intro: str = "") -> QWidget:
    widget = QWidget()
    layout = QVBoxLayout(widget)
    if intro:
        note = QLabel(intro)
        note.setWordWrap(True)
        note.setStyleSheet("color: #667085;")
        layout.addWidget(note)
    for _, control in items:
        layout.addWidget(control)
    layout.addStretch()
    return widget
