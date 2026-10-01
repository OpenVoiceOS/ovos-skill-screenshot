"""Golden-utterance end-to-end coverage for ovos-skill-screenshot, every locale.

Each ``golden_utterances_<lang>.jsonl`` file holds the golden rows of one
locale. The suite boots one ``MiniCroft`` per language, with that language as
the configured default, and asserts that each row reaches its own intent.

Capture ends at ``mycroft.skill.handler.start``, right after the intent
binding fires and before the handler body runs, the same technique used by
``test_intents_en_us.py``: the screenshot side effect needs a real display,
which isn't available in CI/offline test environments, so routing is
asserted without depending on it.

Rows marked ``machine_generated`` run even when they carry
``needs_manual: true``. A human-written row with ``needs_manual: true`` is
skipped.
"""
import json
from pathlib import Path

import pytest
from ovos_bus_client.message import Message
from ovos_bus_client.session import Session
from ovoscope import CaptureSession, get_minicroft

SKILL_ID = "ovos-skill-screenshot.openvoiceos"

_PIPELINE = [
    "ovos-padatious-pipeline-plugin-high",
    "ovos-padatious-pipeline-plugin-medium",
]

GOLDEN_DIR = Path(__file__).parent

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
]


def _load_golden_rows():
    rows = []
    for path in sorted(GOLDEN_DIR.glob("golden_utterances_*.jsonl")):
        lang = path.stem.split("_", 2)[2]
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            row.setdefault("lang", lang)
            if row.get("needs_manual") and not row.get("machine_generated"):
                continue
            rows.append(row)
    return rows


GOLDEN_ROWS = [pytest.param(r, id=f"{r['lang']}-{r['utterance']}")
               for r in _load_golden_rows()]


class _MiniCroftPerLang:
    """Keeps one MiniCroft alive; boots a new one when the language changes."""

    def __init__(self):
        self.lang = None
        self.mc = None

    def get(self, lang):
        if lang != self.lang:
            self.stop()
            self.mc = get_minicroft([SKILL_ID], lang=lang)
            self.lang = lang
        return self.mc

    def stop(self):
        if self.mc is not None:
            self.mc.stop()
        self.mc = None
        self.lang = None


@pytest.fixture(scope="module")
def minicrofts():
    holder = _MiniCroftPerLang()
    yield holder
    holder.stop()


def _types(mc, text, lang, session_id):
    session = Session(session_id)
    session.lang = lang
    session.pipeline = list(_PIPELINE)
    utterance = Message(
        "recognizer_loop:utterance",
        {"utterances": [text], "lang": lang},
        {"session": session.serialize(), "source": "A", "destination": "B"},
    )
    # ends at handler start, before the screenshot side effect (which needs
    # a real display) runs -- see module docstring.
    capture = CaptureSession(mc, eof_msgs=["mycroft.skill.handler.start"])
    capture.capture(utterance, timeout=30)
    return [m.msg_type for m in capture.finish()]


def _matched_intents(types):
    return [t for t in types if t.startswith(f"{SKILL_ID}:")]


@pytest.mark.timeout(180)
@pytest.mark.parametrize("row", GOLDEN_ROWS)
def test_golden_utterance(minicrofts, row):
    lang = row["lang"]
    base = row["intent_label"].removesuffix(".intent")
    expected = f"{SKILL_ID}:{base}"
    types = _types(minicrofts.get(lang), row["utterance"], lang,
                   f"golden-{lang}-{row['utterance']}")
    assert _matched_intents(types) == [expected], (
        f"{lang} {row['utterance']!r}: expected {expected!r}, "
        f"matched {_matched_intents(types)!r}"
    )


@pytest.mark.timeout(180)
@pytest.mark.parametrize("negative", NEGATIVE_UTTERANCES, ids=lambda n: n[0])
def test_negative_confusable_not_claimed(minicrofts, negative):
    text, source_skill = negative
    types = _types(minicrofts.get("en-US"), text, "en-US", f"negative-{text}")
    assert not _matched_intents(types), (
        f"{text!r} (from {source_skill}) was incorrectly claimed by {SKILL_ID}"
    )
