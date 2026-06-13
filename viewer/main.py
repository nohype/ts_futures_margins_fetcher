"""Entry point for the futures margin rates TUI viewer."""

import argparse
import sys
from pathlib import Path

from .app import MarginViewerApp
from .constants import DEFAULT_DATA_DIR


def find_latest_csv(data_dir: Path) -> Path | None:
    """Find the most recent CSV file in the data directory."""
    if not data_dir.exists():
        return None
    csv_files = sorted(data_dir.glob("futures_margin_rates_*.csv"), reverse=True)
    return csv_files[0] if csv_files else None


def run_viewer(csv_path: Path) -> None:
    """Run the TUI viewer with an explicit CSV path (no arg parsing)."""
    app = MarginViewerApp(csv_path)
    app.run()


def main() -> None:
    """Parse args and run the TUI viewer."""
    parser = argparse.ArgumentParser(
        description="Interactive TUI viewer for TradeStation futures margin rates."
    )
    parser.add_argument(
        "csv_path",
        nargs="?",
        type=Path,
        help="Path to the CSV file. If not provided, uses the latest file in margin_data/.",
    )
    args = parser.parse_args()

    csv_path: Path | None = args.csv_path

    if csv_path is None:
        csv_path = find_latest_csv(DEFAULT_DATA_DIR)
        if csv_path is None:
            print(
                "Error: No CSV file found. Run scrape_margins.py first or specify a path.",
                file=sys.stderr,
            )
            sys.exit(1)

    if not csv_path.exists():
        print(f"Error: File not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    app = MarginViewerApp(csv_path)
    app.run()


if __name__ == "__main__":
    main()
