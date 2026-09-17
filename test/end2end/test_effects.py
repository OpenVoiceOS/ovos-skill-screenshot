"""Effect assertions for ovos-skill-screenshot's take-screenshot path.

``test_intents_en_us.py`` and the golden suite end capture at the intent
match itself, on the stated grounds that the screenshot side effect needs a
real display -- so neither ever proves the handler does anything after
routing. A handler that routes and then raises, or never emits the message
that actually asks something to take a screenshot, passes both suites
unchanged.

The skill has two paths after routing:

* ``is_ovos_shell`` True: it emits ``ovos.display.screenshot.get`` and lets
  ovos-shell take the real screenshot. This is the path asserted here,
  because it lets the test assert the bus message that does the work
  without needing a display and without writing anywhere on the host --
  ovos-shell is not running in this suite, so nothing consumes the message
  and no file is written.
* no shell: it calls ``mss.mss().shot()`` directly, a real display/host
  write this suite must never trigger (there is no display in CI, and the
  skill's own filesystem write must never land outside a scratch
  directory). This suite forces the shell path and never falls into that
  branch.

The skill also always computes ``self.screenshots_folder`` first, which
creates the configured directory as a side effect -- the skill's own
``settings["screenshots_path"]`` is pointed at a scratch directory before
firing, so nothing is written under the real home directory.
"""
import shutil
import tempfile
import unittest
from pathlib import Path

from ovos_bus_client.message import Message
from ovos_bus_client.session import Session
from ovos_config import Configuration
from ovoscope import CaptureSession, get_minicroft

SKILL_ID = "ovos-skill-screenshot.openvoiceos"
LANG = "en-US"
LOCALE_DIR = Path(__file__).parent.parent.parent / "locale" / "en-US"


def _dialog_templates(name):
    text = (LOCALE_DIR / name).read_text(encoding="utf-8")
    return [line.strip() for line in text.splitlines() if line.strip()]


class TestScreenshotEffects(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.minicroft = get_minicroft([SKILL_ID])
        cls.skill = cls.minicroft.plugin_skills[SKILL_ID].instance
        cls.scratch_dir = tempfile.mkdtemp(prefix="ovos-skill-screenshot-test-")
        # force the shell (bus-message) path: never let this suite fall
        # into the real mss.mss() capture, which would need a real display.
        cfg = dict(Configuration().get("gui", {}))
        cfg["extension"] = "ovos-gui-plugin-shell-companion"
        Configuration().update({"gui": cfg})
        # keep the skill's own filesystem write (screenshots_folder computes
        # and creates this directory as a side effect of being read) inside
        # the test's own scratch tree, never the real home directory.
        cls.skill.settings["screenshots_path"] = cls.scratch_dir

    @classmethod
    def tearDownClass(cls):
        cls.minicroft.stop()
        shutil.rmtree(cls.scratch_dir, ignore_errors=True)

    def _session(self, session_id):
        session = Session(session_id)
        session.lang = LANG
        session.pipeline = [
            "ovos-padatious-pipeline-plugin-high",
            "ovos-padatious-pipeline-plugin-medium",
        ]
        return session

    def _fire(self, text, session_id):
        session = self._session(session_id)
        utterance = Message(
            "recognizer_loop:utterance",
            {"utterances": [text], "lang": LANG},
            {"session": session.serialize(), "source": "A", "destination": "B"},
        )
        capture = CaptureSession(self.minicroft, ignore_messages=[])
        capture.capture(utterance, timeout=30)
        return capture.finish()

    def test_take_screenshot_emits_shell_capture_request(self):
        """The real effect of 'take a screenshot' (on the shell path used
        here to avoid touching a display) is asking ovos-shell to actually
        capture the screen, over the bus, into the configured folder --
        assert that message by type and by its folderpath payload field,
        not merely that routing happened."""
        self.assertIs(self.skill.is_ovos_shell, True, "test setup did not force the shell path")

        messages = self._fire("take a screenshot", "effects-take-screenshot")

        capture_requests = [m for m in messages if m.msg_type == "ovos.display.screenshot.get"]
        self.assertEqual(
            len(capture_requests), 1,
            f"expected exactly one ovos.display.screenshot.get message, got {[m.msg_type for m in messages]!r}",
        )
        self.assertEqual(
            capture_requests[0].data.get("folderpath"), self.scratch_dir,
            "capture request did not carry the configured screenshots folder",
        )

    def test_screenshot_taken_response_speaks_confirmation(self):
        """Once ovos-shell (or, in this suite, the test itself standing in
        for it) reports a completed capture on
        ``ovos.display.screenshot.get.response``, the skill must speak the
        confirmation from its own screenshot_taken.dialog -- assert the
        spoken text, derived from the locale file, not merely that some
        speak fired."""
        result_path = str(Path(self.scratch_dir) / "fake-shell-capture.png")
        response = Message(
            "ovos.display.screenshot.get.response",
            {"result": result_path},
            {"skill_id": SKILL_ID},
        )
        capture = CaptureSession(self.minicroft, ignore_messages=[])
        capture.capture(response, timeout=30)
        messages = capture.finish()

        speak_msgs = [m for m in messages if m.msg_type == "ovos.utterance.speak"]
        self.assertGreaterEqual(
            len(speak_msgs), 1,
            f"expected a spoken confirmation, got types {[m.msg_type for m in messages]!r}",
        )
        expected = set(_dialog_templates("screenshot_taken.dialog"))
        self.assertIn(
            speak_msgs[0].data["utterance"], expected,
            f"spoken confirmation {speak_msgs[0].data['utterance']!r} not in {expected!r}",
        )


if __name__ == "__main__":
    unittest.main()
