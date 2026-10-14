"""Wake-word matching tolerates how whisper-tiny mishears "Glance"."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "glance", "shell"))
pytest.importorskip("sounddevice")
pytest.importorskip("numpy")

from audio.ambient_listener import wake_match  # noqa: E402


@pytest.mark.parametrize("text", [
    "hey glance what is on my screen",
    "Glance",
    "we first stand for the video, k-lax, what?",   # real whisper mishearing
    "hey clance", "glans, open youtube", "hey k lax", "Clackie help", "yo glance",
])
def test_matches_wake_word_and_mishearings(text):
    assert wake_match(text)


@pytest.mark.parametrize("text", [
    "what is the weather today", "open the glass door", "please play some music",
    "the class starts at nine", "I need a new laptop", "look at that glow",
    "hello there", "blanket and pillows", "chance of rain", "",
])
def test_ignores_unrelated_speech(text):
    assert not wake_match(text)
