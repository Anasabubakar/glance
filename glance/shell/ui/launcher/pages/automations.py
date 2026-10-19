"""
Automations — fast, exact, no-AI commands: the catalog of what Glance does instantly, your own
routines (voice phrase or schedule), and scheduled jobs.
"""

from __future__ import annotations

import json
import time

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QVBoxLayout, QWidget

from .. import design_tokens as dt
from ..page_base import BasePage
from ..widgets import Card, DangerButton, Divider, FlatButton, GhostButton, GradientButton, PillBadge


class AutomationsPage(BasePage):
    title = "Automations"
    icon = "activity"
    subtitle = "Instant commands that never need an AI, and routines you build yourself."

    def __init__(self, parent=None):
        super().__init__(parent)

        self.body_layout.addWidget(self.section_label("Your routines"))
        self._routines = Card(padding=18)
        self.body_layout.addWidget(self._routines)

        self.body_layout.addWidget(self.section_label("New routine"))
        form = Card(padding=18)
        form._layout.setSpacing(10)
        self._name = QLineEdit()
        self._name.setPlaceholderText("Name, for example morning")
        self._phrase = QLineEdit()
        self._phrase.setPlaceholderText("Optional phrase that starts it, for example start my day")
        self._steps = QPlainTextEdit()
        self._steps.setPlaceholderText("One command per line, in plain words:\nopen gmail\nopen youtube\nset the volume to 30")
        self._steps.setFixedHeight(110)
        self._when = QLineEdit()
        self._when.setPlaceholderText("Optional schedule, for example every weekday at 9am (leave empty to run it by voice)")
        for w in (self._name, self._phrase, self._when):
            w.setStyleSheet(dt.LINEEDIT_QSS)
        self._steps.setStyleSheet(dt.TEXTEDIT_QSS)
        for w in (self._name, self._phrase, self._steps, self._when):
            form.add_widget(w)
        row = QHBoxLayout()
        save = GradientButton("Save routine")
        save.setMinimumHeight(38)
        save.clicked.connect(self._save)
        row.addWidget(save)
        self._status = QLabel("")
        self._status.setFont(dt.font(13))
        self._status.setWordWrap(True)
        row.addWidget(self._status, 1)
        form.add_layout(row)
        self.body_layout.addWidget(form)

        self.body_layout.addWidget(self.section_label("Scheduled"))
        self._jobs = Card(padding=18)
        self.body_layout.addWidget(self._jobs)

        self.body_layout.addWidget(self.section_label("What Glance does instantly"))
        self.body_layout.addWidget(self.hint_label("Say any of these. They run in a fraction of a second and never use the AI."))
        self._catalog = Card(padding=18)
        self.body_layout.addWidget(self._catalog)
        self.body_layout.addStretch()
        self._render_catalog()
        self.on_activate()

    # ── rendering ────────────────────────────────────────────────────────
    def on_activate(self):
        self._render_routines()
        self._render_jobs()

    def _render_routines(self):
        from automation import routines
        c = self._routines
        c.clear_layout()
        rs = routines.load()
        if not rs:
            c.add_widget(self.hint_label("No routines yet. Create one below, or say: create a routine called "
                                         "morning that opens gmail and opens calendar."))
            return
        for i, r in enumerate(rs):
            if i:
                c.add_widget(Divider())
            row = QHBoxLayout()
            col = QVBoxLayout()
            col.setSpacing(2)
            t = QLabel(r["name"])
            t.setFont(dt.font(14, dt.QFont.Weight.DemiBold))
            col.addWidget(t)
            col.addWidget(self.hint_label(" → ".join(r["steps"])[:140]))
            row.addLayout(col, 1)
            if r.get("phrases"):
                row.addWidget(PillBadge("says: " + r["phrases"][0][:22], "accent"))
            run = FlatButton("Run")
            run.clicked.connect(lambda _c=False, n=r["name"]: self._run(n))
            rm = GhostButton("Delete")
            rm.clicked.connect(lambda _c=False, n=r["name"]: self._delete(n))
            row.addWidget(run)
            row.addWidget(rm)
            c.add_layout(row)

    def _render_jobs(self):
        from automation import scheduler
        c = self._jobs
        c.clear_layout()
        jobs = sorted(scheduler.jobs(), key=lambda j: j["when"])
        if not jobs:
            c.add_widget(self.hint_label("Nothing scheduled. Say: remind me in 20 minutes to stretch."))
            return
        for i, j in enumerate(jobs):
            if i:
                c.add_widget(Divider())
            row = QHBoxLayout()
            text = j["text"] if j["kind"] == "say" else " → ".join(json.loads(j["text"])) if j["kind"] == "steps" else j["text"]
            col = QVBoxLayout()
            col.setSpacing(2)
            t = QLabel(text[:80])
            t.setFont(dt.font(14, dt.QFont.Weight.Medium))
            col.addWidget(t)
            when = time.strftime("%a %I:%M %p", time.localtime(j["when"])).replace(" 0", " ")
            col.addWidget(self.hint_label(when + (f" · repeats {j['repeat']}" if j.get("repeat") else "")))
            row.addLayout(col, 1)
            cancel = GhostButton("Cancel")
            cancel.clicked.connect(lambda _c=False, jid=j["id"]: (scheduler.remove(jid), self._render_jobs()))
            row.addWidget(cancel)
            c.add_layout(row)

    def _render_catalog(self):
        from automation.catalog import CATALOG
        c = self._catalog
        for i, (cat, examples) in enumerate(CATALOG.items()):
            if i:
                c.add_widget(Divider())
            t = QLabel(cat)
            t.setFont(dt.font(14, dt.QFont.Weight.DemiBold))
            c.add_widget(t)
            body = QLabel("  ·  ".join(f"“{e}”" for e in examples))
            body.setWordWrap(True)
            body.setFont(dt.font(13))
            body.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
            c.add_widget(body)

    # ── actions ──────────────────────────────────────────────────────────
    def _say(self, text: str, ok: bool = True):
        self._status.setText(text)
        self._status.setStyleSheet(f"color: {(dt.SUCCESS if ok else dt.ERROR).name()};")

    def _save(self):
        import automation
        from automation import routines, scheduler
        from automation.nlp import parse_when
        name = self._name.text().strip()
        steps = [ln.strip() for ln in self._steps.toPlainText().splitlines() if ln.strip()]
        if not name or not steps:
            self._say("Give it a name and at least one command.", False)
            return
        bad = [s for s in steps if not automation.understands(s)]
        if bad:
            self._say(f"I don't know how to do: {bad[0]}. See the examples below.", False)
            return
        phrase = self._phrase.text().strip()
        routines.upsert(name, [routines._imperative(s) for s in steps], [phrase] if phrase else None)
        when = self._when.text().strip()
        if when:
            import re as _re
            mm = _re.search(r"(?:every|each)\s+(day|weekday|weekdays|morning|evening|\w+day)\s+(?:at\s+)?(.+)$", when, _re.I)
            t = parse_when("at " + (mm.group(2) if mm else when))
            if t:
                rep = "weekdays" if mm and mm.group(1).lower().startswith("weekday") else "daily"
                scheduler.add(t.timestamp(), "routine", name, rep)
        self._name.clear(); self._phrase.clear(); self._steps.clear(); self._when.clear()
        self._say(f"Saved {name}.", True)
        self.on_activate()

    def _run(self, name: str):
        import threading
        import automation
        from automation import routines
        mgr = getattr(self.window(), "manager", None)
        threading.Thread(target=lambda: routines.run(automation.Ctx(mgr), name), daemon=True).start()
        self._say(f"Running {name}…", True)

    def _delete(self, name: str):
        from automation import routines
        if QMessageBox.question(self, "Delete routine", f"Delete {name}?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) \
                == QMessageBox.StandardButton.Yes:
            routines.remove(name)
            self.on_activate()
