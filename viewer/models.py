"""Data models for the futures margin rates TUI viewer."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .constants import COL_IDX_PRODUCT_GROUP, COLUMNS, GROUPS, OTHER_GROUP_LABEL


@dataclass
class Row:
    """A single futures margin rate row (10 columns)."""

    product_description: str
    intraday_initial: str
    intraday_maintenance: str
    long_overnight_margin: str
    short_overnight_margin: str
    long_maintenance_margin: str
    short_maintenance_margin: str
    intraday_rate: str
    product_group: str
    currency: str

    def as_list(self) -> list[str]:
        """Return row values as a list matching COLUMNS order."""
        return [
            self.product_description,
            self.intraday_initial,
            self.intraday_maintenance,
            self.long_overnight_margin,
            self.short_overnight_margin,
            self.long_maintenance_margin,
            self.short_maintenance_margin,
            self.intraday_rate,
            self.product_group,
            self.currency,
        ]


@dataclass
class FilterState:
    """Substring filter state for product description."""

    text: str = ""


@dataclass
class SortState:
    """Sort state: which column, which direction."""

    column_index: int | None = None
    ascending: bool = True

    def toggle(self, column_index: int) -> None:
        """Set sort column; toggle direction if same column."""
        if self.column_index == column_index:
            self.ascending = not self.ascending
        else:
            self.column_index = column_index
            self.ascending = True


@dataclass
class GroupState:
    """Toggle state for all 13 product groups. All enabled by default."""

    enabled: dict[str, bool] = field(default_factory=lambda: {g: True for g in GROUPS})

    def toggle(self, group: str) -> None:
        """Toggle a single group."""
        if group in self.enabled:
            self.enabled[group] = not self.enabled[group]

    def all_on(self) -> None:
        """Enable all groups."""
        for g in self.enabled:
            self.enabled[g] = True

    def all_off(self) -> None:
        """Disable all groups."""
        for g in self.enabled:
            self.enabled[g] = False

    def toggle_all(self) -> None:
        """If all are on, turn all off; otherwise turn all on."""
        if all(self.enabled.values()):
            self.all_off()
        else:
            self.all_on()


@dataclass
class MarginDataModel:
    """Holds all loaded rows and provides the single source of truth for data."""

    all_rows: list[Row] = field(default_factory=list)
    file_path: Path | None = None

    def load_csv(self, path: Path) -> None:
        """Load rows from a CSV file. Raises on error."""
        self.file_path = path
        # Implementation in services.py - called via services.load_csv(model, path)

    @property
    def group_set(self) -> set[str]:
        """Return the set of distinct product groups present in the data."""
        groups: set[str] = set()
        for row in self.all_rows:
            g = row.product_group.strip() if row.product_group else ""
            groups.add(g if g else OTHER_GROUP_LABEL)
        return groups
