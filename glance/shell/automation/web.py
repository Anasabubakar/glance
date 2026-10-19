"""web.py — sites, searches, maps, translate, weather, email and calendar links: no AI needed."""

from __future__ import annotations

import re
import urllib.parse as up
import urllib.request

from .nlp import fuzzy_pick, parse_when
from .registry import Result, rule

SITES = {
    "youtube": "https://www.youtube.com", "gmail": "https://mail.google.com", "email": "https://mail.google.com",
    "inbox": "https://mail.google.com", "google": "https://www.google.com", "google drive": "https://drive.google.com",
    "drive": "https://drive.google.com", "google docs": "https://docs.google.com", "docs": "https://docs.google.com",
    "google sheets": "https://sheets.google.com", "sheets": "https://sheets.google.com",
    "google slides": "https://slides.google.com", "slides": "https://slides.google.com",
    "google calendar": "https://calendar.google.com", "calendar": "https://calendar.google.com",
    "google maps": "https://maps.google.com", "maps": "https://maps.google.com", "google photos": "https://photos.google.com",
    "photos": "https://photos.google.com", "google meet": "https://meet.google.com", "meet": "https://meet.google.com",
    "github": "https://github.com", "stack overflow": "https://stackoverflow.com", "stackoverflow": "https://stackoverflow.com",
    "reddit": "https://www.reddit.com", "twitter": "https://x.com", "x": "https://x.com", "facebook": "https://www.facebook.com",
    "instagram": "https://www.instagram.com", "linkedin": "https://www.linkedin.com", "whatsapp": "https://web.whatsapp.com",
    "whatsapp web": "https://web.whatsapp.com", "netflix": "https://www.netflix.com", "spotify": "https://open.spotify.com",
    "amazon": "https://www.amazon.com", "wikipedia": "https://www.wikipedia.org", "chatgpt": "https://chatgpt.com",
    "gemini": "https://gemini.google.com", "claude": "https://claude.ai", "notion": "https://www.notion.so",
    "figma": "https://www.figma.com", "canva": "https://www.canva.com", "trello": "https://trello.com",
    "slack": "https://app.slack.com/client", "discord": "https://discord.com/app", "zoom": "https://zoom.us/join",
    "outlook": "https://outlook.live.com", "onedrive": "https://onedrive.live.com", "dropbox": "https://www.dropbox.com",
    "news": "https://news.google.com", "tiktok": "https://www.tiktok.com", "pinterest": "https://www.pinterest.com",
    "twitch": "https://www.twitch.tv", "vercel": "https://vercel.com", "supabase": "https://supabase.com",
    "hacker news": "https://news.ycombinator.com", "translate": "https://translate.google.com",
    "weather": "https://weather.com", "ebay": "https://www.ebay.com", "paypal": "https://www.paypal.com",
    "yahoo": "https://www.yahoo.com", "bing": "https://www.bing.com", "duckduckgo": "https://duckduckgo.com",
}

ENGINES = {  # name -> query URL
    "google": "https://www.google.com/search?q={q}", "youtube": "https://www.youtube.com/results?search_query={q}",
    "amazon": "https://www.amazon.com/s?k={q}", "github": "https://github.com/search?q={q}",
    "wikipedia": "https://en.wikipedia.org/w/index.php?search={q}", "stack overflow": "https://stackoverflow.com/search?q={q}",
    "stackoverflow": "https://stackoverflow.com/search?q={q}", "reddit": "https://www.reddit.com/search/?q={q}",
    "twitter": "https://x.com/search?q={q}", "x": "https://x.com/search?q={q}", "bing": "https://www.bing.com/search?q={q}",
    "duckduckgo": "https://duckduckgo.com/?q={q}", "maps": "https://www.google.com/maps/search/{q}",
    "google maps": "https://www.google.com/maps/search/{q}", "images": "https://www.google.com/search?tbm=isch&q={q}",
    "google images": "https://www.google.com/search?tbm=isch&q={q}", "news": "https://news.google.com/search?q={q}",
    "ebay": "https://www.ebay.com/sch/i.html?_nkw={q}", "linkedin": "https://www.linkedin.com/search/results/all/?keywords={q}",
    "spotify": "https://open.spotify.com/search/{q}", "netflix": "https://www.netflix.com/search?q={q}",
    "gmail": "https://mail.google.com/mail/u/0/#search/{q}", "drive": "https://drive.google.com/drive/search?q={q}",
    "google drive": "https://drive.google.com/drive/search?q={q}", "pinterest": "https://www.pinterest.com/search/pins/?q={q}",
}

