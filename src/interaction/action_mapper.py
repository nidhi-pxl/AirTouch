
"""Map gesture events to desktop actions."""

import pyautogui


class ActionMapper:
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run

    def handle_event(self, event: str | None) -> None:
        """Execute the desktop action for a recognized event."""

        actions = {
            "SCROLL_UP": lambda: pyautogui.press("pageup"),
            "SCROLL_DOWN": lambda: pyautogui.press("pagedown"),
            "ZOOM_IN": lambda: pyautogui.hotkey("ctrl", "+"),
            "ZOOM_OUT": lambda: pyautogui.hotkey("ctrl", "-"),
            "RIGHT_CLICK": lambda: pyautogui.rightClick(),
        }

        if event is None:
            return

        action = actions.get(event)

        if action is None:
            print(f"Unknown gesture event: {event}")
            return

        if self.dry_run:
            print(f"[DRY RUN] Would execute: {event}")
        else:
            action()
            print(f"Executed: {event}")
