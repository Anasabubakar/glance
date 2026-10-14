// Glance Cursor — draws Glance's buddy inside GNOME Shell so it is ALWAYS above
// every window and workspace, never appears in the taskbar/alt-tab, and tracks
// the real pointer on the compositor's own frame clock.
//
// The Glance app drives it over D-Bus (name app.glance.Overlay). The buddy is
// shown while the app's bus name `app.glance.Companion` is present and hidden
// the moment it disappears (quit or crash), so it can never get stuck on screen.

import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import St from 'gi://St';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

import {Motion, FOLLOW} from './motion.js';

const IFACE = `<node>
  <interface name="app.glance.Overlay">
    <method name="SetMode"><arg type="s" direction="in" name="mode"/></method>
    <method name="SetAudioLevel"><arg type="d" direction="in" name="rms"/></method>
    <method name="PointAt">
      <arg type="d" direction="in" name="x"/><arg type="d" direction="in" name="y"/>
      <arg type="s" direction="in" name="label"/></method>
    <method name="SetSlowMode"><arg type="b" direction="in" name="on"/></method>
    <method name="SetPointHold"><arg type="b" direction="in" name="hold"/></method>
    <method name="ReleasePoint"/>
    <method name="HideCursor"/>
    <method name="AddArrow">
      <arg type="d" direction="in" name="x1"/><arg type="d" direction="in" name="y1"/>
      <arg type="d" direction="in" name="x2"/><arg type="d" direction="in" name="y2"/>
      <arg type="d" direction="in" name="ttl"/></method>
    <method name="AddCircle">
      <arg type="d" direction="in" name="x"/><arg type="d" direction="in" name="y"/>
      <arg type="d" direction="in" name="r"/><arg type="d" direction="in" name="ttl"/></method>
    <method name="AddUnderline">
      <arg type="d" direction="in" name="x"/><arg type="d" direction="in" name="y"/>
      <arg type="d" direction="in" name="w"/><arg type="d" direction="in" name="ttl"/></method>
    <method name="AddText">
      <arg type="d" direction="in" name="x"/><arg type="d" direction="in" name="y"/>
      <arg type="s" direction="in" name="text"/><arg type="d" direction="in" name="ttl"/></method>
    <method name="ClearAnnotations"/>
    <method name="SetHotkey"><arg type="s" direction="in" name="accel"/></method>
    <method name="GetState"><arg type="s" direction="out" name="json"/></method>
    <signal name="HotkeyPressed"/>
    <signal name="HotkeyReleased"/>
    <property name="Version" type="u" access="read"/>
  </interface>
</node>`;

const BLUE = '#3380FF';
const MARK = 28;                       // px, matches CURSOR_SIZE in overlay.py
const CLIENT_NAME = 'app.glance.Companion';

export default class GlanceCursor extends Extension {
    enable() {
        this._motion = new Motion();
        this._visible = false;
        this._shown = false;
        this._buildActors();

        this._timeline = new Clutter.Timeline({
            actor: this._root, duration: 1000, repeat_count: -1,
        });
        this._timeline.connect('new-frame', () => this._frame());

        this._dbus = Gio.DBusExportedObject.wrapJSObject(IFACE, this);
        this._dbus.export(Gio.DBus.session, '/app/glance/Overlay');
        this._ownId = Gio.bus_own_name_on_connection(
            Gio.DBus.session, 'app.glance.Overlay',
            Gio.BusNameOwnerFlags.NONE, null, null);
        this._watchId = Gio.bus_watch_name(
            Gio.BusType.SESSION, CLIENT_NAME, Gio.BusNameWatcherFlags.NONE,
            () => this._setShown(true), () => this._setShown(false));

        this._monitorsId = Main.layoutManager.connect(
            'monitors-changed', () => this._resize());
        this._resize();

        // Global push-to-talk: the compositor sees every key, which apps on
        // Wayland cannot. The app sends the combo via SetHotkey().
        this._action = 0;
        this._held = false;
        this._accelId = global.display.connect(
            'accelerator-activated', (_d, action) => {
                if (action === this._action) this._hotkeyDown();
            });
    }

