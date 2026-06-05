"""Reusable animation helpers (Nothing OS-style micro-interactions)."""
from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve, QParallelAnimationGroup, QPoint, QPropertyAnimation,
    QSequentialAnimationGroup, QSize, Qt,
)
from PySide6.QtWidgets import QGraphicsColorizeEffect, QGraphicsOpacityEffect, QWidget


def _opacity_effect(widget: QWidget) -> QGraphicsOpacityEffect:
    eff = widget.graphicsEffect()
    if not isinstance(eff, QGraphicsOpacityEffect):
        eff = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(eff)
    return eff


def fade_in(widget: QWidget, duration_ms: int = 200) -> QPropertyAnimation:
    eff = _opacity_effect(widget)
    eff.setOpacity(0.0)
    a = QPropertyAnimation(eff, b"opacity", widget)
    a.setDuration(duration_ms)
    a.setStartValue(0.0)
    a.setEndValue(1.0)
    a.setEasingCurve(QEasingCurve.Type.OutCubic)
    a.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
    return a


def fade_out(widget: QWidget, duration_ms: int = 160, on_done=None) -> QPropertyAnimation:
    eff = _opacity_effect(widget)
    a = QPropertyAnimation(eff, b"opacity", widget)
    a.setDuration(duration_ms)
    a.setStartValue(1.0)
    a.setEndValue(0.0)
    a.setEasingCurve(QEasingCurve.Type.InCubic)
    if on_done:
        a.finished.connect(on_done)
    a.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
    return a


def slide_up_in(widget: QWidget, distance: int = 8, duration_ms: int = 220) -> QPropertyAnimation:
    start_pos = widget.pos()
    widget.move(start_pos.x(), start_pos.y() + distance)
    eff = _opacity_effect(widget)
    eff.setOpacity(0.0)
    a_pos = QPropertyAnimation(widget, b"pos", widget)
    a_pos.setDuration(duration_ms)
    a_pos.setStartValue(widget.pos())
    a_pos.setEndValue(start_pos)
    a_pos.setEasingCurve(QEasingCurve.Type.OutCubic)
    a_pos.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
    fade_in(widget, duration_ms)
    return a_pos


def slide_up_stagger(widgets: list[QWidget], delay_ms: int = 22,
                     distance: int = 6, duration_ms: int = 220) -> None:
    for i, w in enumerate(widgets):
        start_pos = w.pos()
        w.move(start_pos.x(), start_pos.y() + distance)
        eff = _opacity_effect(w)
        eff.setOpacity(0.0)
        a_pos = QPropertyAnimation(w, b"pos", w)
        a_pos.setDuration(duration_ms)
        a_pos.setStartValue(w.pos())
        a_pos.setEndValue(start_pos)
        a_pos.setEasingCurve(QEasingCurve.Type.OutCubic)
        a_op = QPropertyAnimation(eff, b"opacity", w)
        a_op.setDuration(duration_ms)
        a_op.setStartValue(0.0)
        a_op.setEndValue(1.0)
        a_op.setEasingCurve(QEasingCurve.Type.OutCubic)

        if i == 0:
            a_pos.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
            a_op.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        else:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(i * delay_ms, a_pos.start)
            QTimer.singleShot(i * delay_ms, a_op.start)


def pulse(widget: QWidget, low=5, high=9, duration_ms=1100) -> QPropertyAnimation:
    """Continuous pulse — used for the red dot during active downloads."""
    a = QPropertyAnimation(widget, b"minimumSize", widget)
    a.setDuration(duration_ms)
    a.setStartValue(QSize(low, low))
    a.setKeyValueAt(0.5, QSize(high, high))
    a.setEndValue(QSize(low, low))
    a.setEasingCurve(QEasingCurve.Type.InOutSine)
    a.setLoopCount(-1)
    a.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
    return a


def press_pulse(widget: QWidget) -> None:
    """Brief scale-down feedback on press."""
    eff = widget.graphicsEffect()
    if not isinstance(eff, QGraphicsOpacityEffect):
        eff = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(eff)
    a = QPropertyAnimation(eff, b"opacity", widget)
    a.setDuration(120)
    a.setStartValue(1.0)
    a.setKeyValueAt(0.5, 0.6)
    a.setEndValue(1.0)
    a.setEasingCurve(QEasingCurve.Type.OutCubic)
    a.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)


def ripple_out(widget: QWidget, max_size: int = 48, duration_ms: int = 420) -> None:
    """One-shot ripple expanding from a small dot to fade out."""
    eff = _opacity_effect(widget)
    eff.setOpacity(1.0)
    widget.show()

    a_size = QPropertyAnimation(widget, b"size", widget)
    a_size.setDuration(duration_ms)
    a_size.setStartValue(QSize(8, 8))
    a_size.setEndValue(QSize(max_size, max_size))
    a_size.setEasingCurve(QEasingCurve.Type.OutCubic)

    a_op = QPropertyAnimation(eff, b"opacity", widget)
    a_op.setDuration(duration_ms)
    a_op.setStartValue(1.0)
    a_op.setEndValue(0.0)
    a_op.setEasingCurve(QEasingCurve.Type.OutCubic)

    a_op.finished.connect(lambda: (widget.hide(), widget.deleteLater()))
    a_size.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
    a_op.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)


def dot_colorize_pulse(widget: QWidget, base_color: str, glow_color: str,
                       duration_ms: int = 1400) -> QPropertyAnimation:
    """Colorize effect that pulses a red dot — visible 'alive' feel."""
    eff = widget.graphicsEffect()
    if not isinstance(eff, QGraphicsColorizeEffect):
        eff = QGraphicsColorizeEffect(widget)
        widget.setGraphicsEffect(eff)
    eff.setColor(Qt.GlobalColor.red)
    a = QPropertyAnimation(eff, b"strength", widget)
    a.setDuration(duration_ms)
    a.setStartValue(0.0)
    a.setKeyValueAt(0.5, 0.6)
    a.setEndValue(0.0)
    a.setEasingCurve(QEasingCurve.Type.InOutSine)
    a.setLoopCount(-1)
    a.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
    return a
