"""system.py — volume, brightness, night light, themes, wifi, bluetooth, power, lock, settings pages."""

from __future__ import annotations

import os
import re

from .registry import Result, rule

_SINK = "@DEFAULT_AUDIO_SINK@"
_SRC = "@DEFAULT_AUDIO_SOURCE@"


def _wpctl(ctx, *args):
    return ctx.run(["wpctl", *args], timeout=4)


@rule(r"(?:set\s+|turn\s+|put\s+)?(?:the\s+)?(?:volume|sound)\s+(?:to|at)\s+(?P<n>\d{1,3})\s*(?:%|percent)?$|"
      r"(?:volume|sound)\s+(?P<w>max|maximum|full|half|zero|min|minimum)$", name="volume_set", prio=20)
def volume_set(ctx, m, text):
    if m.group("n") is not None:
        n = max(0, min(100, int(m.group("n"))))
    else:
        n = {"max": 100, "maximum": 100, "full": 100, "half": 50, "zero": 0, "min": 0, "minimum": 0}[m.group("w")]
    ctx.caption(f"Volume {n}%", 0.4)
    _wpctl(ctx, "set-volume", "-l", "1.0", _SINK, f"{n}%")
    return Result(f"Volume {n} percent.")


@rule(r"(?:turn\s+)?(?:the\s+)?(?:volume|sound)\s*(?:up|louder)(?:\s+(?:a\s+)?(?:bit|little|lot))?$|turn it up$|louder$|"
      r"(?:increase|raise)\s+(?:the\s+)?volume$|make\s+(?:it|the\s+sound|the\s+volume)\s+(?:louder|higher|bigger)$", name="volume_up", prio=20)
def volume_up(ctx, m, text):
    step = 20 if "lot" in text else 5 if ("bit" in text or "little" in text) else 10
    ctx.caption("Volume up", 0.4)
    _wpctl(ctx, "set-volume", "-l", "1.0", _SINK, f"{step}%+")
    return Result("")


@rule(r"(?:turn\s+)?(?:the\s+)?(?:volume|sound)\s*(?:down|lower|quieter)(?:\s+(?:a\s+)?(?:bit|little|lot))?$|turn it down$|"
      r"quieter$|(?:decrease|lower|reduce)\s+(?:the\s+)?volume$|make\s+(?:it|the\s+sound|the\s+volume)\s+(?:quieter|lower|softer|smaller)$", name="volume_down", prio=20)
def volume_down(ctx, m, text):
    step = 20 if "lot" in text else 5 if ("bit" in text or "little" in text) else 10
    ctx.caption("Volume down", 0.4)
    _wpctl(ctx, "set-volume", _SINK, f"{step}%-")
    return Result("")


@rule(r"(?P<un>un)?mute(?:\s+(?:the\s+|my\s+)?(?:sound|volume|audio|speakers?|computer|laptop|pc|everything))?$", name="mute", prio=20)
def mute(ctx, m, text):
    _wpctl(ctx, "set-mute", _SINK, "0" if m.group("un") else "1")
    return Result("Unmuted." if m.group("un") else "Muted.")


@rule(r"(?:(?P<un>un)?mute|turn (?P<on>off|on)|(?P<dis>disable|enable))\s+(?:my\s+|the\s+)?(?:mic|microphone)$", name="mic", prio=20)
def mic(ctx, m, text):
    unmute = bool(m.group("un")) or m.group("on") == "on" or m.group("dis") == "enable"
    _wpctl(ctx, "set-mute", _SRC, "0" if unmute else "1")
    return Result("Microphone on." if unmute else "Microphone muted.")


def _brightness_get(ctx):
    rc, out = ctx.run(["gdbus", "call", "--session", "--dest", "org.gnome.SettingsDaemon.Power", "--object-path",
                       "/org/gnome/SettingsDaemon/Power", "--method", "org.freedesktop.DBus.Properties.Get",
                       "org.gnome.SettingsDaemon.Power.Screen", "Brightness"], timeout=3)
    mm = re.search(r"(\d+)", out or "")
    return int(mm.group(1)) if mm else None


