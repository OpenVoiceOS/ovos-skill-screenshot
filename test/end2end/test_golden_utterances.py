"""Golden-utterance end-to-end coverage for ovos-skill-screenshot (en-US).

The golden corpus (``golden_utterances.jsonl``) is a vendored slice of the
shared ovoscope golden-utterance dataset, keyed by
``skill_id == "ovos-skill-screenshot.openvoiceos"``. One shared
``MiniCroft`` (module-scoped fixture) is booted for the whole suite.

Capture ends at the intent match (``eof_msgs=[intent_msg-shaped candidates]``
is not viable since we don't know in advance which candidate name fires, so
capture instead ends at ``mycroft.skill.handler.start`` -- right after the
intent binding fires, before the handler body runs), the same technique used
by ``test_intents_en_us.py``: the screenshot side effect needs a real
display, which isn't available in CI/offline test environments, so routing
is asserted without depending on it.
"""
import json
from pathlib import Path

import pytest
from ovos_bus_client.message import Message
from ovos_bus_client.session import Session
from ovoscope import CaptureSession, get_minicroft

SKILL_ID = "ovos-skill-screenshot.openvoiceos"
LANG = "en-US"

_PIPELINE = [
    "ovos-padatious-pipeline-plugin-high",
    "ovos-padatious-pipeline-plugin-medium",
]

GOLDEN_PATH = Path(__file__).parent / "golden_utterances.jsonl"

# utterances lifted verbatim from OTHER skills' golden-utterance slices,
# picked for lexical overlap with screenshot's "capture"/"screen"/"save"/
# "display" vocabulary.
NEGATIVE_UTTERANCES = [
    ("play some music", "ovos-skill-music.openvoiceos"),
    ("turn up the brightness", "ovos-skill-homeassistant.openvoiceos"),
    ("what's the weather", "ovos-skill-weather.openvoiceos"),
    ("save my location", "ovos-skill-homeassistant.openvoiceos"),
    ("record a voice memo", "ovos-skill-voice-memo.openvoiceos"),
    ("turn off the display", "ovos-skill-homeassistant.openvoiceos"),
    # sibling confusions introduced by the "please"/"can you" politeness
    # prefixes and the "picture of" phrasing added to take_screenshot.intent
    ("take a picture", "ovos-skill-camera.openvoiceos"),
    ("take a picture of the cat", "ovos-skill-camera.openvoiceos"),
    ("can you turn up the volume", "ovos-skill-volume.openvoiceos"),
    ("please turn off the lights", "ovos-skill-homeassistant.openvoiceos"),
    ("can you play some music", "ovos-skill-music.openvoiceos"),
    ("please save my location", "ovos-skill-homeassistant.openvoiceos"),
    # sibling confusions for the new screenshot_location.intent phrasings
    ("where is my music folder", "ovos-skill-file-browser.openvoiceos"),
    ("open my pictures folder", "ovos-skill-file-browser.openvoiceos"),
]


def _candidates(skill_id: str, intent_label: str) -> set:
    """padatious/padacioso plugin versions register the matched-intent bus
    event under different normalizations of the ``.intent`` filename
    basename -- candidates cover both the suffixed and unsuffixed forms."""
    base = intent_label[:-len(".intent")] if intent_label.endswith(".intent") else intent_label
    return {f"{skill_id}:{intent_label}", f"{skill_id}:{base}"}


def _load_golden_rows():
    rows = []
    with open(GOLDEN_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("needs_manual"):
                continue
            rows.append(row)
    return rows


GOLDEN_ROWS = [pytest.param(r, id=r["utterance"]) for r in _load_golden_rows()]


@pytest.fixture(scope="module")
def minicroft():
    mc = get_minicroft([SKILL_ID])
    yield mc
    mc.stop()


def _types(mc, text, session_id):
    session = Session(session_id)
    session.lang = LANG
    session.pipeline = list(_PIPELINE)
    utterance = Message(
        "recognizer_loop:utterance",
        {"utterances": [text], "lang": LANG},
        {"session": session.serialize(), "source": "A", "destination": "B"},
    )
    # ends at handler start, before the screenshot side effect (which needs
    # a real display) runs -- see module docstring.
    capture = CaptureSession(mc, eof_msgs=["mycroft.skill.handler.start"])
    capture.capture(utterance, timeout=30)
    return [m.msg_type for m in capture.finish()]


def _golden_id(row):
    return row["utterance"]


@pytest.mark.timeout(60)
@pytest.mark.parametrize("row", GOLDEN_ROWS, ids=_golden_id)
def test_golden_utterance(minicroft, row):
    candidates = _candidates(SKILL_ID, row["intent_label"])
    types = _types(minicroft, row["utterance"], f"golden-{_golden_id(row)}")
    assert any(t in candidates for t in types), (
        f"{row['utterance']!r}: expected one of {sorted(candidates)!r}, got {types!r}"
    )


@pytest.mark.timeout(60)
@pytest.mark.parametrize("negative", NEGATIVE_UTTERANCES, ids=lambda n: n[0])
def test_negative_confusable_not_claimed(minicroft, negative):
    text, source_skill = negative
    types = _types(minicroft, text, f"negative-{text}")
    claimed = any(t.startswith(f"{SKILL_ID}:") for t in types)
    assert not claimed, f"{text!r} (from {source_skill}) was incorrectly claimed by {SKILL_ID}"
