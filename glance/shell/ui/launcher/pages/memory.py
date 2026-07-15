"""Memory page — facts + skills CRUD, import/export."""

from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QFileDialog, QMessageBox,
)
from PyQt6.QtCore import Qt
import json

from ..page_base import BasePage
from ..widgets import Card, FlatButton, DangerButton, GradientButton
from .. import design_tokens as dt


class MemoryPage(BasePage):
    title = "Memory"
    icon = "\U0001F4AD"
    subtitle = "Manage facts and skills Glance has learned."

    def __init__(self, parent=None):
        super().__init__(parent)
        self._store = None
        try:
            from memory_store import MemoryStore
            self._store = MemoryStore()
        except Exception:
            pass

        # ── Facts ────────────────────────────────────────────────────
        self.body_layout.addWidget(self.section_label("Facts"))

        add_row = QHBoxLayout()
        self._fact_input = QLineEdit()
        self._fact_input.setPlaceholderText("Add a fact…")
        self._fact_input.setStyleSheet(f"""
            QLineEdit {{
                background: {dt.BG_ELEVATED.name()};
                color: {dt.TEXT_PRIMARY.name()};
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 6px; padding: 8px 10px;
            }}
            QLineEdit:focus {{ border-color: {dt.BRAND_INDIGO.name()}; }}
        """)
        self._fact_input.returnPressed.connect(self._add_fact)
        add_row.addWidget(self._fact_input, 1)
        add_btn = FlatButton("Add")
        add_btn.clicked.connect(self._add_fact)
        add_row.addWidget(add_btn)
        self.body_layout.addLayout(add_row)

        self._facts_container = QVBoxLayout()
        self._facts_container.setSpacing(4)
        self.body_layout.addLayout(self._facts_container)

        # ── Skills ───────────────────────────────────────────────────
        self.body_layout.addWidget(self.section_label("Skills"))

        skill_add = QHBoxLayout()
        self._skill_name = QLineEdit()
        self._skill_name.setPlaceholderText("Skill name")
        self._skill_name.setStyleSheet(self._fact_input.styleSheet())
        skill_add.addWidget(self._skill_name)
        self._skill_steps = QLineEdit()
        self._skill_steps.setPlaceholderText("Steps")
        self._skill_steps.setStyleSheet(self._fact_input.styleSheet())
        skill_add.addWidget(self._skill_steps, 1)
        skill_btn = FlatButton("Add")
        skill_btn.clicked.connect(self._add_skill)
        skill_add.addWidget(skill_btn)
        self.body_layout.addLayout(skill_add)

        self._skills_container = QVBoxLayout()
        self._skills_container.setSpacing(4)
        self.body_layout.addLayout(self._skills_container)

        # ── Import / Export ──────────────────────────────────────────
        io_row = QHBoxLayout()
        exp_btn = FlatButton("Export")
        exp_btn.clicked.connect(self._export)
        io_row.addWidget(exp_btn)
        imp_btn = FlatButton("Import")
        imp_btn.clicked.connect(self._import)
        io_row.addWidget(imp_btn)
        io_row.addStretch()
        self.body_layout.addLayout(io_row)

        self.body_layout.addStretch()

    def on_activate(self):
        if self._store:
            self._store._load()
        self._refresh_facts()
        self._refresh_skills()

    def _refresh_facts(self):
        while self._facts_container.count():
            item = self._facts_container.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if not self._store or not self._store.facts:
            lbl = QLabel("No facts stored.")
            lbl.setFont(dt.FONT_CAPTION)
            lbl.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
            self._facts_container.addWidget(lbl)
            return

        for i, fact in enumerate(self._store.facts):
            text = fact.get("text", str(fact)) if isinstance(fact, dict) else str(fact)
            row_w = QWidget()
            row = QHBoxLayout(row_w)
            row.setContentsMargins(0, 2, 0, 2)
            lbl = QLabel(f"•  {text}")
            lbl.setFont(dt.FONT_BODY)
            lbl.setStyleSheet(f"color: {dt.TEXT_PRIMARY.name()};")
            lbl.setWordWrap(True)
            row.addWidget(lbl, 1)
            del_btn = DangerButton("×")
            del_btn.setFixedSize(28, 28)
            del_btn.clicked.connect(lambda _c=False, t=text: self._remove_fact(t))
            row.addWidget(del_btn)
            self._facts_container.addWidget(row_w)

    def _refresh_skills(self):
        while self._skills_container.count():
            item = self._skills_container.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if not self._store or not self._store.skills:
            lbl = QLabel("No skills learned.")
            lbl.setFont(dt.FONT_CAPTION)
            lbl.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
            self._skills_container.addWidget(lbl)
            return

        for name, info in self._store.skills.items():
            card = Card()
            row = QHBoxLayout()
            lbl = QLabel(name)
            lbl.setFont(dt.font(13, dt.QFont.Weight.DemiBold))
            lbl.setStyleSheet(f"color: {dt.TEXT_PRIMARY.name()};")
            row.addWidget(lbl, 1)
            del_btn = DangerButton("Remove")
            del_btn.setFixedWidth(80)
            del_btn.clicked.connect(lambda _c=False, n=name: self._remove_skill(n))
            row.addWidget(del_btn)
            card.add_layout(row)

            steps = info.get("steps", "") if isinstance(info, dict) else str(info)
            if steps:
                d = QLabel(steps)
                d.setFont(dt.FONT_CAPTION)
                d.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
                d.setWordWrap(True)
                card.add_widget(d)
            self._skills_container.addWidget(card)

    def _add_fact(self):
        text = self._fact_input.text().strip()
        if not text or not self._store:
            return
        self._store.add_fact(text)
        self._store.save()
        self._fact_input.clear()
        self._refresh_facts()

    def _remove_fact(self, text: str):
        if not self._store:
            return
        reply = QMessageBox.question(
            self, "Remove Fact",
            f"Remove this fact?\n\n{text[:120]}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._store.forget(text)
            self._store.save()
            self._refresh_facts()

    def _add_skill(self):
        name = self._skill_name.text().strip()
        steps = self._skill_steps.text().strip()
        if not name or not steps or not self._store:
            return
        self._store.add_skill(name, steps)
        self._store.save()
        self._skill_name.clear()
        self._skill_steps.clear()
        self._refresh_skills()

    def _remove_skill(self, name: str):
        if not self._store:
            return
        reply = QMessageBox.question(
            self, "Remove Skill",
            f"Remove the skill '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._store.remove_skill(name)
            self._store.save()
            self._refresh_skills()

    def _export(self):
        if not self._store:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Memory", "glance_memory.json", "JSON (*.json)"
        )
        if path:
            try:
                import shutil
                shutil.copy2(str(self._store.path), path)
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

    def _import(self):
        if not self._store:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Memory", "", "JSON (*.json)"
        )
        if path:
            try:
                with open(path) as f:
                    data = json.load(f)
                if "facts" in data:
                    for fact in data["facts"]:
                        text = fact.get("text", str(fact)) if isinstance(fact, dict) else str(fact)
                        self._store.add_fact(text)
                if "skills" in data:
                    for name, info in data["skills"].items():
                        steps = info.get("steps", str(info)) if isinstance(info, dict) else str(info)
                        self._store.add_skill(name, steps)
                self._store.save()
                self.on_activate()
            except Exception as e:
                QMessageBox.warning(self, "Import Error", str(e))
