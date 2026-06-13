# Handoff: Futures Margin Rates TUI Viewer

## Mission for the Next Session

**Implement** the TUI viewer feature planned in this conversation. The planning phase is complete; the next session should begin coding.

---

## What Exists Now

### Working Scraper
`D:\ts_futures_margin_crawler\scrape_margins.py` — Fully functional. Fetches 190 futures margin rate rows from TradeStation and writes CSV. Uses `scrapling.Fetcher` (static HTTP, no browser needed). Extracts data from Next.js RSC payload in `<script>` tags, which includes a hidden "Product Group" column (11 columns total). Falls back to HTML table parsing. Uses `pathlib.Path` throughout. Output goes to `margin_data/` with timestamped filenames.

### Sample Data
`D:\ts_futures_margin_crawler\margin_data\futures_margin_rates_2026-06-13_1529.csv` — 190 rows, 11 columns. Use this for development/testing.

### Virtual Environment
`D:\ts_futures_margin_crawler\.venv\` — Python 3.11. Installed: `scrapling`, `curl_cffi`, `playwright` (used by scrapling internally), `browserforge`, `lxml`, `orjson`, etc. **All work must use this venv.**

---

## What to Build

An interactive TUI viewer for the CSV data, using the **Textual** framework.

### Core Features
1. **Scrollable data table** — 190 rows, 11 columns, cursor navigation
2. **Group toggles** — Enable/disable 13 Product Groups to filter rows
3. **Substring filter** — Live "as you type" filter on Product Description
4. **Column sorting** — Sort by any column, ascending/descending toggle

### Key Design Decisions (Already Made)

| Decision | Choice | Rationale |
|---|---|---|
| TUI library | **Textual** | Built-in DataTable, Input, Checkbox, reactive state, mouse, 120fps |
| Sort interaction | **`s` prefix** then `a-k` | Avoids conflict with `j/k` nav and `g` groups. Headers show hints like `[sa]`, `[sb]` |
| Filter activation | **`/`** key | Standard search convention (vim/less) |
| Group toggles (wide) | **Inline checkbox bar** | All 13 groups visible above table on terminals ≥160 cols |
| Group toggles (narrow) | **Modal overlay** | Press `g` to open modal on terminals <160 cols |
| Layout threshold | **160 columns** | Below this, inline bar too cramped; switch to modal |
| Empty Product Group | **Labeled "Other"** | 3 rows have no group; "Other" makes them toggleable |

### Sort Key Mapping

| Key | Column |
|---|---|
| `sa` | Product Description |
| `sb` | Symbol Root |
| `sc` | Intraday Initial |
| `sd` | Intraday Maintenance |
| `se` | Long Overnight Margin |
| `sf` | Short Overnight Margin |
| `sg` | Long Maintenance Margin |
| `sh` | Short Maintenance Margin |
| `si` | Intraday Rate |
| `sj` | Product Group |
| `sk` | Currency |

### Key Bindings Summary

| Context | Key | Action |
|---|---|---|
| Any | `q` | Quit |
| Any | `?` | Help modal |
| Any | `/` | Focus filter input |
| Any | `ctrl+u` | Clear filter |
| Any | `g` | Groups (modal narrow / focus bar wide) |
| Table | `↑↓` or `jk` | Cursor move |
| Table | `Page Up/Down` | Page scroll |
| Table | `Home/End` | Jump top/bottom |
| Table | `s` + `a-k` | Sort by column (toggle direction on repeat) |
| Table | Click header | Sort by that column |
| Filter | type | Live filter |
| Filter | `Enter`/`Escape` | Return to table |
| Groups | `Space` | Toggle group |
| Groups | `ctrl+a` | Toggle all on/off |

---

## Architecture (MECE / DRY / SLAP / GRASP)

### File Structure

```
viewer/
├── __init__.py
├── main.py              # Entry point, CLI arg parsing, Path handling
├── app.py               # MarginViewerApp, MainScreen — lifecycle, state, key routing
├── models.py            # Row, MarginDataModel, FilterState, SortState, GroupState
├── services.py          # Pure functions: filter_rows, sort_rows, group_rows, get_layout_mode
├── widgets.py           # MarginTableWidget, FilterInput, GroupToggleBar, GroupToggleModal, HelpModal
├── constants.py         # COLUMNS, SORT_KEY_MAP, GROUPS, WIDE_THRESHOLD
└── styles.tcss          # Textual CSS
```

### Responsibility Boundaries

| Module | Owns | Does NOT own |
|---|---|---|
| `models.py` | Data shapes and state | UI rendering, business logic |
| `services.py` | Pure transform functions on data | State management, UI |
| `widgets.py` | Visual rendering and user interaction | Data transforms, state ownership |
| `app.py` | Orchestration, state wiring, key routing | Low-level data ops, widget internals |
| `constants.py` | Configuration values | Logic, state |

### Data Flow

```
CSV → csv_loader → List[Row] → MarginDataModel.all_rows
                                         │
         GroupState ──→ group_rows() ──→ filtered
         FilterState ──→ filter_rows() ──→ further filtered
         SortState ──→ sort_rows() ──→ sorted
                                         │
                                         ▼
                              MarginTableWidget.render_table()
                                         │
                                         ▼
                                   DataTable (displayed)
