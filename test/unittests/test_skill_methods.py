import os
from unittest.mock import patch

from ovos_skill_screenshot import ScreenshotSkill


def _make_skill():
    """Build a ScreenshotSkill without booting the full OVOSSkill stack."""
    skill = ScreenshotSkill.__new__(ScreenshotSkill)
    skill._settings = {}
    return skill


def test_default_screenshots_folder(tmp_path):
    skill = _make_skill()
    with patch.dict(os.environ, {"HOME": str(tmp_path)}):
        folder = skill.screenshots_folder
    assert folder == os.path.join(str(tmp_path), "Pictures", "Screenshots")
    assert os.path.isdir(folder)


def test_custom_screenshots_folder(tmp_path):
    skill = _make_skill()
    target = tmp_path / "shots"
    skill._settings = {"screenshots_path": str(target)}
    assert skill.screenshots_folder == str(target)
    assert os.path.isdir(target)


def test_is_ovos_shell_true():
    skill = _make_skill()
    cfg = {"gui": {"extension": "ovos-gui-plugin-shell-companion"}}
    with patch("ovos_skill_screenshot.Configuration", return_value=cfg):
        assert skill.is_ovos_shell is True


def test_is_ovos_shell_false():
    skill = _make_skill()
    with patch("ovos_skill_screenshot.Configuration", return_value={}):
        assert skill.is_ovos_shell is False
