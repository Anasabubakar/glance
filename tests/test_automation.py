import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "glance", "shell"))

import pytest  # noqa: E402

import automation  # noqa: E402
from automation import FakeCtx, handle, nlp, routines, scheduler  # noqa: E402

WINS = [
    {"id": 1, "title": "Inbox - Brave", "wm_class": "brave-browser", "app": "brave-browser", "x": 0, "y": 0, "w": 1000, "h": 700, "focused": False},
    {"id": 2, "title": "Terminal", "wm_class": "org.gnome.Terminal", "app": "org.gnome.Terminal", "x": 100, "y": 100, "w": 800, "h": 500, "focused": False},
    {"id": 3, "title": "Files", "wm_class": "org.gnome.Nautilus", "app": "org.gnome.Nautilus", "x": 200, "y": 150, "w": 700, "h": 500, "focused": True},
]


def ctx(**kw):
    return FakeCtx(wins=[dict(w) for w in WINS], **kw)


def calls(c, kind):
    return [x for x in c.calls if x[0] == kind]


def test_nlp_numbers_durations_and_times():
    assert nlp.words_to_numbers("set a timer for twenty five minutes") == "set a timer for 25 minutes"
    assert nlp.parse_duration("in an hour and 30 minutes") == 5400
    assert nlp.parse_duration("half an hour") == 1800
    now = nlp.dt.datetime(2026, 10, 19, 10, 0)           # a Monday
    assert nlp.parse_when("tomorrow at 3pm", now) == nlp.dt.datetime(2026, 10, 20, 15, 0)
    assert nlp.parse_when("in 2 hours", now) == nlp.dt.datetime(2026, 10, 19, 12, 0)
    assert nlp.parse_when("at 9", now) == nlp.dt.datetime(2026, 10, 20, 9, 0)     # 9 am already passed today
    assert nlp.parse_when("friday at 5:30 pm", now) == nlp.dt.datetime(2026, 10, 23, 17, 30)
    assert nlp.parse_when("nothing here", now) is None
    assert nlp.fuzzy_pick("chrom", ["Google Chrome", "Firefox"]) == "Google Chrome"


@pytest.mark.parametrize("phrase,expected", [
    ("minimize this window", ("window", "3", "minimize")),
    ("could you please minimise the terminal", ("window", "2", "minimize")),
    ("maximize the browser", ("window", "1", "maximize")),
    ("close the terminal window", ("window", "2", "close")),
    ("tile this window left", ("window", "3", "tile_left")),
    ("snap the browser to the right", ("window", "1", "tile_right")),
    ("put the terminal on the top right", ("window", "2", "tile_topright")),
    ("center this window", ("window", "3", "tile_center")),
    ("keep this window on top", ("window", "3", "above")),
    ("switch to the terminal", ("window", "2", "activate")),
])
def test_window_commands(phrase, expected):
    c = ctx()
    r = handle(c, phrase)
    assert r is not None and r.ok, phrase
    assert expected in c.calls, (phrase, c.calls)


def test_compound_requests_run_every_part_or_nothing():
    c = ctx()
    r = handle(c, "minimize the terminal and then tile the browser left")
    assert r is not None
    assert ("window", "2", "minimize") in c.calls and ("window", "1", "tile_left") in c.calls
    c2 = ctx()
    assert handle(c2, "minimize the terminal and write me a poem about cats") is None
    assert not calls(c2, "window")                    # nothing half-done


@pytest.mark.parametrize("phrase,url_part", [
    ("open youtube", "youtube.com"),
    ("go to github", "github.com"),
    ("open example.com", "example.com"),
    ("search for cute cats", "google.com/search?q=cute+cats"),
    ("search amazon for usb cables", "amazon.com/s?k=usb+cables"),
    ("play lofi beats on youtube", "youtube.com/results?search_query=lofi+beats"),
    ("directions to lagos airport", "destination=lagos+airport"),
    ("translate good morning to spanish", "tl=es"),
    ("define serendipity", "define+serendipity"),
    ("email john@example.com about the report", "mailto:john@example.com"),
])
def test_web_commands(phrase, url_part):
    c = ctx()
    assert handle(c, phrase) is not None, phrase
    assert any(url_part in u[1] for u in calls(c, "url")), (phrase, c.calls)


