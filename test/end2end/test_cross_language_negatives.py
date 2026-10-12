"""A request in one language must not route to this skill in a session of another.

One MiniCroft per session language loads the skill on padacioso. A German
request in an English session, an English request in a German session, and
English requests for other skills in Spanish and French sessions must each
match none of this skill's intents.
"""
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

CROSS_LANG_NEGATIVES = [
    ("Screenshot machen", "en-US", "german utterance in an english session"),
    ("take a screenshot", "de-DE", "english utterance in a german session"),
    ("play some music", "es-ES", "other-skill (music) phrasing, spanish session"),
    ("what's the weather", "fr-FR", "other-skill (weather) phrasing, french session"),
]

_MINICROFTS = {}


def _get_minicroft(lang):
    if lang not in _MINICROFTS:
        _MINICROFTS[lang] = get_minicroft([SKILL_ID], max_wait=150, lang=lang,
                                          default_pipeline=PIPELINE)
    return _MINICROFTS[lang]


@pytest.fixture(scope="module", autouse=True)
def _stop_all_minicrofts():
    yield
    # each MiniCroft restores the default language that was set when it booted,
    # so stopping them in reverse boot order leaves the process default in place
    for minicroft in reversed(list(_MINICROFTS.values())):
        minicroft.stop()
    _MINICROFTS.clear()


def _types(minicroft, text, lang, session_id):
    session = Session(session_id)
    session.lang = lang
    session.pipeline = list(PIPELINE)
    utterance = Message(
        "recognizer_loop:utterance",
        {"utterances": [text], "lang": lang},
        {"session": session.serialize(), "source": "A", "destination": "B"},
    )
    # capture ends when a handler starts, before the screenshot side effect,
    # which needs a real display
    capture = CaptureSession(minicroft, eof_msgs=["mycroft.skill.handler.start"])
    capture.capture(utterance, timeout=30)
    return [m.msg_type for m in capture.finish()]


@pytest.mark.timeout(180)
@pytest.mark.parametrize("negative", CROSS_LANG_NEGATIVES, ids=lambda n: f"{n[1]}-{n[0]}")
def test_cross_language_negative(negative):
    text, lang, _why = negative
    types = _types(_get_minicroft(lang), text, lang, f"negative-{lang}-{text}")
    claimed = any(t.startswith(f"{SKILL_ID}:") for t in types)
    assert not claimed, f"[{lang}] {text!r} was incorrectly claimed by {SKILL_ID}"