def _brightness_set(ctx, n):
    n = max(1, min(100, int(n)))
    ctx.run(["gdbus", "call", "--session", "--dest", "org.gnome.SettingsDaemon.Power", "--object-path",
             "/org/gnome/SettingsDaemon/Power", "--method", "org.freedesktop.DBus.Properties.Set",
             "org.gnome.SettingsDaemon.Power.Screen", "Brightness", f"<int32 {n}>"], timeout=3)
    return n


@rule(r"(?:set\s+)?(?:the\s+)?(?:screen\s+)?brightness\s+(?:to|at)\s+(?P<n>\d{1,3})\s*(?:%|percent)?$", name="brightness_set", prio=20)
def brightness_set(ctx, m, text):
    n = _brightness_set(ctx, int(m.group("n")))
    return Result(f"Brightness {n} percent.")


@rule(r"(?:turn\s+)?(?:the\s+)?(?:screen\s+)?brightness\s+(?P<d>up|down)|(?P<d2>brighter|dimmer)(?:\s+screen)?$|"
      r"(?P<d3>increase|decrease|raise|lower|reduce)\s+(?:the\s+)?(?:screen\s+)?brightness$|(?:dim|brighten)\s+(?:the\s+)?screen$|"
      r"(?:turn|bring)\s+(?:the\s+)?(?:screen\s+)?brightness\s+(?P<d4>up|down)$|(?:turn|bring)\s+(?P<d5>up|down)\s+(?:the\s+)?(?:screen\s+)?brightness$|"
      r"make\s+(?:the\s+)?(?:screen|display)\s+(?P<d6>brighter|dimmer|darker)$",
      name="brightness_rel", prio=20)
def brightness_rel(ctx, m, text):
    up = bool(re.search(r"\b(up|brighter|increase|raise|brighten)\b", text))
    if re.search(r"\b(down|dimmer|darker|decrease|lower|reduce|dim)\b", text):
        up = False
    cur = _brightness_get(ctx)
    if cur is None:
        return None
    n = _brightness_set(ctx, cur + (15 if up else -15))
    return Result(f"Brightness {n} percent.")


@rule(r"(?:turn|switch)\s+(?P<s>on|off)\s+(?:the\s+)?night\s*(?:light|shift|mode)$|(?P<s2>enable|disable)\s+night\s*(?:light|shift|mode)$",
      name="night_light", prio=21)
def night_light(ctx, m, text):
    on = (m.group("s") == "on") or (m.group("s2") == "enable")
    ctx.run(["gsettings", "set", "org.gnome.settings-daemon.plugins.color", "night-light-enabled", "true" if on else "false"])
    return Result("Night light on." if on else "Night light off.")


@rule(r"(?:turn on|enable|switch to|use|go|activate)\s+(?:the\s+)?(?P<t>dark|light)\s*(?:mode|theme)?$|(?P<t2>dark|light)\s+mode$",
      name="theme", prio=21)
def theme(ctx, m, text):
    t = m.group("t") or m.group("t2")
    ctx.run(["gsettings", "set", "org.gnome.desktop.interface", "color-scheme", "prefer-dark" if t == "dark" else "default"])
    return Result(f"{t.title()} mode.")


@rule(r"(?:turn|switch)\s+(?P<s>on|off)\s+(?:do not disturb|dnd|notifications|quiet mode|focus mode)$|"
      r"(?:enable|disable)\s+(?:do not disturb|dnd)$|(?:do not disturb|dnd)\s+(?P<s2>on|off)$", name="dnd", prio=21)
def dnd(ctx, m, text):
    on = (m.group("s") == "on") or ("enable" in text) or (m.group("s2") == "on")
    if "notifications" in text:
        on = m.group("s") == "off"                      # notifications off = do not disturb on
    ctx.run(["gsettings", "set", "org.gnome.desktop.notifications", "show-banners", "false" if on else "true"])
    return Result("Do not disturb is on." if on else "Notifications are back on.")


@rule(r"(?:turn|switch)\s+(?P<s>on|off)\s+(?:the\s+)?(?:wi-?fi|wireless)$|(?P<s2>enable|disable)\s+(?:the\s+)?wi-?fi$", name="wifi", prio=21)
def wifi(ctx, m, text):
    on = (m.group("s") == "on") or (m.group("s2") == "enable")
    rc, _ = ctx.run(["nmcli", "radio", "wifi", "on" if on else "off"])
    return Result("Wi-Fi on." if on else "Wi-Fi off.", ok=rc == 0)


