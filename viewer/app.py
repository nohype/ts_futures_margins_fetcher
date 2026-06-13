"""MarginViewerApp and MainScreen — lifecycle, state, key routing."""

from pathlib import Path

from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Input

from .constants import (
    COLUMNS,
    DEFAULT_DATA_DIR,
    GROUPS,
    SORT_KEY_MAP,
    SORT_PREFIX,
    WIDE_THRESHOLD,
)
from .models import (
    FilterState,
    GroupState,
    MarginDataModel,
    Row,
    SortState,
)
from .services import (
    filter_rows,
    format_cell_value,
    get_layout_mode,
    group_rows,
    load_csv,
    sort_rows,
)
from .widgets import (
    FilterInput,
    GroupToggleBar,
    GroupToggleModal,
    HelpModal,
    MarginTableWidget,
)


class MainScreen(Screen):
    """Main screen: header, filter, group bar (wide), table, footer."""

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("question_mark", "show_help", "Help"),
        Binding("slash", "focus_filter", "Filter"),
        Binding("ctrl+u", "clear_filter", "Clear filter"),
        Binding("g", "toggle_groups", "Groups"),
    ]

    def __init__(self, data_model: MarginDataModel) -> None:
        super().__init__()
        self.data_model = data_model
        self.filter_state = FilterState()
        self.sort_state = SortState()
        self.group_state = GroupState()
        self._sort_prefix_active = (
            False  # True after 's' pressed, waiting for second key
        )
        self._layout_mode: str = "wide"  # "wide" or "narrow"

    def compose(self) -> ComposeResult:
        """Build the screen layout."""
        yield Header()
        yield FilterInput()
        yield GroupToggleBar(self.group_state)
        yield MarginTableWidget()
        yield Footer()

    def on_mount(self) -> None:
        """After mount, render the initial table."""
        self._render_table()

    # --- Event Handlers ---

    def on_filter_input_changed(self, event: FilterInput.Changed) -> None:
        """Live filter: update filter state and re-render."""
        self.filter_state.text = event.text
        self._render_table()

    def on_filter_input_submitted(self, event: FilterInput.Submitted) -> None:
        """Return focus to table on Enter/Escape in filter."""
        self.query_one(MarginTableWidget).focus()

    def on_margin_table_widget_header_clicked(
        self, event: MarginTableWidget.HeaderClicked
    ) -> None:
        """Sort by clicked column header."""
        self.sort_state.toggle(event.column_index)
        self._render_table()

    def on_resize(self, event: events.Resize) -> None:
        """Detect terminal width and switch between wide/narrow group layout."""
        try:
            group_bar = self.query_one(GroupToggleBar)
        except Exception:
            return
        new_mode = get_layout_mode(event.size.width)
        if new_mode != self._layout_mode:
            self._layout_mode = new_mode
            if new_mode == "wide":
                group_bar.display = True
            else:
                group_bar.display = False

    def on_group_toggle_bar_toggled(self, event: GroupToggleBar.Toggled) -> None:
        """Re-render when a group is toggled."""
        self._render_table()

    # --- Key Handling ---

    def key_s(self) -> None:
        """Activate sort prefix mode."""
        self._sort_prefix_active = True

    def on_key(self, event: events.Key) -> None:
        """Handle sort key combo (s + letter) and navigation keys."""
        # If sort prefix is active and a letter key is pressed
        if self._sort_prefix_active and event.key and len(event.key) == 1:
            letter = event.key.lower()
            if letter == "s":
                # "s" itself was handled by key_s(), don't consume it here
                event.prevent_default()
                return
            if letter in SORT_KEY_MAP:
                self.sort_state.toggle(SORT_KEY_MAP[letter])
                self._render_table()
            self._sort_prefix_active = False
            event.prevent_default()
            return

        # Reset sort prefix on any other key
        self._sort_prefix_active = False

        # Navigation keys for table
        table = self.query_one(MarginTableWidget)
        if event.key == "j":
            table.action_cursor_down()
            event.prevent_default()
        elif event.key == "k":
            table.action_cursor_up()
            event.prevent_default()
        elif event.key == "home":
            table.action_scroll_home()
            event.prevent_default()
        elif event.key == "end":
            table.action_scroll_end()
            event.prevent_default()
        elif event.key == "pageup":
            table.action_page_up()
            event.prevent_default()
        elif event.key == "pagedown":
            table.action_page_down()
            event.prevent_default()

    # --- Actions ---

    def action_quit(self) -> None:
        self.app.exit()

    def action_show_help(self) -> None:
        """Show help modal."""
        self.app.push_screen(HelpModal())

    def action_focus_filter(self) -> None:
        """Focus the filter input."""
        filter_widget = self.query_one(FilterInput)
        filter_widget.query_one(Input).focus()

    def action_clear_filter(self) -> None:
        """Clear the filter text."""
        self.filter_state.text = ""
        filter_widget = self.query_one(FilterInput)
        inp = filter_widget.query_one(Input)
        inp.value = ""
        self._render_table()

    def action_toggle_groups(self) -> None:
        """Open group modal (narrow) or focus group bar (wide)."""
        if self._layout_mode == "wide":
            # Focus the first checkbox in the group bar
            group_bar = self.query_one(GroupToggleBar)
            try:
                first_cb = group_bar.query("Checkbox").first()
                first_cb.focus()
            except Exception:
                pass
        else:
            # Push the group modal
            self.app.push_screen(
                GroupToggleModal(self.group_state), self._on_group_modal_dismissed
            )

    def _on_group_modal_dismissed(self, _result=None) -> None:
        """After modal dismiss, re-render the table."""
        self._render_table()
        # Sync the group bar checkboxes with the updated state
        group_bar = self.query_one(GroupToggleBar)
        group_bar.sync_from_state()

    # --- Render Pipeline ---

    def _render_table(self) -> None:
        """
        Full render pipeline: group -> filter -> sort -> display.
        Called after any state change.
        """
        rows = self.data_model.all_rows

        # Step 1: Group filter
        rows = group_rows(rows, self.group_state)

        # Step 2: Substring filter
        rows = filter_rows(rows, self.filter_state)

        # Step 3: Sort
        rows = sort_rows(rows, self.sort_state)

        # Step 4: Display
        table = self.query_one(MarginTableWidget)
        table.render_table(rows, self.sort_state)


class MarginViewerApp(App):
    """Main Textual application for the futures margin viewer."""

    CSS_PATH = "styles.tcss"  # Will be created in Step 4

    BINDINGS = [
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, csv_path: Path) -> None:
        super().__init__()
        self.csv_path = csv_path
        self.data_model = MarginDataModel()

    def on_mount(self) -> None:
        """Load CSV data and push the main screen."""
        load_csv(self.data_model, self.csv_path)
        self.push_screen(MainScreen(self.data_model))
