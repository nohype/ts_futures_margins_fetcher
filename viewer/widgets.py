"""Textual widgets for the futures margin rates TUI viewer."""

from __future__ import annotations

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, Checkbox, DataTable, Input, Static

from .constants import COLUMNS, GROUPS, SORT_KEY_MAP, abbreviate_title
from .models import GroupState, Row, SortState
from .services import format_cell_value

# Reverse mapping: column_index (0..10) -> sort key letter ("a".."k")
_SORT_KEY_LETTER: dict[int, str] = {v: k for k, v in SORT_KEY_MAP.items()}


def _sanitize_id(group: str) -> str:
    """Convert a group name to a valid Textual widget ID."""
    return group.replace(" ", "_")


class FilterInput(Horizontal):
    """Filter bar: label + input field for live substring filtering."""

    can_focus = False

    class Changed(Message):
        """Emitted when the filter text changes."""

        def __init__(self, text: str) -> None:
            self.text = text
            super().__init__()

    class Submitted(Message):
        """Emitted when the user presses Enter or Escape in the filter input."""

    def compose(self):
        yield Static("Filter:")
        yield Input(placeholder="type to filter...")

    def on_input_changed(self, event: Input.Changed) -> None:
        self.post_message(self.Changed(event.value))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        self.post_message(self.Submitted())

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            self.post_message(self.Submitted())
            event.stop()


class MarginTableWidget(DataTable):
    """Scrollable data table for futures margin rates."""

    class HeaderClicked(Message):
        """Emitted when the user clicks a column header to sort."""

        def __init__(self, column_index: int) -> None:
            self.column_index = column_index
            super().__init__()

    def __init__(self) -> None:
        super().__init__(zebra_stripes=True, cursor_type="row")
        for i, (label, _) in enumerate(COLUMNS):
            short_label = abbreviate_title(label)
            if i == 0:
                self.add_column(short_label, key=label, width=30)
            else:
                self.add_column(short_label, key=label)

    def render_table(self, rows: list[Row], sort_state: SortState) -> None:
        """Clear and re-render the table with sorted, formatted rows.

        Args:
            rows: The list of Row objects to display (already sorted/filtered).
            sort_state: Current sort state used to decorate column headers.
        """
        self.clear()

        for i, row in enumerate(rows):
            formatted = [
                format_cell_value(row.as_list()[j], j) for j in range(len(COLUMNS))
            ]
            self.add_row(*formatted, key=str(i))

        # Update column header labels with sort hints
        for col_idx, (label, _) in enumerate(COLUMNS):
            key_letter = _SORT_KEY_LETTER.get(col_idx, "?")
            short_label = abbreviate_title(label)
            col = self.columns[label]

            if sort_state.column_index == col_idx:
                arrow = "\u25b2" if sort_state.ascending else "\u25bc"  # ▲ or ▼
                col.label = f"{short_label} {arrow} [s{key_letter}]"
            else:
                col.label = f"{short_label} [s{key_letter}]"

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        event.stop()
        self.post_message(self.HeaderClicked(event.column_index))