@rule(r"(?:turn|switch)\s+(?P<s>on|off)\s+(?:the\s+)?bluetooth$|(?P<s2>enable|disable)\s+bluetooth$", name="bluetooth", prio=21)
def bluetooth(ctx, m, text):
    on = (m.group("s") == "on") or (m.group("s2") == "enable")
    rc, _ = ctx.run(["rfkill", "unblock" if on else "block", "bluetooth"])
    if on:
        ctx.run(["bluetoothctl", "power", "on"], timeout=4)
    return Result("Bluetooth on." if on else "Bluetooth off.", ok=rc == 0)


@rule(r"(?:turn|switch)\s+(?P<s>on|off)\s+(?:the\s+)?(?:airplane|flight|aeroplane)\s+mode$|(?P<s2>enable|disable)\s+(?:airplane|flight)\s+mode$",
      name="airplane", prio=21)
def airplane(ctx, m, text):
    on = (m.group("s") == "on") or (m.group("s2") == "enable")
    ctx.run(["rfkill", "block" if on else "unblock", "all"])
    return Result("Airplane mode on." if on else "Airplane mode off.")


@rule(r"(?:set\s+)?(?:the\s+)?power\s+(?:mode|profile)\s+(?:to\s+)?(?P<p>performance|balanced|power saver|power-saver|battery saver|saver)$|"
      r"(?:switch|go)\s+to\s+(?P<p2>performance|balanced|power saver|battery saver)\s+(?:mode|power)$|(?P<p3>power saver|battery saver|performance)\s+mode$",
      name="power_profile", prio=21)
def power_profile(ctx, m, text):
    p = (m.group("p") or m.group("p2") or m.group("p3")).replace(" ", "-")
    p = {"battery-saver": "power-saver", "saver": "power-saver"}.get(p, p)
    rc, _ = ctx.run(["powerprofilesctl", "set", p], timeout=4)
    return Result(f"{p.replace('-', ' ').title()} mode.", ok=rc == 0)


@rule(r"lock\s+(?:the\s+|my\s+)?(?:screen|computer|laptop|pc|session)$|lock it$", name="lock", prio=22)
def lock(ctx, m, text):
    ctx.run(["loginctl", "lock-session"])
    return Result("")


@rule(r"(?:put\s+(?:the\s+|my\s+)?(?:computer|laptop|pc)\s+to sleep|go to sleep|suspend(?:\s+(?:the\s+)?(?:computer|laptop|pc))?|sleep)$",
      name="suspend", prio=22)
def suspend(ctx, m, text):
    if not ctx.confirm("put the computer to sleep"):
        return Result("Okay, not sleeping.", ok=False)
    ctx.spawn(["systemctl", "suspend"])
    return Result("")


@rule(r"(?P<v>shut\s*down|power off|turn off|restart|reboot|log\s*out|sign out)\s+(?:the\s+|my\s+)?(?:computer|laptop|pc|system|machine|session)?$",
      name="power_off", prio=22)
def power_off(ctx, m, text):
    v = m.group("v").replace(" ", "")
    if v in ("turnoff",) and not re.search(r"(computer|laptop|pc|system|machine)", text):
        return None
    action = {"shutdown": "poweroff", "poweroff": "poweroff", "turnoff": "poweroff", "restart": "reboot",
              "reboot": "reboot", "logout": "logout", "signout": "logout"}[v]
    if not ctx.confirm({"poweroff": "shut down the computer", "reboot": "restart the computer",
                        "logout": "log you out"}[action]):
        return Result("Okay, I won't.", ok=False)
    if action == "logout":
        ctx.spawn(["gnome-session-quit", "--logout", "--no-prompt"])
    else:
        ctx.spawn(["systemctl", action])
    return Result("")


