"""Pure service functions for data transforms on margin data."""

from __future__ import annotations

import csv
import os
import re
from pathlib import Path

from .constants import (
    COL_IDX_PRODUCT_GROUP,
    COLUMNS,
    CSV_ENCODING,
    GROUPS,
    NUMERIC_COLUMNS,
    OTHER_GROUP_LABEL,
    WIDE_THRESHOLD,
)
from .models import FilterState, GroupState, MarginDataModel, Row, SortState


def clean_description(desc: str, symbol: str) -> str:
    """Clean description and prepend symbol.

    - Remove parenthetical (...) from end of description
    - Remove trailing 'futures' (case insensitive)
    - Prepend symbol: 'SYMBOL: Description'
    """
    # Remove parenthetical at end: " (MET)" or "(MET)"
    desc = re.sub(r"\s*\([^)]*\)\s*$", "", desc).strip()
    # Remove trailing "futures" (case insensitive)
    desc = re.sub(r"\s*[Ff][Uu][Tt][Uu][Rr][Ee][Ss]\s*$", "", desc).strip()
    return f"{symbol}: {desc}"


def load_csv(model: MarginDataModel, path: Path) -> None:
    """
    Load CSV rows into model.all_rows.

    Reads the CSV file at `path`, skips the header row, and creates Row objects
    for each data row. Updates model.file_path.

    Handles:
    - Empty product_group -> store as empty string (display layer maps to "Other")
    - Missing columns -> fill with empty string
    - Encoding: CSV_ENCODING (utf-8)
    """
    model.file_path = path
    rows: list[Row] = []

    with open(path, "r", encoding=CSV_ENCODING, newline="") as f:
        reader = csv.reader(f)
        # Skip header row
        try:
            next(reader)
        except StopIteration:
            # Empty file - no rows to load
            model.all_rows = rows
            return

        for line in reader:
            # Ensure we have exactly 11 columns, filling missing with ""
            cols = line[:11]
            while len(cols) < 11:
                cols.append("")

            row = Row(
                product_description=clean_description(cols[0].strip(), cols[1].strip()),
                intraday_initial=cols[2].strip(),
                intraday_maintenance=cols[3].strip(),
                long_overnight_margin=cols[4].strip(),
                short_overnight_margin=cols[5].strip(),
                long_maintenance_margin=cols[6].strip(),
                short_maintenance_margin=cols[7].strip(),
                intraday_rate=cols[8].strip(),
                product_group=cols[9].strip(),
                currency=cols[10].strip(),
            )
            rows.append(row)

    model.all_rows = rows


def filter_rows(rows: list[Row], filter_state: FilterState) -> list[Row]:
    """
    Filter rows by substring match on product_description.

    Case-insensitive. If filter text is empty, returns all rows unchanged.
    """
    if not filter_state.text:
        return list(rows)

    filter_lower = filter_state.text.lower()
    return [row for row in rows if filter_lower in row.product_description.lower()]


def sort_rows(rows: list[Row], sort_state: SortState) -> list[Row]:
    """
    Sort rows by the current sort column and direction.

    If sort_state.column_index is None, returns rows unchanged.
    Uses natural sort: tries numeric comparison first, falls back to string.
    """
    if sort_state.column_index is None:
        return list(rows)

    col_idx = sort_state.column_index

    def sort_key(row: Row):
        """Extract sort key from row, trying numeric comparison first."""
        value = row.as_list()[col_idx]

        if col_idx in NUMERIC_COLUMNS:
            try:
                return (0, float(value), "")
            except (ValueError, TypeError):
                # Fall through to string comparison
                pass

        # String comparison (case-insensitive)
        return (1, 0, value.lower())

    sorted_rows = sorted(rows, key=sort_key, reverse=not sort_state.ascending)
    return sorted_rows


def group_rows(rows: list[Row], group_state: GroupState) -> list[Row]:
    """
    Filter rows to only include those whose product_group is enabled in GroupState.

    Rows with empty product_group are mapped to OTHER_GROUP_LABEL for filtering.
    """
    return [
        row
        for row in rows
        if group_state.enabled.get(
            row.product_group.strip() if row.product_group else OTHER_GROUP_LABEL,
            True,
        )
    ]


def get_layout_mode(terminal_width: int | None) -> str:
    """
    Determine whether to use 'wide' (inline bar) or 'narrow' (modal) layout.

    Returns 'wide' if terminal_width >= WIDE_THRESHOLD, else 'narrow'.
    If terminal_width is None, defaults to 'narrow'.
    """
    if terminal_width is not None and terminal_width >= WIDE_THRESHOLD:
        return "wide"
    return "narrow"


def format_cell_value(value: str, column_index: int) -> str:
    """
    Format a cell value for display.

    For numeric columns: strip trailing zeros and decimal point if whole number.
    For empty product_group: return OTHER_GROUP_LABEL.
    Otherwise: return value as-is.
    """
    # Handle empty product_group
    if column_index == COL_IDX_PRODUCT_GROUP and not value:
        return OTHER_GROUP_LABEL

    # Handle numeric columns
    if column_index in NUMERIC_COLUMNS:
        try:
            num = float(value)
            # Format to remove trailing zeros
            if num == int(num):
                return str(int(num))
            else:
                # Strip trailing zeros after decimal point
                formatted = f"{num:f}"
                formatted = formatted.rstrip("0").rstrip(".")
                return formatted
        except (ValueError, TypeError):
            pass

    return value
