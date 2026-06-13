"""Constants for the futures margin rates TUI viewer."""

from pathlib import Path


def abbreviate_title(title: str) -> str:
    """Abbreviate a column title for display.

    - Keep first word full
    - Abbreviate subsequent words to first 5 chars + '.'
    - Remove trailing word 'Margin' (case insensitive)
    - Trim whitespace
    """
    words = title.strip().split()
    if not words:
        return title
    # Remove trailing "Margin"
    if words[-1].lower() == "margin":
        words = words[:-1]
    if not words:
        return title
    result = [words[0]]
    for w in words[1:]:
        result.append(w[:5] + ".")
    return " ".join(result).strip()


# --- Column Definitions ---
# (label, alignment: "left" or "right")
COLUMNS: list[tuple[str, str]] = [
    ("Symbol Root & Description", "left"),
    ("Intraday Initial", "right"),
    ("Intraday Maintenance", "right"),
    ("Long Overnight Margin", "right"),
    ("Short Overnight Margin", "right"),
    ("Long Maintenance Margin", "right"),
    ("Short Maintenance Margin", "right"),
    ("Intraday Rate", "right"),
    ("Product Group", "left"),
    ("Currency", "left"),
]

# Column index constants for clarity
COL_IDX_PRODUCT_DESC = 0  # was 0, same
COL_IDX_INTRADAY_INITIAL = 1  # was 2
COL_IDX_INTRADAY_MAINT = 2  # was 3
COL_IDX_LONG_OVERNIGHT = 3  # was 4
COL_IDX_SHORT_OVERNIGHT = 4  # was 5
COL_IDX_LONG_MAINT = 5  # was 6
COL_IDX_SHORT_MAINT = 6  # was 7
COL_IDX_INTRADAY_RATE = 7  # was 8
COL_IDX_PRODUCT_GROUP = 8  # was 9
COL_IDX_CURRENCY = 9  # was 10

# Sort key mapping: two-char key sequence -> column index
# 's' is the prefix, second char maps to column
SORT_KEY_MAP: dict[str, int] = {
    "a": COL_IDX_PRODUCT_DESC,
    "c": COL_IDX_INTRADAY_INITIAL,
    "d": COL_IDX_INTRADAY_MAINT,
    "e": COL_IDX_LONG_OVERNIGHT,
    "f": COL_IDX_SHORT_OVERNIGHT,
    "g": COL_IDX_LONG_MAINT,
    "h": COL_IDX_SHORT_MAINT,
    "i": COL_IDX_INTRADAY_RATE,
    "j": COL_IDX_PRODUCT_GROUP,
    "k": COL_IDX_CURRENCY,
}

# All known product groups (order matters for display)
GROUPS: list[str] = [
    "Index",
    "Currencies",
    "Agriculture",
    "Energy",
    "Eurex Index",
    "Metals",
    "Interest Rate",
    "Crypto",
    "Euronext LIFFE",
    "Soft",
    "Eurex Interest Rate",
    "Meats",
    "Other",
]

# Label for rows with empty/missing product group
OTHER_GROUP_LABEL = "Other"

# Terminal width threshold: below this, use modal for groups instead of inline bar
WIDE_THRESHOLD = 160

# CSV file encoding
CSV_ENCODING = "utf-8"

# Sort prefix key
SORT_PREFIX = "s"

# Number of numeric columns (used for right-alignment)
NUMERIC_COLUMNS: set[int] = {
    COL_IDX_INTRADAY_INITIAL,
    COL_IDX_INTRADAY_MAINT,
    COL_IDX_LONG_OVERNIGHT,
    COL_IDX_SHORT_OVERNIGHT,
    COL_IDX_LONG_MAINT,
    COL_IDX_SHORT_MAINT,
    COL_IDX_INTRADAY_RATE,
}

# Default CSV path relative to project root
DEFAULT_DATA_DIR = Path("margin_data")