LANGS = {"spanish": "es", "french": "fr", "german": "de", "italian": "it", "portuguese": "pt", "russian": "ru",
         "chinese": "zh-CN", "japanese": "ja", "korean": "ko", "arabic": "ar", "hindi": "hi", "turkish": "tr",
         "dutch": "nl", "swedish": "sv", "polish": "pl", "greek": "el", "hebrew": "iw", "yoruba": "yo", "igbo": "ig",
         "hausa": "ha", "swahili": "sw", "english": "en", "indonesian": "id", "vietnamese": "vi", "thai": "th",
         "ukrainian": "uk", "czech": "cs", "romanian": "ro", "hungarian": "hu", "persian": "fa", "urdu": "ur"}


def _q(s: str) -> str:
    return up.quote_plus(s.strip())


def _site_for(name: str):
    n = name.strip().lower()
    n = re.sub(r"^(?:my|the)\s+", "", n)
    if n in SITES:
        return SITES[n]
    hit = fuzzy_pick(n, SITES, cutoff=0.88)
    return SITES[hit] if hit else None


@rule(r"(?:open|go to|visit|navigate to|take me to|pull up|launch|load)\s+(?:up\s+)?(?:the\s+|my\s+)?(?P<u>(?:https?://)?[\w\-]+(?:\.[\w\-]+)+(?:/\S*)?)$",
      name="open_domain", prio=39)
def open_domain(ctx, m, text):
    u = m.group("u")
    ctx.caption("Opening the page", 0.4)
    ctx.open_url(u if u.startswith("http") else "https://" + u)
    return Result("")


@rule(r"(?:open|go to|visit|launch|pull up|load|take me to|show me)\s+(?:up\s+)?(?:the\s+|my\s+)?(?P<s>[\w .&\-']{2,26}?)(?:\s+(?:website|site|page|web app|online))?$",
      name="open_site", prio=40)
def open_site(ctx, m, text):
    url = _site_for(m.group("s"))
    if not url:
        return None
    ctx.caption(f"Opening {m.group('s').strip()}", 0.4)
    ctx.open_url(url)
    return Result("")


def _resolvable(ctx, name: str):
    """A site URL, or an installed app name, for one item of "open A and B"."""
    url = _site_for(name)
    if url:
        return ("url", url)
    from . import apps
    a = apps.find(name)
    return ("app", a["name"]) if a else None


@rule(r"(?:open|launch|start|pull up|bring up)\s+(?:up\s+)?(?P<l>[\w .\-']{2,24}(?:\s*(?:,|\band\b)\s*[\w .\-']{2,24})+)$", name="open_many", prio=38,
      dry=lambda t: _open_many_ok(t))
def open_many(ctx, m, text):
    items = [i.strip() for i in re.split(r"\s*(?:,|\band\b)\s*", m.group("l")) if i.strip()]
    found = [(i, _resolvable(ctx, re.sub(r"^(?:the|my)\s+", "", i))) for i in items]
    if len(items) < 2 or any(r is None for _i, r in found):
        return None
    for name, (kind, target) in found:
        ctx.caption(f"Opening {name}", 0.3)
        if kind == "url":
            ctx.open_url(target)
        else:
            ctx.launch(target)
    return Result("Opening " + ", ".join(i for i, _r in found) + ".")


def _open_many_ok(text: str) -> bool:
    m = re.match(r"(?:open|launch|start|pull up|bring up)\s+(?:up\s+)?(?P<l>[\w .\-']{2,24}(?:\s*(?:,|\band\b)\s*[\w .\-']{2,24})+)$", text)
    if not m:
        return False
    items = [re.sub(r"^(?:the|my)\s+", "", i.strip()) for i in re.split(r"\s*(?:,|\band\b)\s*", m.group("l")) if i.strip()]
    return len(items) >= 2 and all(_site_for(i) or __import__("automation.apps", fromlist=["find"]).find(i) for i in items)


@rule(r"(?:search|look|find|google)\s*(?:the web\s+|online\s+)?(?:for\s+)?(?P<q>.+?)\s+(?:on|in|at|using|with)\s+(?P<e>[\w .]{2,18})$|"
      r"(?:search|look up)\s+(?P<e2>[\w .]{2,18}?)\s+for\s+(?P<q2>.+)$", name="search_engine", prio=41)