    disable() {
        this._releaseHotkey(false);
        this._ungrab();
        if (this._accelId) global.display.disconnect(this._accelId);
        this._accelId = 0;
        if (this._monitorsId)
            Main.layoutManager.disconnect(this._monitorsId);
        if (this._watchId) Gio.bus_unwatch_name(this._watchId);
        if (this._ownId) Gio.bus_unown_name(this._ownId);
        this._dbus?.unexport();
        this._timeline?.stop();
        this._timeline = null;
        Main.layoutManager.removeChrome(this._root);
        this._root.destroy();
        this._root = null;
        this._motion = null;
        this._dbus = null;
    }

    // ── actors ────────────────────────────────────────────────────────────
    _buildActors() {
        // Full-stage, input-transparent container above all windows and
        // fullscreen apps; chrome is global, so it shows on every workspace.
        this._root = new St.Widget({reactive: false, name: 'glance-cursor-root'});
        Main.layoutManager.addTopChrome(this._root, {
            affectsInputRegion: false, affectsStruts: false, trackFullscreen: false,
        });
        this._root.hide();

        this._notes = new St.DrawingArea({reactive: false});
        this._notes.connect('repaint', a => this._paintNotes(a));
        this._root.add_child(this._notes);

        this._buddy = new St.Widget({reactive: false});   // origin = buddy centre
        this._root.add_child(this._buddy);

        const glow = (r, a) => `width:${r * 2}px;height:${r * 2}px;border-radius:${r}px;` +
            `background-color:rgba(51,128,255,${a});`;
        this._halo = new St.Widget({style: glow(MARK * 0.75, 0.22), reactive: false});
        this._halo.set_position(-MARK * 0.75, -MARK * 0.75);

        const png = GLib.build_filenamev([this.path, 'glance-cursor.png']);
        this._mark = new St.Widget({
            reactive: false,
            style: `width:${MARK}px;height:${MARK}px;border-radius:${MARK / 2}px;` +
                `background-image:url("file://${png}");background-size:${MARK}px ${MARK}px;` +
                `box-shadow:0 0 12px rgba(51,128,255,0.55);`,
        });
        this._mark.set_position(-MARK / 2, -MARK / 2);
        this._mark.set_pivot_point(0.5, 0.5);

        this._bars = [];
        for (let i = 0; i < 5; i++) {
            const b = new St.Widget({
                reactive: false,
                style: `width:2px;background-color:${BLUE};border-radius:1px;`,
            });
            this._bars.push(b);
        }

        this._spinner = new St.Widget({
            reactive: false,
            style: `width:11px;height:11px;border-radius:7px;border:2.5px solid ${BLUE};` +
                `border-top-color:transparent;box-shadow:0 0 8px rgba(51,128,255,0.5);`,
        });
        this._spinner.set_position(-7, -7);
        this._spinner.set_pivot_point(0.5, 0.5);

        this._bubble = new St.Label({
            reactive: false,
            style: `background-color:${BLUE};color:white;font-size:9pt;font-weight:500;` +
                `padding:4px 8px;border-radius:6px;box-shadow:0 0 8px rgba(51,128,255,0.45);`,
        });
        this._bubble.set_pivot_point(0, 0.5);

        for (const a of [this._halo, this._mark, this._spinner, ...this._bars, this._bubble])
            this._buddy.add_child(a);
    }

    _resize() {
        this._root.set_position(0, 0);
        this._root.set_size(global.stage.width, global.stage.height);
        this._notes.set_size(global.stage.width, global.stage.height);
    }

    _setShown(on) {
        this._shown = on;
        if (on) {
            this._root.show();
            this._timeline.start();
        } else {
            this._root.hide();
            this._timeline.stop();
        }
    }

    // ── frame loop (runs on the compositor frame clock) ───────────────────
    _frame() {
        const m = this._motion;
        const [px, py] = global.get_pointer();
        m.update(GLib.get_monotonic_time() / 1e6, px, py);

        this._buddy.set_position(Math.round(m.pos.x), Math.round(m.pos.y));

        const listening = m.mode === 'listening', thinking = m.mode === 'thinking';
        this._mark.visible = this._halo.visible = !listening && !thinking;
        this._spinner.visible = thinking;
        for (const b of this._bars) b.visible = listening;

        if (!listening && !thinking) {
            this._mark.set_scale(m.scale, m.scale);
            this._mark.rotation_angle_z = m.rotation;
        }
        if (thinking)
            this._spinner.rotation_angle_z = (m.spin * 180 / Math.PI * 2) % 360;
        if (listening) {
            const prof = [0.4, 0.7, 1.0, 0.7, 0.4], total = 5 * 2 + 4 * 2;
            this._bars.forEach((b, i) => {
                const ph = m.phase * 1.8 + i * 0.35;
                const h = 3 + m.audio * 10 * prof[i] + (Math.sin(ph) + 1) / 2 * 1.5;
                b.set_size(2, Math.max(2, h));
                b.set_position(-total / 2 + i * 4, -h / 2);
            });
        }

        const showBubble = m.locked && m.bubbleText;
        this._bubble.visible = !!showBubble;
        if (showBubble) {
            if (this._bubble.text !== m.bubbleText) this._bubble.text = m.bubbleText;
            this._bubble.set_position(10, 18 - this._bubble.height / 2);
            this._bubble.opacity = Math.round(255 * m.bubbleAlpha);
            const s = Math.max(0.01, m.bubbleScale);
            this._bubble.set_scale(s, s);
        }

        this._notes.visible = m.annotations.length > 0;
        if (m.annotations.length) this._notes.queue_repaint();
    }

