"""
scheduler.py — one background thread that fires timers, reminders and scheduled routines,
surviving restarts (jobs are saved to ~/.glance/scheduled.json).

A job: {"id", "when": epoch seconds, "kind": "say" | "routine", "text": ..., "repeat": "" | "daily" | "weekdays"}
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from pathlib import Path

FILE = Path.home() / ".glance" / "scheduled.json"
_lock = threading.Lock()
_jobs: list = []
_started = False
_handler = None            # fn(job) called on the scheduler thread when a job is due


def _load():
    global _jobs
    try:
        _jobs = json.loads(FILE.read_text())
    except (OSError, ValueError):
        _jobs = []


def _save():
    try:
        FILE.parent.mkdir(parents=True, exist_ok=True)
        FILE.write_text(json.dumps(_jobs, indent=1))
    except OSError:
        pass


def add(when: float, kind: str, text: str, repeat: str = "") -> str:
    with _lock:
        jid = uuid.uuid4().hex[:8]
        _jobs.append({"id": jid, "when": float(when), "kind": kind, "text": text, "repeat": repeat})
        _save()
    return jid


def remove(jid: str) -> bool:
    with _lock:
        n = len(_jobs)
        _jobs[:] = [j for j in _jobs if j["id"] != jid]
        _save()
        return len(_jobs) != n


def jobs() -> list:
    with _lock:
        return [dict(j) for j in _jobs]


def _next_time(job):
    import datetime as dt
    d = dt.datetime.fromtimestamp(job["when"])
    step = dt.timedelta(days=1)
    nxt = d + step
    if job.get("repeat") == "weekdays":
        while nxt.weekday() >= 5:
            nxt += step
    return nxt.timestamp()


def _loop():
    while True:
        time.sleep(1.0)
        due = []
        with _lock:
            now = time.time()
            for j in list(_jobs):
                if j["when"] <= now:
                    due.append(dict(j))
                    if j.get("repeat"):
                        j["when"] = _next_time(j)
                        while j["when"] <= now:
                            j["when"] = _next_time(j)
                    else:
                        _jobs.remove(j)
            if due:
                _save()
        for j in due:
            try:
                if _handler:
                    _handler(j)
            except Exception as e:                  # a bad job must not kill the clock
                print(f"[glance] scheduled job failed: {type(e).__name__}: {e}", flush=True)


def start(handler):
    """Begin firing jobs; `handler(job)` does the work. Safe to call more than once."""
    global _started, _handler
    _handler = handler
    if _started:
        return
    _started = True
    _load()
    threading.Thread(target=_loop, daemon=True, name="glance-scheduler").start()