```

App's reactive `watch_*` methods trigger `render_table()` on any state change.

### DRY: Shared Group State
`GroupState` is the single source of truth. Both `GroupToggleBar` (wide) and `GroupToggleModal` (narrow) read/write the same `GroupState` instance on the app. No duplicated toggle logic.

### SLAP: Render Pipeline
`render_table()` calls `group_rows()` → `filter_rows()` → `sort_rows()` → `format_cells()` → `DataTable.add_row()`. Each step is one abstraction level.

---

## Data Shape Reference

- **190 rows**, **11 columns**
- **13 Product Groups**: Index(44), Currencies(20), Agriculture(19), Energy(19), Eurex Index(21), Metals(17), Interest Rate(17), Crypto(10), Euronext LIFFE(10), Soft(9), Eurex Interest Rate(8), Meats(3), Other(3)
- **5 Currencies**: USD, EUR, GBP, JPY, CHF
- **7 numeric columns** (right-align): Intraday Initial, Intraday Maintenance, Long/Short Overnight Margin, Long/Short Maintenance Margin, Intraday Rate
- **4 string columns** (left-align): Product Description, Symbol Root, Product Group, Currency
- **Special chars**: `®` (EURO STOXX®), `†` (Ultra 10-Year), `"C"` (Coffee "C")
- **Min terminal width for all cols**: ~178 chars

---

## Implementation Order

1. **`constants.py` + `models.py`** — Column defs, Row dataclass, MarginDataModel, state classes
2. **`services.py`** — Pure functions for filter/sort/group/layout
3. **`widgets.py`** (table + filter only) — MarginTableWidget renders data, FilterInput live-filters
4. **`widgets.py`** (groups) + `app.py`** — GroupToggleBar, GroupToggleModal, state wiring
5. **Sort + key bindings** — `s`+letter sort, click-header sort, navigation keys, help modal
6. **Responsive layout + polish** — Width detection, bar/modal switching, special chars, number formatting, edge cases

Each phase is independently testable.

---

## Constraints

- **Only run Python in `.venv/`** — install `textual` there (`pip install textual`)
- **Use `pathlib.Path`** everywhere, no raw string paths or `os.path`
- **Follow DRY, SLAP, GRASP, MECE** strictly
- **Use Double Diamond + CoT** to find answers and solutions
- **No changes to `scrape_margins.py`**

---

## Suggested Skills for Next Session

- **review-loop** — After each implementation phase, use this to validate the code against the architecture spec above
- **write-a-skill** — If the TUI viewer pattern proves reusable, capture it as a skill for future projects