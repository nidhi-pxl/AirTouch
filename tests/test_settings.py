import json

import pytest

from src.settings import BASE_SETTINGS, UserSettings, clamp_setting


@pytest.fixture
def settings_file(tmp_path, monkeypatch):
    path = tmp_path / "AirTouch" / "settings.json"
    monkeypatch.setenv("AIRTOUCH_SETTINGS", str(path))
    return path


def test_base_settings_match_original_constants():
    assert BASE_SETTINGS["cursor_sensitivity"] == 0.75
    assert BASE_SETTINGS["dead_zone"] == 5
    assert BASE_SETTINGS["filter_frames"] == 5
    assert BASE_SETTINGS["click_bend_angle"] == 145
    assert BASE_SETTINGS["click_confirm_frames"] == 3


def test_missing_file_gives_base_settings(settings_file):
    settings = UserSettings.load()
    assert settings.use_personal is False
    assert settings.effective() == BASE_SETTINGS
    assert settings.profile_name() == "Base settings"


def test_personal_values_used_only_when_enabled(settings_file):
    settings = UserSettings()
    settings.personal["cursor_sensitivity"] = 1.4
    assert settings.effective()["cursor_sensitivity"] == 0.75

    settings.use_personal = True
    assert settings.effective()["cursor_sensitivity"] == 1.4


def test_save_and_load_round_trip(settings_file):
    settings = UserSettings(use_personal=True, calibrated_at="2026-11-21T15:40")
    settings.personal["click_bend_angle"] = 132
    settings.seen_help = True
    assert settings.save()

    loaded = UserSettings.load()
    assert loaded.use_personal is True
    assert loaded.personal["click_bend_angle"] == 132
    assert loaded.calibrated_at == "2026-11-21T15:40"
    assert loaded.seen_help is True
    assert loaded.profile_name() == "Calibrated"


def test_reset_to_base(settings_file):
    settings = UserSettings(use_personal=True, calibrated_at="2026-11-21T15:40")
    settings.personal["dead_zone"] = 12
    settings.reset_to_base()
    assert settings.use_personal is False
    assert settings.personal == BASE_SETTINGS
    assert settings.calibrated_at is None


def test_corrupt_or_out_of_range_file_is_sanitised(settings_file):
    settings_file.parent.mkdir(parents=True)
    settings_file.write_text(json.dumps({
        "use_personal": True,
        "personal": {"dead_zone": 999, "cursor_sensitivity": "fast", "unknown": 1},
    }))
    loaded = UserSettings.load()
    assert loaded.personal["dead_zone"] == 20                  # clamped
    assert loaded.personal["cursor_sensitivity"] == 0.75       # bad value ignored
    assert "unknown" not in loaded.personal

    settings_file.write_text("not json")
    assert UserSettings.load().effective() == BASE_SETTINGS


def test_clamp_setting_types():
    assert clamp_setting("filter_frames", 3.6) == 4
    assert isinstance(clamp_setting("filter_frames", 3.6), int)
    assert clamp_setting("cursor_sensitivity", 0.1) == 0.3