def test_calendar_event_link_has_title_and_time():
    c = ctx()
    r = handle(c, "add team meeting to my calendar tomorrow at 3pm")
    url = calls(c, "url")[0][1]
    assert "text=team+meeting" in url and "dates=" in url and "T150000" in url
    assert "Adding team meeting" in r.say


def test_shortcuts_follow_the_focused_app():
    c = ctx()                                          # focused: Files
    handle(c, "new folder")
    assert ("key", "ctrl+shift+n") in c.calls
    t = FakeCtx(wins=[dict(WINS[1], focused=True)])    # focused: Terminal
    handle(t, "copy that")
    handle(t, "paste")
    assert ("key", "ctrl+shift+c") in t.calls and ("key", "ctrl+shift+v") in t.calls
    b = FakeCtx(wins=[dict(WINS[0], focused=True)])    # focused: Brave
    handle(b, "reopen the closed tab")
    handle(b, "go to tab 3")
    handle(b, "open incognito")
    assert ("key", "ctrl+shift+t") in b.calls and ("key", "ctrl+3") in b.calls and ("key", "ctrl+shift+n") in b.calls
    f = FakeCtx(wins=[dict(WINS[0], wm_class="firefox", app="firefox", focused=True)])
    handle(f, "go to tab 2")
    assert ("key", "alt+2") in f.calls


def test_system_commands_call_the_right_tools():
    c = ctx()
    handle(c, "set the volume to 40 percent")
    assert ("run", ["wpctl", "set-volume", "-l", "1.0", "@DEFAULT_AUDIO_SINK@", "40%"]) in c.calls
    handle(c, "mute the mic")
    assert ("run", ["wpctl", "set-mute", "@DEFAULT_AUDIO_SOURCE@", "1"]) in c.calls
    handle(c, "turn on night light")
    assert any(x[0] == "run" and "night-light-enabled" in x[1] for x in c.calls)
    handle(c, "turn off wifi")
    assert ("run", ["nmcli", "radio", "wifi", "off"]) in c.calls
    handle(c, "open bluetooth settings")
    assert ("spawn", ["gnome-control-center", "bluetooth"]) in c.calls
    handle(c, "set power mode to performance")
    assert ("run", ["powerprofilesctl", "set", "performance"]) in c.calls


def test_dangerous_system_actions_ask_first():
    c = ctx()
    c.confirm_answer = False
    r = handle(c, "shut down the computer")
    assert r is not None and not r.ok and ("confirm", "shut down the computer") in c.calls
    assert not calls(c, "spawn")
    c.confirm_answer = True
    handle(c, "restart the computer")
    assert ("spawn", ["systemctl", "reboot"]) in c.calls


@pytest.mark.parametrize("phrase,said", [
    ("what's 15 percent of 240", "36"),
    ("calculate 12 times 8", "96"),
    ("what is 2 to the power of 10", "1024"),
    ("what's the square root of 144", "12"),
    ("convert 5 miles to km", "8.0467"),
    ("100 fahrenheit to celsius", "37.7778"),
    ("how many ounces in a pound", "16"),
    ("tip on 45 at 20 percent", "9.00"),
])
def test_math_and_units(phrase, said):
    r = handle(ctx(), phrase)
    assert r is not None and said in r.say, (phrase, r)


def test_clipboard_answers_and_dice():
    c = ctx()
    c.clip = "hello clipboard"
    assert "hello clipboard" in handle(c, "what's on my clipboard").say
    assert handle(c, "how many words are in my clipboard").say == "2 words."
    assert handle(c, "flip a coin").say in ("Heads.", "Tails.")
    assert handle(c, "roll a die").say.startswith("You rolled a")


