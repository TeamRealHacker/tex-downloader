"""Download queue: 5-slot concurrent FIFO."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from .config import load
from .downloader import DownloadRequest, DownloaderWorker


@dataclass
class QueueItem:
    item_id: str
    req: DownloadRequest
    status: str = "pending"      # pending | active | paused | done | error | cancelled
    percent: float = 0.0
    speed: float = 0.0
    eta: float = 0.0
    downloaded: int = 0
    total: int = 0
    started_at: float = 0.0
    finished_at: float = 0.0
    result_path: str = ""
    error: str = ""
    worker: DownloaderWorker | None = field(default=None, repr=False)


class DownloadQueue(QObject):
    added = Signal(str)        # item_id
    started = Signal(str)      # item_id
    progress = Signal(str, float, float, float, int, int)
    status_changed = Signal(str, str)
    finished = Signal(str, bool, str)
    slot_changed = Signal(int, int)  # active_count, total_slots
    cleared = Signal()

    def __init__(self, max_slots: int | None = None, parent=None):
        super().__init__(parent)
        cfg = load()
        configured = max_slots if max_slots is not None else int(cfg.get("concurrency", 0))
        self._items: dict[str, QueueItem] = {}
        self._order: list[str] = []
        # Treat 0 / negative as "unlimited" — user wants no cap.
        if configured <= 0:
            self._max = 1_000_000
            self._unlimited = True
        else:
            self._max = max(1, configured)
            self._unlimited = False

    # --- Public API ---
    def set_max_slots(self, n: int) -> None:
        # User asked for "unlimited" — keep the Settings key for back-compat
        # but never throttle below a generous cap. The display in the queue
        # bar shows "∞" when we hit the cap.
        try:
            n = int(n)
        except (TypeError, ValueError):
            n = 0
        # 0 / negative => unlimited. Otherwise the configured number.
        if n <= 0:
            self._max = 1_000_000
            self._unlimited = True
        else:
            self._max = max(1, n)
            self._unlimited = False
        self._emit_slots()

    def slots(self) -> int:
        return self._max

    def is_unlimited(self) -> bool:
        return getattr(self, "_unlimited", True)

    def active_count(self) -> int:
        return sum(1 for it in self._items.values() if it.status == "active")

    def pending_count(self) -> int:
        """Count items that are still waiting or in progress."""
        return sum(1 for it in self._items.values()
                   if it.status in ("active", "paused", "pending"))

    def get_item(self, item_id: str) -> QueueItem | None:
        return self._items.get(item_id)

    def all_items(self) -> list[QueueItem]:
        return [self._items[k] for k in self._order]

    def cancel(self, item_id: str) -> None:
        it = self._items.get(item_id)
        if not it:
            return
        if it.status == "pending":
            # Pending items have no worker yet — just mark as cancelled.
            it.status = "cancelled"
            self.status_changed.emit(item_id, "cancelled")
            self._emit_slots()
            return
        if it.worker and it.status in ("active", "paused"):
            it.worker.cancel()

    def cancel_all(self) -> None:
        for it in list(self._items.values()):
            self.cancel(it.item_id)

    def toggle_pause(self, item_id: str) -> None:
        it = self._items.get(item_id)
        if not it or not it.worker:
            return
        if it.status == "active":
            # Snapshot status BEFORE the toggle to avoid TOCTOU race.
            it.status = "paused"
            self.status_changed.emit(item_id, "paused")
            it.worker.toggle_pause()
        elif it.status == "paused":
            it.status = "active"
            self.status_changed.emit(item_id, "active")
            it.worker.toggle_pause()

    def clear_finished(self) -> None:
        keep_order = [k for k in self._order if self._items[k].status not in ("done", "error", "cancelled")]
        removed = [k for k in self._order if k not in keep_order]
        for k in removed:
            it = self._items.pop(k, None)
            # Disconnect worker signals to prevent orphaned QThreads.
            if it and it.worker:
                try:
                    it.worker.progress.disconnect()
                    it.worker.status.disconnect()
                    it.worker.finished.disconnect()
                except RuntimeError:
                    pass  # already disconnected
                # Schedule thread cleanup — it has already finished running.
                it.worker.deleteLater()
        self._order = keep_order
        self.cleared.emit()
        self._emit_slots()

    def enqueue(self, req: DownloadRequest) -> str:
        item_id = uuid.uuid4().hex[:8]
        it = QueueItem(item_id=item_id, req=req)
        self._items[item_id] = it
        self._order.append(item_id)
        self.added.emit(item_id)
        self._pump()
        return item_id

    def enqueue_many(self, reqs: list) -> list:
        """Batch enqueue — single pump() after all items are added."""
        ids: list[str] = []
        for req in reqs:
            item_id = uuid.uuid4().hex[:8]
            it = QueueItem(item_id=item_id, req=req)
            self._items[item_id] = it
            self._order.append(item_id)
            self.added.emit(item_id)
            ids.append(item_id)
        self._pump()
        return ids

    # --- Internals ---
    def _pump(self) -> None:
        self._kick_pending()
        self._emit_slots()

    def _kick_pending(self) -> None:
        # Start workers until we hit concurrency cap
        for it in self._items.values():
            if it.status != "pending":
                continue
            if self.active_count() >= self._max:
                break
            self._start_item(it)

    def _start_item(self, it: QueueItem) -> None:
        worker = DownloaderWorker(it.item_id, it.req)
        it.worker = worker
        it.status = "active"
        it.started_at = time.time()

        worker.progress.connect(self._on_progress)
        worker.status.connect(self._on_status)
        worker.finished.connect(self._on_finished)

        self.started.emit(it.item_id)
        self.status_changed.emit(it.item_id, "active")
        worker.start()
        self._emit_slots()

    def _on_progress(self, tag: str, pct: float, speed: float, eta: float, dl: int, total: int) -> None:
        it = self._items.get(tag)
        if not it:
            return
        it.percent = pct
        it.speed = speed
        it.eta = eta
        it.downloaded = dl
        it.total = total
        self.progress.emit(tag, pct, speed, eta, dl, total)

    def _on_status(self, tag: str, msg: str) -> None:
        it = self._items.get(tag)
        if not it:
            return
        if msg == "PAUSED":
            it.status = "paused"
            self.status_changed.emit(tag, "paused")
        elif msg == "DOWNLOADING" and it.status == "paused":
            it.status = "active"
            self.status_changed.emit(tag, "active")
        # Other status messages are informational only

    def _on_finished(self, tag: str, ok: bool, result: str) -> None:
        it = self._items.get(tag)
        if not it:
            return
        it.finished_at = time.time()
        if ok:
            it.status = "done"
            it.result_path = result
        else:
            if "Cancel" in result:
                it.status = "cancelled"
            else:
                it.status = "error"
                it.error = result
        self.finished.emit(tag, ok, result)
        self.status_changed.emit(tag, it.status)
        # Start next pending
        self._kick_pending()
        self._emit_slots()

    def _emit_slots(self) -> None:
        self.slot_changed.emit(self.active_count(), self._max)
