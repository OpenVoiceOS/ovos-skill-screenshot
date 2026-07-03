"""End-to-end intent routing tests for the en-US locale.

Each canonical utterance is fired through a real MiniCroft and asserted to
route to the take-screenshot Padatious intent. The capture ends at the intent
match, so the assertion covers routing without depending on the screenshot
side effect (which needs a display).
"""
import unittest

from ovos_bus_client.message import Message
from ovos_bus_client.session import Session
from ovoscope import CaptureSession, get_minicroft

SKILL_ID = "ovos-skill-screenshot.openvoiceos"
LANG = "en-US"


class TestScreenshotIntentsEnUS(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.minicroft = get_minicroft([SKILL_ID])

    @classmethod
    def tearDownClass(cls):
        cls.minicroft.stop()

    def _assert_intent(self, text, intent_file):
        intent_msg = f"{SKILL_ID}:{intent_file}"
        session = Session("test-session")
        session.lang = LANG
        session.pipeline = [
            "ovos-padatious-pipeline-plugin-high",
            "ovos-padatious-pipeline-plugin-medium",
        ]
        utterance = Message(
            "recognizer_loop:utterance",
            {"utterances": [text], "lang": LANG},
            {"session": session.serialize(), "source": "A", "destination": "B"},
        )
        capture = CaptureSession(self.minicroft, eof_msgs=[intent_msg])
        capture.capture(utterance, timeout=30)
        types = [m.msg_type for m in capture.finish()]
        self.assertIn(intent_msg, types)

    def test_take_a_screenshot(self):
        self._assert_intent("take a screenshot", "take.screenshot.intent")

    def test_capture_the_screen(self):
        self._assert_intent("capture the screen", "take.screenshot.intent")

    def test_grab_the_screen(self):
        self._assert_intent("grab the screen", "take.screenshot.intent")

    def test_save_a_screenshot(self):
        self._assert_intent("save a screenshot", "take.screenshot.intent")

    def test_screenshot_the_display(self):
        self._assert_intent("screenshot the display", "take.screenshot.intent")
