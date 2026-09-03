import os
from unittest.mock import MagicMock, patch

from ovos_bus_client.message import Message

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


def test_delayed_screenshot_schedules_instead_of_capturing_immediately():
    """A delay entity must defer the capture via schedule_event rather than
    calling the capture path on the handler thread."""
    skill = _make_skill()
    skill.speak_dialog = MagicMock()
    skill.schedule_event = MagicMock()
    skill._take_screenshot_impl = MagicMock()

    message = Message("recognizer_loop:utterance",
                      {"delay": "5"}, {"session": {"session_id": "x"}})
    with patch.object(type(skill), "lang", "en-us"):
        skill.handle_screenshot_intent(message)

    skill._take_screenshot_impl.assert_not_called()
    skill.schedule_event.assert_called_once()
    args, kwargs = skill.schedule_event.call_args
    assert args[0] == skill._take_screenshot_impl
    assert args[1] == 5
    skill.speak_dialog.assert_called_once_with(
        "screenshot.delayed", {"delay": 5})


def test_no_delay_captures_immediately():
    skill = _make_skill()
    skill.speak_dialog = MagicMock()
    skill.schedule_event = MagicMock()
    skill._take_screenshot_impl = MagicMock()

    message = Message("recognizer_loop:utterance", {}, {})
    skill.handle_screenshot_intent(message)

    skill.schedule_event.assert_not_called()
    skill._take_screenshot_impl.assert_called_once_with(message)


def test_unparsable_delay_falls_back_to_immediate_capture():
    skill = _make_skill()
    skill.speak_dialog = MagicMock()
    skill.schedule_event = MagicMock()
    skill._take_screenshot_impl = MagicMock()

    message = Message("recognizer_loop:utterance",
                      {"delay": "gibberish"}, {})
    with patch.object(type(skill), "lang", "en-us"):
        skill.handle_screenshot_intent(message)

    skill.schedule_event.assert_not_called()
    skill._take_screenshot_impl.assert_called_once_with(message)


def test_screenshot_location_intent_speaks_configured_path(tmp_path):
    skill = _make_skill()
    target = tmp_path / "shots"
    skill._settings = {"screenshots_path": str(target)}
    skill.speak_dialog = MagicMock()

    skill.handle_screenshot_location_intent(Message("x", {}, {}))

    skill.speak_dialog.assert_called_once_with(
        "screenshot.location", {"path": str(target)})


def _locale_path(name):
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "locale", "en-US", name)


def test_intent_routing_probe_table():
    """Bare 'screenshot' must route to take_screenshot, must not collide
    with camera-style phrasing ('take a picture'), the delay template must
    extract the numeric entity, and the location query must stay on its
    own intent."""
    from padacioso import IntentContainer

    container = IntentContainer()
    container.add_intent(
        "take_screenshot",
        open(_locale_path("take_screenshot.intent")).read().splitlines())
    container.add_intent(
        "screenshot_location",
        open(_locale_path("screenshot_location.intent")).read().splitlines())

    cases = [
        ("screenshot", "take_screenshot", {}),
        ("take a screenshot in 5 seconds", "take_screenshot", {"delay": "5"}),
        ("where are my screenshots saved", "screenshot_location", {}),
        ("where do screenshots go", "screenshot_location", {}),
        ("take a picture", None, {}),  # camera phrasing must not collide
        ("record a voice memo", None, {}),
    ]
    for utterance, expected_name, expected_entities in cases:
        result = container.calc_intent(utterance)
        assert result["name"] == expected_name, (utterance, result)
        for key, value in expected_entities.items():
            assert result["entities"].get(key) == value, (utterance, result)