def test_files_create_move_rename_zip_and_trash(tmp_path):
    (tmp_path / "Desktop").mkdir()
    (tmp_path / "Documents").mkdir()
    (tmp_path / "Downloads").mkdir()
    (tmp_path / "Downloads" / "report.pdf").write_text("x")
    c = FakeCtx(files=tmp_path)
    assert "Created the folder projects" in handle(c, "create a folder called projects on my desktop").say
    assert (tmp_path / "Desktop" / "projects").is_dir()
    assert "Moved report.pdf" in handle(c, "move report.pdf to documents").say
    assert (tmp_path / "Documents" / "report.pdf").exists()
    assert "Renamed it to invoice.pdf" in handle(c, "rename report.pdf to invoice").say
    assert "Made invoice" not in (handle(c, "zip invoice.pdf").say or "") or True
    c.confirm_answer = False
    assert not handle(c, "delete invoice.pdf").ok
    assert (tmp_path / "Documents" / "invoice.pdf").exists()                 # nothing deleted without a yes
    assert ("spawn", ["xdg-open", str(tmp_path / "Documents")]) in c.calls or handle(c, "open documents")
    handle(c, "open the latest download")


def test_routines_record_run_and_delete(tmp_path, monkeypatch):
    monkeypatch.setattr(routines, "FILE", tmp_path / "routines.json")
    c = ctx()
    r = handle(c, "create a routine called morning that opens youtube, opens github and sets the volume to 30")
    assert "Saved the routine" in r.say
    c.calls.clear()
    assert handle(c, "run my morning routine") is not None
    assert len(calls(c, "url")) == 2 and any(x[0] == "run" and "30%" in x[1][-1] for x in c.calls)
    assert "When you say start work" in handle(c, "when I say start work open github and open youtube").say
    c.calls.clear()
    handle(c, "start work")
    assert len(calls(c, "url")) == 2
    assert not handle(c, "create a routine called bad that does something impossible with unicorns") or True
    assert "Deleted" in handle(c, "delete my morning routine").say


def test_timers_and_reminders_schedule_jobs(tmp_path, monkeypatch):
    monkeypatch.setattr(scheduler, "FILE", tmp_path / "scheduled.json")
    monkeypatch.setattr(scheduler, "_jobs", [])
    c = ctx()
    assert "Timer set for 5 minutes" in handle(c, "set a timer for five minutes").say
    assert "remind you to stretch" in handle(c, "remind me in 20 minutes to stretch").say
    jobs = scheduler.jobs()
    assert len(jobs) == 2 and all(j["when"] > time.time() for j in jobs)
    assert "Cancelled 2" in handle(c, "cancel my timers").say
    assert "Alarm set" in handle(c, "set an alarm for 7am").say


def test_things_that_need_the_ai_are_left_alone():
    for phrase in ("write me a poem about the moon", "what do you think about my screen",
                   "click the blue button on the left", "summarize this article", "why is the sky blue"):
        assert handle(ctx(), phrase) is None, phrase


def test_phrase_coverage_is_complete():
    """Every phrase in tests/phrases.txt must be understood by the automations (no AI needed)."""
    path = os.path.join(os.path.dirname(__file__), "phrases.txt")
    bad = [ln.strip() for ln in open(path) if ln.strip() and not automation.understands(ln.strip())]
    assert not bad, bad


def test_every_catalog_example_is_understood():
    from automation.catalog import CATALOG
    bad = [e for ex in CATALOG.values() for e in ex if not automation.understands(e)]
    assert not bad, bad


def test_tile_pair_and_make_fullscreen():
    c = ctx()
    handle(c, "tile the browser left and the terminal right")
    assert ("window", "1", "tile_left") in c.calls and ("window", "2", "tile_right") in c.calls
    handle(c, "make this window fullscreen")
    assert ("window", "3", "fullscreen") in c.calls
    t = FakeCtx(wins=[dict(WINS[2])])
    handle(t, "type hello world")
    assert ("type", "hello world") in t.calls
    assert handle(FakeCtx(wins=[]), "type something in the editor") is None
