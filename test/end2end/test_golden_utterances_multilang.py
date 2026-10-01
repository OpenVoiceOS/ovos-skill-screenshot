"""Multilingual golden-utterance end-to-end coverage for
ovos-skill-screenshot.

test_intents_en_us.py only exercised en-US. This skill registers two
Padatious/Padacioso file-intents (take_screenshot.intent,
screenshot_location.intent); every locale under locale/ ships real .intent
content for both. Each golden row is a literal resolution of that locale's
own .intent template lines -- alternatives ("a|b") and optional groups
("[a|b]") are resolved to one concrete choice, {delay} slots (where a
locale's take_screenshot.intent carries one) are filled with a literal
number -- no translated or invented prose is introduced. Where a locale's
file has no alternation to vary (a single flat line), fewer than three rows
exist for that intent; those gaps are listed in the PR body rather than
padded with invented phrasing.

Unlike ovos-skill-alerts' shared-MiniCroft-with-secondary-langs approach
(blocked by ovoscope#179 at multi-locale scale), this suite follows the
ovos-skill-date-time per-locale pattern (see
test/end2end/test_intents_it_it.py on that repo's dev branch): one
MiniCroft is booted per locale, in turn, torn down when the module's tests
finish. Only the pure-Python, swig-free padacioso template engine is
booted (no padatious training phase, so no "mycroft.skills.trained" wait
across many locales).
"""
import json
from pathlib import Path

import pytest
from ovos_bus_client.message import Message
from ovos_bus_client.session import Session
from ovoscope import CaptureSession, get_minicroft

SKILL_ID = "ovos-skill-screenshot.openvoiceos"

PIPELINE = [
    "ovos-padacioso-pipeline-plugin-high",
    "ovos-padacioso-pipeline-plugin-medium",
    "ovos-padacioso-pipeline-plugin-low",
]

END2END_DIR = Path(__file__).parent

LANGS = [
    "ca-ES", "da-DK", "de-DE", "en-US", "es-ES", "eu-ES", "fr-FR", "gl-ES",
    "it-IT", "kab", "nl-NL", "oc-FR", "pt-BR", "pt-PT", "sv-SE",
]

CROSS_LANG_NEGATIVES = [
    ("Screenshot machen", "en-US", "german utterance in an english session"),
    ("take a screenshot", "de-DE", "english utterance in a german session"),
    ("play some music", "es-ES", "other-skill (music) phrasing, spanish session"),
    ("what's the weather", "fr-FR", "other-skill (weather) phrasing, french session"),
]


def _candidates(skill_id: str, intent_label: str) -> set:
    """padatious/padacioso plugin versions register the matched-intent bus
    event under different normalizations of the ``.intent`` filename
    basename -- candidates cover both the suffixed and unsuffixed forms."""
    base = intent_label[:-len(".intent")] if intent_label.endswith(".intent") else intent_label
    return {f"{skill_id}:{intent_label}", f"{skill_id}:{base}"}


def _load_rows(lang):
    path = END2END_DIR / f"golden_utterances_{lang}.jsonl"
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("needs_manual"):
                continue
            rows.append(row)
    return rows


ALL_ROWS = []
for _lang in LANGS:
    for _row in _load_rows(_lang):
        ALL_ROWS.append(_row)


def _golden_id(row):
    return f"{row['lang']}-{row['intent_label']}-{row['utterance']}"


GOLDEN_ROWS = [pytest.param(r, id=_golden_id(r)) for r in ALL_ROWS]

# lazily booted, one per locale, in the order LANGS/ALL_ROWS visits them;
# stopped by the module-scoped autouse fixture below once every test using
# it has run.
_MINICROFTS = {}


def _get_minicroft(lang):
    mc = _MINICROFTS.get(lang)
    if mc is None:
        mc = get_minicroft([SKILL_ID], max_wait=150, lang=lang,
                            default_pipeline=PIPELINE)
        _MINICROFTS[lang] = mc
    return mc


@pytest.fixture(scope="module", autouse=True)
def _stop_all_minicrofts():
    yield
    for mc in _MINICROFTS.values():
        mc.stop()
    _MINICROFTS.clear()


def _types(mc, text, lang, session_id):
    session = Session(session_id)
    session.lang = lang
    session.pipeline = list(PIPELINE)
    utterance = Message(
        "recognizer_loop:utterance",
        {"utterances": [text], "lang": lang},
        {"session": session.serialize(), "source": "A", "destination": "B"},
    )
    capture = CaptureSession(mc, eof_msgs=["mycroft.skill.handler.start"])
    capture.capture(utterance, timeout=30)
    return [m.msg_type for m in capture.finish()]


@pytest.mark.timeout(180)
@pytest.mark.parametrize("row", GOLDEN_ROWS, ids=_golden_id)
def test_golden_utterance_multilang(row):
    mc = _get_minicroft(row["lang"])
    candidates = _candidates(SKILL_ID, row["intent_label"])
    types = _types(mc, row["utterance"], row["lang"], f"golden-{_golden_id(row)}")
    assert any(t in candidates for t in types), (
        f"[{row['lang']}] {row['utterance']!r}: expected one of {sorted(candidates)!r}, got {types!r}"
    )


@pytest.mark.timeout(180)
@pytest.mark.parametrize("negative", CROSS_LANG_NEGATIVES, ids=lambda n: f"{n[1]}-{n[0]}")
def test_cross_language_negative(negative):
    text, lang, _why = negative
    mc = _get_minicroft(lang)
    types = _types(mc, text, lang, f"negative-{lang}-{text}")
    claimed = any(t.startswith(f"{SKILL_ID}:") for t in types)
    assert not claimed, f"[{lang}] {text!r} was incorrectly claimed by {SKILL_ID}"