def search_engine(ctx, m, text):
    eng = (m.group("e") or m.group("e2") or "").strip().lower()
    q = (m.group("q") or m.group("q2") or "").strip()
    eng = re.sub(r"^(?:the|my)\s+", "", eng)
    if eng not in ENGINES:
        hit = fuzzy_pick(eng, ENGINES, cutoff=0.85)
        if not hit:
            return None
        eng = hit
    ctx.caption(f"Searching {eng} for {q}", 0.5)
    ctx.open_url(ENGINES[eng].format(q=_q(q)))
    return Result("")


@rule(r"(?P<e>youtube|amazon|github|wikipedia|reddit|ebay)\s+(?:search\s+)?(?P<q>.+)$", name="engine_first", prio=42)
def engine_first(ctx, m, text):
    ctx.open_url(ENGINES[m.group("e")].format(q=_q(m.group("q"))))
    return Result("")


@rule(r"(?:play|put on|listen to|watch)\s+(?P<q>.+?)\s+(?:on|in|using)\s+(?P<e>youtube|spotify|netflix)$", name="play_on", prio=43)
def play_on(ctx, m, text):
    q, e = m.group("q"), m.group("e")
    ctx.caption(f"Playing {q} on {e}", 0.5)
    if e == "spotify" and ctx.have("spotify"):
        ctx.spawn(["xdg-open", f"spotify:search:{up.quote(q)}"])
    else:
        ctx.open_url(ENGINES[e].format(q=_q(q)))
    return Result(f"Searching {e} for {q}.")


@rule(r"(?:search the web for|search online for|search google for|search for|look up|look for|find out about|search|google)\s+(?P<q>.{2,80})$", name="search_web", prio=70)
def search_web(ctx, m, text):
    q = m.group("q").strip()
    if re.match(r"(?:the )?(?:file|folder|document|photo|picture|download)s?\b", q):
        return None
    ctx.caption(f"Searching for {q}", 0.5)
    ctx.open_url(ENGINES["google"].format(q=_q(q)))
    return Result("")


@rule(r"(?:directions|route|navigate|drive|walk|how (?:do i|to) get)\s+(?:to|from)\s+(?P<a>.+?)(?:\s+(?:from|to)\s+(?P<b>.+))?$", name="directions", prio=44)
def directions(ctx, m, text):
    a, b = m.group("a"), m.group("b")
    if text.startswith(("directions from", "route from")) and b:
        orig, dest = a, b
    else:
        dest, orig = a, b
    url = "https://www.google.com/maps/dir/?api=1&destination=" + _q(dest) + (f"&origin={_q(orig)}" if orig else "")
    ctx.open_url(url)
    return Result(f"Getting directions to {dest}.")


@rule(r"(?:where is|show me|find|locate)\s+(?P<p>.+?)\s+(?:on|in)\s+(?:the\s+)?(?:google\s+)?map(?:s)?$|(?:map of|show)\s+(?P<p2>.+?)\s+on the map$",
      name="map_place", prio=44)
def map_place(ctx, m, text):
    p = m.group("p") or m.group("p2")
    ctx.open_url(ENGINES["maps"].format(q=_q(p)))
    return Result("")


@rule(r"translate\s+(?P<t>.+?)\s+(?:in)?to\s+(?P<l>[a-z]+)$|how (?:do you|do i|would you) say\s+(?P<t2>.+?)\s+in\s+(?P<l2>[a-z]+)$|"
      r"(?P<t3>.+?)\s+in\s+(?P<l3>spanish|french|german|italian|portuguese|russian|chinese|japanese|korean|arabic|hindi|turkish|yoruba|igbo|hausa|swahili)$",
      name="translate", prio=45)
def translate(ctx, m, text):
    t = m.group("t") or m.group("t2") or m.group("t3")
    lang = (m.group("l") or m.group("l2") or m.group("l3")).lower()
    code = LANGS.get(lang)
    if not code:
        return None
    ctx.open_url(f"https://translate.google.com/?sl=auto&tl={code}&text={_q(t)}&op=translate")
    return Result(f"Translating to {lang.title()}.")


