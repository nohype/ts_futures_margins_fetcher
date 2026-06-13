"""
TradeStation Futures Margin Rates Scraper

Fetches all futures margin rates from TradeStation's website and writes them to a CSV file.
Uses the scrapling library for HTTP fetching and HTML parsing.

Data source: https://www.tradestation.com/pricing/futures-margin-requirements/

The script extracts data from the Next.js RSC payload embedded in the page,
which includes a hidden "Product Group" column not shown in the rendered table.
Falls back to parsing the HTML table if the RSC payload cannot be parsed.
"""

import argparse
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from scrapling.fetchers import Fetcher

URL = "https://www.tradestation.com/pricing/futures-margin-requirements/"
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT = (
    SCRIPT_DIR
    / "margin_data"
    / f"futures_margin_rates_{datetime.now().strftime('%Y-%m-%d_%H%M')}.csv"
)

# Full column set from the RSC payload (includes hidden Product Group)
RSC_HEADERS = [
    "Product Description",
    "Symbol Root",
    "Intraday Initial",
    "Intraday Maintenance",
    "Long Overnight Margin",
    "Short Overnight Margin",
    "Long Maintenance Margin",
    "Short Maintenance Margin",
    "Intraday Rate",
    "Product Group",
    "Currency",
]

# Columns visible in the rendered HTML table (no Product Group)
HTML_HEADERS = [
    "Product Description",
    "Symbol Root",
    "Intraday Initial",
    "Intraday Maintenance",
    "Long Overnight Margin",
    "Short Overnight Margin",
    "Long Maintenance Margin",
    "Short Maintenance Margin",
    "Intraday Rate",
    "Currency",
]


def extract_from_rsc(page) -> list[list[str]] | None:
    """Extract margin data from the Next.js RSC payload in script tags.

    The page embeds row data in a self.__next_f.push([1,"..."]) script tag.
    The inner string is an RSC payload containing a "rows" key with the full
    data array (including the hidden Product Group column).

    Returns list of rows (header + data) or None on failure.
    """
    scripts = page.css("script")
    for script in scripts:
        text = script.text
        if "Intraday" not in text or len(text) < 10000:
            continue

        # Locate the self.__next_f.push([1,"..."]) call
        push_match = re.search(r"self\.__next_f\.push\(\[1,", text)
        if not push_match:
            continue

        # Extract the JSON array argument: [1, "..."]
        push_start = text.index("self.__next_f.push(") + len("self.__next_f.push(")
        end_match = re.search(r'"\]\)\s*$', text)
        if not end_match:
            continue

        json_str = text[push_start : end_match.end() - 1]  # exclude trailing )

        try:
            push_arg = json.loads(json_str)
        except json.JSONDecodeError:
            continue

        if not isinstance(push_arg, list) or len(push_arg) < 2:
            continue

        rsc_string = push_arg[1]
        rows_idx = rsc_string.find('rows":[')
        if rows_idx < 0:
            continue

        # Extract the JSON array after "rows":
        start = rows_idx + len('rows":')
        depth = 0
        end = start
        for i in range(start, len(rsc_string)):
            if rsc_string[i] == "[":
                depth += 1
            elif rsc_string[i] == "]":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break

        rows_json = rsc_string[start:end]
        try:
            data = json.loads(rows_json)
        except json.JSONDecodeError:
            continue

        if not data or len(data[0]) != len(RSC_HEADERS):
            continue

        # Replace the generic header row with our canonical headers
        data[0] = RSC_HEADERS
        return data

    return None


def extract_from_html_table(page) -> list[list[str]] | None:
    """Extract margin data from the rendered HTML table.

    Fallback method that parses the visible <table> element.
    Does not include the Product Group column.

    Returns list of rows (header + data) or None on failure.
    """
    tables = page.css("table")
    if not tables:
        return None

    table = tables[0]
    header_cells = table.css("thead th")
    if not header_cells:
        return None

    headers = [th.text for th in header_cells]
    rows = [headers]

    for tr in table.css("tbody tr"):
        cells = [td.text for td in tr.css("td")]
        if cells:
            rows.append(cells)

    return rows if len(rows) > 1 else None


def scrape_margin_rates() -> list[list[str]]:
    """Fetch the TradeStation futures margin page and extract all margin rates.

    Returns a list of rows where the first row is the header.
    """
    print(f"Fetching {URL} ...")
    page = Fetcher.get(URL)

    if page.status != 200:
        print(f"Error: HTTP {page.status}", file=sys.stderr)
        sys.exit(1)

    # Try RSC payload first (includes Product Group column)
    data = extract_from_rsc(page)
    if data:
        print(
            f"Extracted {len(data) - 1} rows from RSC payload ({len(data[0])} columns)"
        )
        return data

    # Fallback to HTML table
    data = extract_from_html_table(page)
    if data:
        print(
            f"Extracted {len(data) - 1} rows from HTML table ({len(data[0])} columns)"
        )
        return data

    print("Error: could not extract margin data from the page", file=sys.stderr)
    sys.exit(1)


def write_csv(data: list[list[str]], output_path: Path) -> None:
    """Write the extracted data to a CSV file."""
    headers = data[0]
    rows = data[1:]

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Scrape TradeStation futures margin rates and optionally open the TUI viewer."
    )
    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        help="Output CSV file path. Defaults to margin_data/futures_margin_rates_<timestamp>.csv",
    )
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="After scraping, open the TUI viewer with the scraped data.",
    )
    args = parser.parse_args()

    output_path = args.output.resolve() if args.output else DEFAULT_OUTPUT

    data = scrape_margin_rates()
    write_csv(data, output_path)

    if args.interactive:
        print("Launching interactive viewer...")
        from viewer.main import run_viewer

        run_viewer(output_path)


if __name__ == "__main__":
    main()
