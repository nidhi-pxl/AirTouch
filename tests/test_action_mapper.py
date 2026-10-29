# TODO: Person 1 tests agreed gesture-to-action mappings.

from unittest.mock import patch

from src.interaction.action_mapper import ActionMapper


def test_dry_run_does_not_scroll():
    mapper = ActionMapper(dry_run=True)

    with patch("src.interaction.action_mapper.pyautogui.press") as press:
        mapper.handle_event("SCROLL_UP")
        press.assert_not_called()


def test_scroll_down_calls_page_down():
    mapper = ActionMapper(dry_run=False)

    with patch("src.interaction.action_mapper.pyautogui.press") as press:
        mapper.handle_event("SCROLL_DOWN")
        press.assert_called_once_with("pagedown")


def test_scroll_up_calls_page_up():
    mapper = ActionMapper(dry_run=False)

    with patch("src.interaction.action_mapper.pyautogui.press") as press:
        mapper.handle_event("SCROLL_UP")
        press.assert_called_once_with("pageup")


def test_none_event_does_nothing():
    mapper = ActionMapper(dry_run=False)

    with patch("src.interaction.action_mapper.pyautogui.press") as press:
        mapper.handle_event(None)
        press.assert_not_called()



def test_right_click_calls_right_click():
    mapper = ActionMapper(dry_run=False)

    with patch("src.interaction.action_mapper.pyautogui.rightClick") as right_click:
        mapper.handle_event("RIGHT_CLICK")
        right_click.assert_called_once_with()


def test_dry_run_does_not_right_click():
    mapper = ActionMapper(dry_run=True)

    with patch("src.interaction.action_mapper.pyautogui.rightClick") as right_click:
        mapper.handle_event("RIGHT_CLICK")
        right_click.assert_not_called()