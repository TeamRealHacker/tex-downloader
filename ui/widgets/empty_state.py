"""Empty state placeholder — re-export of HeroEmpty for backwards-compat."""
from __future__ import annotations

from ui.widgets.hero_empty import HeroEmpty

__all__ = ["HeroEmpty", "EmptyState"]

# Backwards-compatible alias: previously empty_state.py exposed an EmptyState class.
EmptyState = HeroEmpty