    _paintNotes(area) {
        const cr = area.get_context();
        for (const a of this._motion.annotations) {
            cr.setSourceRGBA(0.2, 0.5, 1.0, 0.86 * this._motion.annotationAlpha(a));
            cr.setLineCap(1);                              // round
            if (a.kind === 'arrow') {
                const [x1, y1, x2, y2] = a.args;
                cr.setLineWidth(3);
                cr.moveTo(x1, y1); cr.lineTo(x2, y2); cr.stroke();
                const ang = Math.atan2(y2 - y1, x2 - x1);
                for (const s of [-1, 1]) {
                    cr.moveTo(x2, y2);
                    cr.lineTo(x2 - 14 * Math.cos(ang + s * 0.489),
                              y2 - 14 * Math.sin(ang + s * 0.489));
                    cr.stroke();
                }
            } else if (a.kind === 'circle') {
                const [x, y, r] = a.args;
                cr.setLineWidth(3);
                cr.arc(x, y, r, 0, 2 * Math.PI); cr.stroke();
            } else if (a.kind === 'underline') {
                const [x, y, w] = a.args;
                cr.setLineWidth(4);
                cr.moveTo(x, y); cr.lineTo(x + w, y); cr.stroke();
            } else if (a.kind === 'text') {
                const [x, y, text] = a.args;
                cr.selectFontFace('Sans', 0, 1);           // normal, bold
                cr.setFontSize(15);
                cr.moveTo(x, y); cr.showText(text);
            }
        }
        cr.$dispose();
    }


    // ── global hotkey (push-to-talk) ─────────────────────────────────────
    _ungrab() {
        if (this._action) {
            try {
                Main.wm.allowKeybinding(Meta.external_binding_name_for_action(this._action), Shell.ActionMode.NONE);
                global.display.ungrab_accelerator(this._action);
            } catch (e) { console.error('glance-cursor: ungrab failed', e); }
            this._action = 0;
        }
    }

    _sym(name) { return Clutter[`KEY_${name}`] ?? 0; }

    // "ctrl+alt+m" -> {accel: "<Control><Alt>m", mods: Set(keysyms), key: keysym}
    _parseCombo(spec) {
        const names = {ctrl: 'Control', control: 'Control', alt: 'Alt', shift: 'Shift',
                       win: 'Super', super: 'Super', cmd: 'Super'};
        const modSyms = {Control: ['Control_L', 'Control_R'], Alt: ['Alt_L', 'Alt_R', 'ISO_Level3_Shift'],
                         Shift: ['Shift_L', 'Shift_R'], Super: ['Super_L', 'Super_R']};
        const parts = spec.toLowerCase().split('+').map(p => p.trim()).filter(Boolean);
        let accel = '', syms = new Set(), mask = 0;
        for (const p of parts.slice(0, -1)) {
            const n = names[p];
            if (!n) return null;
            accel += `<${n}>`;
            for (const m of modSyms[n]) syms.add(this._sym(m));
        }
        const keyName = parts[parts.length - 1];
        if (!keyName) return null;
        accel += keyName;
        const cap = keyName[0].toUpperCase() + keyName.slice(1);
        for (const k of [keyName, keyName.toUpperCase(), cap]) {
            const v = this._sym(k);
            if (v) syms.add(v);
        }
        syms.delete(0);
        return {accel, syms, mods: parts.slice(0, -1).map(p => names[p])};
    }