@rule(r"(?:define|definition of|what does\s+(?P<w2>[\w\- ]+?)\s+mean|meaning of|what(?:'s| is) the meaning of)\s*(?P<w>[\w\- ]*)$", name="define", prio=46)
def define(ctx, m, text):
    w = (m.group("w2") or m.group("w") or "").strip()
    if not w or len(w.split()) > 3:
        return None
    ctx.open_url(ENGINES["google"].format(q=_q("define " + w)))
    return Result("")


def fetch_text(url: str, timeout: float = 4.0):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "curl/8"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read(2000).decode("utf-8", "ignore").strip()
    except Exception:
        return None


@rule(r"(?:what(?:'s| is)\s+)?(?:the\s+)?weather(?:\s+(?:like|forecast|today|now|outside))?(?:\s+(?:in|for|at)\s+(?P<c>[\w ,.\-]+))?$|"
      r"(?:is it|will it)\s+(?:going to\s+)?(?:rain|snow|be (?:hot|cold|sunny))(?:\s+(?:in|at)\s+(?P<c2>[\w ,.\-]+))?$|how(?:'s| is) the weather$",
      name="weather", prio=47)
def weather(ctx, m, text):
    city = (m.group("c") or m.group("c2") or "").strip()
    url = "https://wttr.in/" + up.quote(city) + "?format=%l:+%C,+%t,+feels+like+%f,+wind+%w"
    out = fetch_text(url)
    if out and "Unknown location" not in out and len(out) < 220:
        return Result(re.sub(r"\s+", " ", out).replace("+", ""))
    ctx.open_url(ENGINES["google"].format(q=_q("weather " + city)))
    return Result("")


@rule(r"(?:send|write|compose|draft|email)\s+(?:an?\s+)?(?:e-?mail\s+)?(?:to\s+)?(?P<to>[\w.+\-]+@[\w\-]+\.[\w.\-]+|[\w .'\-]{2,30}?)"
      r"(?:\s+(?:about|regarding|saying|that says|with subject|subject)\s+(?P<s>.+))?$", name="email", prio=48)
def email(ctx, m, text):
    to, subj = m.group("to").strip(), (m.group("s") or "").strip()
    if not re.search(r"\bemail|e-mail|mail\b", text) and "@" not in to:
        return None
    if "@" in to:
        url = "mailto:" + to + ("?subject=" + up.quote(subj) if subj else "")
    else:
        url = "https://mail.google.com/mail/?view=cm&fs=1&su=" + up.quote(subj) + "&to=" + up.quote(to)
    ctx.open_url(url)
    return Result("Starting an email.")


_TIMEWORDS = re.compile(r"\b(?:at|on|tomorrow|today|tonight|next|this|in \d+|from|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.I)


@rule(r"(?:add|create|schedule|put|set up|make|book)\s+(?:an?\s+|my\s+)?(?:(?:calendar\s+)?(?:event|meeting|appointment|reminder)\s+)?(?:called\s+|named\s+|for\s+|about\s+)?(?P<t>.+?)\s+"
      r"(?:to|on|in)\s+(?:my\s+)?calendar(?:\s+(?P<w>.+))?$|(?:add|create|schedule|book|set up)\s+(?:an?\s+)?(?:calendar\s+)?(?:event|meeting|appointment)\s+(?P<t2>.+)$",
      name="calendar_event", prio=49)
def calendar_event(ctx, m, text):
    import datetime as dt
    raw = (m.group("t") or m.group("t2") or "").strip()
    extra = (m.group("w") or "") if "w" in m.groupdict() and m.group("w") else ""
    whole = (raw + " " + extra).strip()
    when = parse_when(whole)
    cut = _TIMEWORDS.search(raw)
    title = (raw[:cut.start()] if cut else raw).strip(" ,.-") or "Event"
    title = re.sub(r"^(?:called|named|for|about|a|an|my)\s+", "", title, flags=re.I).strip()
    url = "https://calendar.google.com/calendar/render?action=TEMPLATE&text=" + _q(title)
    if when:
        end = when + dt.timedelta(hours=1)
        url += "&dates=" + when.strftime("%Y%m%dT%H%M%S") + "/" + end.strftime("%Y%m%dT%H%M%S")
    ctx.open_url(url)
    return Result(f"Adding {title} to your calendar" + (f" for {when.strftime('%A at %I:%M %p').replace(' 0', ' ')}." if when else "."))
