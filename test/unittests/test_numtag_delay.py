"""The delay slot is read in every locale that has a numtag lexicon.

Each row is a phrase of the locale's own take_screenshot.intent. padacioso
cuts the slot out of the phrase; the handler must wait the number of seconds a
speaker says. The gold is the number in the phrase, not a parser result.
"""
from os.path import dirname, join
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from ovos_bus_client.message import Message
from padacioso import IntentContainer

from ovos_skill_screenshot import ScreenshotSkill

LOCALE = join(dirname(dirname(dirname(__file__))), "locale")

# (locale dir, skill lang, utterance, seconds)
ROWS = [
    ("da-DK", "da-dk", "tag et skærmbillede om fem sekunder", 5),
    ("da-DK", "da-dk", "skærmbillede om ti sekunder", 10),
    ("en-US", "en-us", "take a screenshot in five seconds", 5),
    ("en-US", "en-us", "screenshot in ten seconds", 10),
    ("en-US", "en-us", "screenshot in twenty five seconds", 25),
    ("en-US", "en-us", "screenshot in 7 seconds", 7),
    ("fa-IR", "fa-ir", "صفحه نمایش در پنج ثانیه", 5),
    ("fa-IR", "fa-ir", "صفحه نمایش در ده ثانیه", 10),
    ("kab", "kab", "tugna n ugdil deg semmus tesdatin", 5),
    ("kab", "kab", "tugna n ugdil deg mraw tesdatin", 10),
    ("oc-FR", "oc-fr", "captura d'aicí a cinc segondas", 5),
    ("oc-FR", "oc-fr", "captura d'aicí a dètz segondas", 10),
    ("pl-PL", "pl-pl", "zrzut ekranu w pięć sekundy", 5),
    ("pl-PL", "pl-pl", "zrzut ekranu w dziesięć sekundy", 10),
    ("pt-BR", "pt-br", "captura de tela em cinco segundos", 5),
    ("pt-BR", "pt-br", "captura de tela em dez segundos", 10),
    ("ru-RU", "ru-ru", "Скриншот пять секунды", 5),
    ("ru-RU", "ru-ru", "Скриншот десять секунды", 10),
    ("sv-SE", "sv-se", "skärmdump om fem sekunder", 5),
    ("sv-SE", "sv-se", "skärmdump om tio sekunder", 10),
]


def _slot(locale, utterance):
    with open(join(LOCALE, locale, "take_screenshot.intent"), encoding="utf-8") as f:
        container = IntentContainer()
        container.add_intent("take_screenshot", f.read().splitlines())
    match = container.calc_intent(utterance)
    assert match["name"] == "take_screenshot", (utterance, match)
    return match["entities"]["delay"]


def _handle(lang, delay):
    skill = ScreenshotSkill.__new__(ScreenshotSkill)
    skill._settings = {}
    skill.speak_dialog = MagicMock()
    skill.schedule_event = MagicMock()
    skill._take_screenshot_impl = MagicMock()
    with patch.object(ScreenshotSkill, "lang", new_callable=PropertyMock, return_value=lang):
        skill.handle_screenshot_intent(Message("test", {"delay": delay}, {}))
    return skill


@pytest.mark.parametrize("locale,lang,utterance,seconds", ROWS)
def test_waits_the_spoken_number_of_seconds(locale, lang, utterance, seconds):
    skill = _handle(lang, _slot(locale, utterance))
    skill._take_screenshot_impl.assert_not_called()
    assert skill.schedule_event.call_args.args[1] == seconds
    skill.speak_dialog.assert_called_once_with("screenshot_delayed", {"delay": seconds})


@pytest.mark.parametrize("delay", ["", "gibberish", "zero"])
def test_no_positive_number_captures_at_once(delay):
    skill = _handle("en-us", delay)
    skill.schedule_event.assert_not_called()
    skill._take_screenshot_impl.assert_called_once()