    SetHotkey(spec) {
        try { this._setHotkey(spec); } catch (e) { console.error('glance-cursor: SetHotkey failed', e); }
    }

    _setHotkey(spec) {
        this._releaseHotkey(false);
        this._ungrab();
        if (!spec) return;
        const combo = this._parseCombo(spec);
        if (!combo) { console.error(`glance-cursor: bad hotkey '${spec}'`); return; }
        const action = global.display.grab_accelerator(combo.accel, Meta.KeyBindingFlags.IGNORE_AUTOREPEAT);
        if (action === Meta.KeyBindingFlags.NONE || action === 0) {
            console.error(`glance-cursor: could not grab '${combo.accel}' (already in use?)`);
            return;
        }
        this._action = action;
        this._combo = combo;
        Main.wm.allowKeybinding(Meta.external_binding_name_for_action(action),
            Shell.ActionMode.NORMAL | Shell.ActionMode.OVERVIEW);
    }

    _hotkeyDown() {
        if (!this._shown) return;
        // Auto-repeat is filtered out, so a second activation while held is a
        // deliberate second press: treat it as "stop" (the stage never reports
        // the release of a grabbed key, only of the modifiers).
        if (this._held) { this._releaseHotkey(true); return; }
        this._held = true;
        this._dbus.emit_signal('HotkeyPressed', null);
        const syms = this._combo.syms;
        // Release = any key of the combo goes up (seen on the stage) ...
        this._relEvent = global.stage.connect('captured-event', (_a, ev) => {
            if (ev.type() === Clutter.EventType.KEY_RELEASE && syms.has(ev.get_key_symbol()))
                this._releaseHotkey(true);
            return Clutter.EVENT_PROPAGATE;
        });
        // ... or, as a backstop, a required modifier is no longer down, or 90 s pass.
        const need = this._combo.mods.reduce((m, n) => m | ({
            Control: Clutter.ModifierType.CONTROL_MASK, Alt: Clutter.ModifierType.MOD1_MASK,
            Shift: Clutter.ModifierType.SHIFT_MASK, Super: Clutter.ModifierType.SUPER_MASK}[n] || 0), 0);
        const t0 = GLib.get_monotonic_time();
        this._relPoll = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 40, () => {
            const [, , mods] = global.get_pointer();
            if ((mods & need) !== need || GLib.get_monotonic_time() - t0 > 90e6) {
                this._relPoll = 0;
                this._releaseHotkey(true);
                return GLib.SOURCE_REMOVE;
            }
            return GLib.SOURCE_CONTINUE;
        });
    }

    _releaseHotkey(emit) {
        if (this._relEvent) { global.stage.disconnect(this._relEvent); this._relEvent = 0; }
        if (this._relPoll) { GLib.source_remove(this._relPoll); this._relPoll = 0; }
        if (this._held) {
            this._held = false;
            if (emit) this._dbus.emit_signal('HotkeyReleased', null);
        }
    }

    // ── D-Bus methods ─────────────────────────────────────────────────────
    SetMode(mode) { this._motion.setMode(mode); }
    SetAudioLevel(rms) { this._motion.setAudioLevel(rms); }
    PointAt(x, y, label) { this._motion.pointAt(x, y, label); }
    SetSlowMode(on) { this._motion.setSlowMode(on); }
    SetPointHold(hold) { this._motion.setPointHold(hold); }
    ReleasePoint() { this._motion.releasePoint(); }
    HideCursor() { this._motion.hideCursor(); }
    AddArrow(x1, y1, x2, y2, ttl) { this._motion.addAnnotation('arrow', [x1, y1, x2, y2], ttl); }
    AddCircle(x, y, r, ttl) { this._motion.addAnnotation('circle', [x, y, r], ttl); }
    AddUnderline(x, y, w, ttl) { this._motion.addAnnotation('underline', [x, y, w], ttl); }
    AddText(x, y, text, ttl) { this._motion.addAnnotation('text', [x, y, text], ttl); }
    ClearAnnotations() { this._motion.clearAnnotations(); }

    GetState() {
        const m = this._motion;
        const [px, py] = global.get_pointer();
        return JSON.stringify({
            shown: this._shown, visible: this._root.visible, mode: m.mode,
            flight: m.flight, pos: m.pos, pointer: {x: px, y: py},
            notes: m.annotations.length, follow: m.flight === FOLLOW,
            stage: {w: global.stage.width, h: global.stage.height},
        });
    }

    get Version() { return 1; }
}