class GroupToggleBar(Widget):
    """Checkbox bar that wraps into multiple rows dynamically."""

    class Toggled(Message):
        """A group was toggled."""

    def __init__(self, group_state: GroupState) -> None:
        super().__init__()
        self.group_state = group_state
        self._columns: int = 7  # default

    def compose(self) -> ComposeResult:
        yield Static("Groups:", id="groups_label")
        for group in GROUPS:
            checked = self.group_state.enabled[group]
            yield Checkbox(group, value=checked, id=f"cb_{_sanitize_id(group)}")

    def on_mount(self) -> None:
        self._update_grid()

    def on_resize(self, event: events.Resize) -> None:
        self._update_grid(event.size.width)

    def _update_grid(self, width: int | None = None) -> None:
        """Recalculate grid columns based on available width."""
        if width is None:
            width = self.size.width
        if width <= 0:
            return

        # Longest group name + checkbox box (~4 cells)
        max_label = max(len(g) for g in GROUPS)
        col_w = max_label + 4
        available = width - 4  # padding
        cols = max(2, min(available // col_w, len(GROUPS)))

        if cols != self._columns:
            self._columns = cols
            items = 1 + len(GROUPS)  # label + 13 checkboxes
            rows = (items + cols - 1) // cols
            self.styles.grid_size_rows = rows
            self.styles.grid_size_columns = cols

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        checkbox = event.checkbox
        group = str(checkbox.label)
        if group in self.group_state.enabled:
            self.group_state.enabled[group] = event.value
        self.post_message(self.Toggled())

    def sync_from_state(self) -> None:
        for group in GROUPS:
            cb = self.query_one(f"#cb_{_sanitize_id(group)}", Checkbox)
            cb.value = self.group_state.enabled[group]


class GroupToggleModal(ModalScreen[None]):
    """Modal overlay for group toggles on narrow terminals."""

    BINDINGS = [
        Binding("space", "toggle_focused", "Toggle"),
        Binding("ctrl+a", "toggle_all", "All on/off"),
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
    ]

    def __init__(self, group_state: GroupState) -> None:
        super().__init__()
        self.group_state = group_state

    def compose(self) -> ComposeResult:
        with Vertical(id="group_modal_container"):
            yield Static("Product Groups", id="modal_title")
            yield Static("Space=toggle  Ctrl+A=toggle all  Esc=close", id="modal_help")
            for group in GROUPS:
                checked = self.group_state.enabled[group]
                yield Checkbox(
                    group, value=checked, id=f"modal_cb_{_sanitize_id(group)}"
                )
            with Horizontal(id="modal_buttons"):
                yield Button("Close", variant="primary", id="modal_close")

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Update group state when a checkbox is toggled."""
        checkbox = event.checkbox
        group = str(checkbox.label)
        if group in self.group_state.enabled:
            self.group_state.enabled[group] = event.value

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "modal_close":
            self.dismiss()

    def action_toggle_focused(self) -> None:
        """Toggle the currently focused checkbox."""
        focused = self.focused
        if isinstance(focused, Checkbox):
            focused.toggle()

    def action_toggle_all(self) -> None:
        """Toggle all groups on/off."""
        self.group_state.toggle_all()
        self._sync_checkboxes()

    def _sync_checkboxes(self) -> None:
        """Update all checkboxes to match the current GroupState."""
        for group in GROUPS:
            cb = self.query_one(f"#modal_cb_{_sanitize_id(group)}", Checkbox)
            cb.value = self.group_state.enabled[group]


class HelpModal(ModalScreen[None]):
    """Help modal showing key bindings."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
        Binding("question_mark", "dismiss", "Close"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="help_modal_container"):
            yield Static("Key Bindings", id="help_title")
            yield Static("─" * 40, id="help_sep")

            yield Static("Navigation", classes="help_section")
            yield Static("  ↑↓ / j k          Move cursor", classes="help_row")
            yield Static("  Page Up / Down     Page scroll", classes="help_row")
            yield Static("  Home / End         Jump top/bottom", classes="help_row")

            yield Static("Filtering", classes="help_section")
            yield Static("  /                  Focus filter", classes="help_row")
            yield Static("  Ctrl+U             Clear filter", classes="help_row")
            yield Static(
                "  Type in filter     Live substring match on Product Description",
                classes="help_row",
            )
            yield Static("  Enter / Escape     Return to table", classes="help_row")

            yield Static("Sorting", classes="help_section")
            yield Static(
                "  s + a..k           Sort by column (a=Description, c=Intraday Init, ...)",
                classes="help_row",
            )
            yield Static(
                "  Click header       Sort by that column (toggle direction)",
                classes="help_row",
            )

            yield Static("Groups", classes="help_section")
            yield Static(
                "  g                  Focus group bar (wide) / Open group modal (narrow)",
                classes="help_row",
            )
            yield Static(
                "  Space              Toggle focused group", classes="help_row"
            )
            yield Static(
                "  Ctrl+A             Toggle all groups on/off", classes="help_row"
            )

            yield Static("General", classes="help_section")
            yield Static("  q                  Quit", classes="help_row")
            yield Static("  ?                  This help", classes="help_row")

            with Horizontal(id="help_buttons"):
                yield Button("Close", variant="primary", id="help_close")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "help_close":
            self.dismiss()