_PAGES = {"wifi": "wifi", "wi-fi": "wifi", "network": "network", "bluetooth": "bluetooth", "display": "display",
          "displays": "display", "screen": "display", "sound": "sound", "audio": "sound", "volume": "sound",
          "power": "power", "battery": "power", "keyboard": "keyboard", "mouse": "mouse", "touchpad": "mouse",
          "privacy": "privacy", "notifications": "notifications", "apps": "applications", "applications": "applications",
          "default apps": "default-apps", "users": "user-accounts", "accounts": "user-accounts", "printers": "printers",
          "date and time": "datetime", "time": "datetime", "language": "region", "region": "region",
          "background": "background", "wallpaper": "background", "appearance": "background", "about": "system",
          "system": "system", "accessibility": "universal-access", "sharing": "sharing", "search": "search",
          "multitasking": "multitasking", "online accounts": "online-accounts", "mouse and touchpad": "mouse"}


@rule(r"(?:open|show|go to|take me to)\s+(?:the\s+|my\s+)?(?P<p>[\w &\-]{2,24}?)\s+settings$|"
      r"(?:open|show)\s+settings\s+(?:for\s+)?(?P<p2>[\w &\-]{2,24})$", name="settings_page", prio=24)
def settings_page(ctx, m, text):
    key = (m.group("p") or m.group("p2")).strip()
    page = _PAGES.get(key)
    if not page:
        return None
    ctx.caption(f"Opening {key} settings", 0.4)
    ctx.spawn(["gnome-control-center", page])
    return Result(f"Opening {key} settings.")


@rule(r"(?:take|grab|capture)\s+(?:a\s+)?screenshot(?:\s+of\s+(?:my|the)\s+screen)?$|screenshot$", name="screenshot", prio=25)
def screenshot(ctx, m, text):
    from pathlib import Path
    import datetime as _dt
    from screen import gnome_bridge as gb
    if not gb.available():
        return None
    info = gb.screenshot()
    if not info:
        return None
    d = Path(ctx.home) / "Pictures"
    d.mkdir(exist_ok=True)
    dest = d / _dt.datetime.now().strftime("Glance %Y-%m-%d %H-%M-%S.png")
    os.replace(info["path"], dest)
    return Result(f"Saved a screenshot to Pictures, {dest.name}.")


@rule(r"(?:play|pause|resume|stop|toggle)(?:\s+(?:the\s+)?(?:music|song|video|media|playback|playing|it))?$", name="media_toggle", prio=26)
def media_toggle(ctx, m, text):
    return _mpris(ctx, "PlayPause")


@rule(r"(?:next|skip)(?:\s+(?:the\s+)?(?:song|track|video|one))?$|play the next (?:song|track)$", name="media_next", prio=26)
def media_next(ctx, m, text):
    return _mpris(ctx, "Next")


@rule(r"(?:previous|last|go back a)\s+(?:song|track|video)$|play the previous (?:song|track)$|previous$", name="media_prev", prio=26)
def media_prev(ctx, m, text):
    return _mpris(ctx, "Previous")


def _mpris(ctx, method):
    rc, names = ctx.run(["gdbus", "call", "--session", "--dest", "org.freedesktop.DBus", "--object-path",
                         "/org/freedesktop/DBus", "--method", "org.freedesktop.DBus.ListNames"], timeout=4)
    players = re.findall(r"org\.mpris\.MediaPlayer2\.[\w.\-]+", names or "")
    if not players:
        return Result("I don't see a music or video player running.", ok=False)
    # prefer a player that is actually playing
    chosen = players[0]
    for p in players:
        _rc, st = ctx.run(["gdbus", "call", "--session", "--dest", p, "--object-path", "/org/mpris/MediaPlayer2",
                           "--method", "org.freedesktop.DBus.Properties.Get", "org.mpris.MediaPlayer2.Player",
                           "PlaybackStatus"], timeout=3)
        if "Playing" in (st or ""):
            chosen = p
            break
    ctx.run(["gdbus", "call", "--session", "--dest", chosen, "--object-path", "/org/mpris/MediaPlayer2",
             "--method", f"org.mpris.MediaPlayer2.Player.{method}"], timeout=4)
    ctx.caption({"PlayPause": "Play / pause", "Next": "Next", "Previous": "Previous"}[method], 0.4)
    return Result("")
