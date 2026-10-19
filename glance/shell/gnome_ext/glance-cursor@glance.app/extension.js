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
    <method name="Screenshot">
      <arg type="s" direction="in" name="path"/><arg type="s" direction="out" name="json"/></method>
    <method name="MoveTo"><arg type="d" direction="in" name="x"/><arg type="d" direction="in" name="y"/></method>
    <method name="Click">
      <arg type="d" direction="in" name="x"/><arg type="d" direction="in" name="y"/>
      <arg type="i" direction="in" name="button"/><arg type="i" direction="in" name="count"/></method>
    <method name="Scroll">
      <arg type="d" direction="in" name="x"/><arg type="d" direction="in" name="y"/>
      <arg type="i" direction="in" name="dy"/></method>
    <method name="TypeText"><arg type="s" direction="in" name="text"/></method>
    <method name="Key"><arg type="s" direction="in" name="combo"/></method>
    <method name="Drag">
      <arg type="d" direction="in" name="x1"/><arg type="d" direction="in" name="y1"/>
      <arg type="d" direction="in" name="x2"/><arg type="d" direction="in" name="y2"/>
      <arg type="i" direction="in" name="button"/><arg type="i" direction="in" name="ms"/></method>
    <method name="DragPath">
      <arg type="s" direction="in" name="points"/><arg type="i" direction="in" name="button"/>
      <arg type="i" direction="in" name="ms"/></method>
    <method name="ClickWith">
      <arg type="d" direction="in" name="x"/><arg type="d" direction="in" name="y"/>
      <arg type="i" direction="in" name="button"/><arg type="i" direction="in" name="count"/>
      <arg type="s" direction="in" name="mods"/></method>
    <method name="GetState"><arg type="s" direction="out" name="json"/></method>
    <method name="GetWindows"><arg type="s" direction="out" name="json"/></method>
    <method name="WindowAction">
      <arg type="s" direction="in" name="which"/><arg type="s" direction="in" name="action"/>
      <arg type="s" direction="out" name="json"/></method>
    <method name="GetClipboard"><arg type="s" direction="in" name="kind"/><arg type="s" direction="out" name="text"/></method>
    <method name="SetClipboard"><arg type="s" direction="in" name="text"/></method>
    <method name="SwitchWorkspace"><arg type="i" direction="in" name="index"/></method>
    <method name="MoveWindowToWorkspace">
      <arg type="s" direction="in" name="which"/><arg type="i" direction="in" name="index"/>
      <arg type="s" direction="out" name="json"/></method>
    <method name="GetWorkspaces"><arg type="s" direction="out" name="json"/></method>
    <method name="SetStopGrab"><arg type="b" direction="in" name="on"/></method>
    <method name="SetRecording"><arg type="b" direction="in" name="on"/></method>
    <signal name="HotkeyPressed"/>
    <signal name="HotkeyReleased"/>
    <signal name="StopPressed"/>
    <signal name="InputEvent"><arg type="s" name="json"/></signal>
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
        this._stopAction = 0;
        this._accelId = global.display.connect(
            'accelerator-activated', (_d, action) => {
                if (action === this._action) this._hotkeyDown();
                else if (this._stopAction && action === this._stopAction)
                    this._dbus.emit_signal('StopPressed', null);
            });
        // Remember the last window that is not Glance's own, so "minimize this window"
        // means the window the user was working in, not Glance's panel.
        this._lastFocus = null;
        this._focusId = global.display.connect('notify::focus-window', () => this._noteFocus());
        this._noteFocus();
        // Create the virtual keyboard now: the first keys sent through a device created
        // at the moment of use were being dropped (the first typed text went missing).
        try { this._keyboard(); this._pointer(); } catch (e) { console.error('glance-cursor: input warm-up failed', e); }
    }

    disable() {
        this._releaseHotkey(false);
        this._ungrab();
        this.SetStopGrab(false);
        this.SetRecording(false);
        if (this._focusId) global.display.disconnect(this._focusId);
        this._focusId = 0;
        this._vptr = this._vkbd = this._vptrMain = null;
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


    // ── screen capture + input injection (Wayland apps can do neither) ───
    // Capture the whole stage without our own overlay in it. Async D-Bus method:
    // the reply is sent from ScreenshotAsync once the PNG has been written.
    ScreenshotAsync(params, invocation) {
        const [path] = params;
        const reply = obj => invocation.return_value(new GLib.Variant('(s)', [JSON.stringify(obj)]));
        try {
            const mons = Main.layoutManager.monitors.map(m => ({
                x: m.x, y: m.y, w: m.width, h: m.height,
                scale: m.geometry_scale ?? 1, primary: m === Main.layoutManager.primaryMonitor,
            }));
            this._root.hide();                     // keep the buddy out of the shot
            const out = Gio.File.new_for_path(path).replace(null, false, Gio.FileCreateFlags.NONE, null);
            // Wait one frame so the hidden overlay is really gone before capturing.
            GLib.timeout_add(GLib.PRIORITY_DEFAULT, 50, () => {
                const ss = new Shell.Screenshot();
                ss.screenshot(false, out, (o, res) => {
                    let ok = true, err = '';
                    try { o.screenshot_finish(res); } catch (e) { ok = false; err = `${e}`; }
                    try { out.close(null); } catch (_e) { /* ignore */ }
                    if (this._shown) this._root.show();
                    reply({ok, err, path, stage: {w: global.stage.width, h: global.stage.height}, monitors: mons});
                });
                return GLib.SOURCE_REMOVE;
            });
        } catch (e) {
            if (this._shown) this._root.show();
            reply({ok: false, err: `${e}`});
        }
    }

    // A fresh virtual pointer per action: a long-lived one stops delivering
    // after its first burst of events on GNOME 46. Kept alive briefly so queued
    // events are flushed before it is released.
    // One long-lived virtual pointer: a device created at the moment of use drops its first
    // events (the first drawing stroke or click after startup was lost), so it is made
    // at enable() and reused.
    _pointer(_keepMs) {
        return this._vptrMain ??= Clutter.get_default_backend().get_default_seat()
            .create_virtual_device(Clutter.InputDeviceType.POINTER_DEVICE);
    }

    _keyboard() {
        return this._vkbd ??= Clutter.get_default_backend().get_default_seat()
            .create_virtual_device(Clutter.InputDeviceType.KEYBOARD_DEVICE);
    }

    _t() { return GLib.get_monotonic_time(); }

    MoveTo(x, y) {
        try { this._pointer().notify_absolute_motion(this._t(), x, y); }
        catch (e) { console.error('glance-cursor: MoveTo failed', e); }
    }

    // Run steps spaced by `ms` so the compositor sees distinct, ordered events
    // (motion, press and release in one instant is not delivered reliably).
    _seq(steps, ms = 40) {
        let i = 0;
        const next = () => {
            if (i >= steps.length) return GLib.SOURCE_REMOVE;
            try { steps[i++](); } catch (e) { console.error('glance-cursor: input step failed', e); }
            return i < steps.length ? GLib.SOURCE_CONTINUE : GLib.SOURCE_REMOVE;
        };
        next();
        if (i < steps.length) GLib.timeout_add(GLib.PRIORITY_DEFAULT, ms, next);
    }

    Click(x, y, button, count) {
        const p = this._pointer();
        const b = {1: Clutter.BUTTON_PRIMARY, 2: Clutter.BUTTON_MIDDLE, 3: Clutter.BUTTON_SECONDARY}[button] ?? Clutter.BUTTON_PRIMARY;
        const steps = [() => p.notify_absolute_motion(this._t(), x, y)];
        for (let i = 0; i < Math.max(1, count); i++) {
            steps.push(() => p.notify_button(this._t(), b, Clutter.ButtonState.PRESSED));
            steps.push(() => p.notify_button(this._t(), b, Clutter.ButtonState.RELEASED));
        }
        this._seq(steps);
    }

    Scroll(x, y, dy) {
        const p = this._pointer();
        const dir = dy > 0 ? Clutter.ScrollDirection.UP : Clutter.ScrollDirection.DOWN;
        const steps = [() => p.notify_absolute_motion(this._t(), x, y)];
        for (let i = 0; i < Math.abs(dy); i++)
            steps.push(() => this._scrollOnce(p, dir));
        this._seq(steps);
    }

    // GNOME 46 takes (time, direction, source); newer shells add finish flags.
    _scrollOnce(p, dir) {
        try {
            p.notify_discrete_scroll(this._t(), dir, Clutter.ScrollSource.WHEEL);
        } catch (_e) {
            p.notify_discrete_scroll(this._t(), dir, Clutter.ScrollSource.WHEEL, Clutter.ScrollFinishFlags.NONE);
        }
    }

    _tap(sym) {
        const k = this._keyboard();
        k.notify_keyval(this._t(), sym, Clutter.KeyState.PRESSED);
        k.notify_keyval(this._t(), sym, Clutter.KeyState.RELEASED);
    }

    TypeText(text) {
        try {
            const k = this._keyboard();
            const steps = [];
            for (const ch of text) {
                const cp = ch.codePointAt(0);
                const sym = ch === '\n' ? Clutter.KEY_Return : ch === '\t' ? Clutter.KEY_Tab
                    : Clutter.unicode_to_keysym(cp);
                if (!sym) continue;
                steps.push(() => k.notify_keyval(this._t(), sym, Clutter.KeyState.PRESSED));
                steps.push(() => k.notify_keyval(this._t(), sym, Clutter.KeyState.RELEASED));
            }
            this._seq(steps, 7);          // ~3.5 ms per event keeps order and drops nothing
        } catch (e) { console.error('glance-cursor: TypeText failed', e); }
    }

    // ── drag, drag and drop, drawing ─────────────────────────────────────
    _button(b) {
        return {1: Clutter.BUTTON_PRIMARY, 2: Clutter.BUTTON_MIDDLE, 3: Clutter.BUTTON_SECONDARY}[b] ?? Clutter.BUTTON_PRIMARY;
    }

    // Walk a polyline with the button held. Points are inserted so no step is > 10 px
    // (apps ignore a drag that jumps), and the whole gesture takes about `ms`.
    _dragAlong(pts, button, ms) {
        if (!pts || pts.length < 2) return;
        const path = [pts[0]];
        for (let i = 1; i < pts.length; i++) {
            const [x0, y0] = pts[i - 1], [x1, y1] = pts[i];
            const n = Math.max(1, Math.ceil(Math.hypot(x1 - x0, y1 - y0) / 10));
            for (let j = 1; j <= n; j++) path.push([x0 + (x1 - x0) * j / n, y0 + (y1 - y0) * j / n]);
        }
        const total = Math.max(300, Math.min(ms || 700, 20000));
        const stepMs = Math.max(4, Math.min(40, Math.floor(total / path.length)));
        const p = this._pointer(total + path.length * stepMs + 2000);
        const b = this._button(button);
        // Let the window under the pointer receive "enter" (about 150 ms) before pressing,
        // and hold briefly after the press, or toolkits like GTK4 ignore the gesture.
        const settle = Math.ceil(150 / stepMs), hold = Math.ceil(70 / stepMs);
        const steps = [() => p.notify_absolute_motion(this._t(), path[0][0], path[0][1])];
        for (let i = 0; i < settle; i++) steps.push(() => {});
        steps.push(() => p.notify_button(this._t(), b, Clutter.ButtonState.PRESSED));
        for (let i = 0; i < hold; i++) steps.push(() => {});
        for (let i = 1; i < path.length; i++)
            steps.push(() => p.notify_absolute_motion(this._t(), path[i][0], path[i][1]));
        steps.push(() => {});
        steps.push(() => p.notify_button(this._t(), b, Clutter.ButtonState.RELEASED));
        this._seq(steps, stepMs);
    }

    Drag(x1, y1, x2, y2, button, ms) {
        try { this._dragAlong([[x1, y1], [x2, y2]], button, ms); }
        catch (e) { console.error('glance-cursor: Drag failed', e); }
    }

    DragPath(points, button, ms) {
        try { this._dragAlong(JSON.parse(points), button, ms); }
        catch (e) { console.error('glance-cursor: DragPath failed', e); }
    }

    // click with modifier keys held ("ctrl", "shift", "alt", "super"), e.g. ctrl+click
    ClickWith(x, y, button, count, mods) {
        try {
            const names = {ctrl: 'Control_L', control: 'Control_L', shift: 'Shift_L', alt: 'Alt_L',
                super: 'Super_L', win: 'Super_L', meta: 'Super_L'};
            const held = String(mods || '').toLowerCase().split(/[+,\s]+/).map(m => this._sym(names[m] ?? '')).filter(Boolean);
            const k = this._keyboard();
            const p = this._pointer(2500);
            const b = this._button(button);
            const steps = [() => held.forEach(m => k.notify_keyval(this._t(), m, Clutter.KeyState.PRESSED)),
                           () => p.notify_absolute_motion(this._t(), x, y)];
            for (let i = 0; i < Math.max(1, count); i++) {
                steps.push(() => p.notify_button(this._t(), b, Clutter.ButtonState.PRESSED));
                steps.push(() => p.notify_button(this._t(), b, Clutter.ButtonState.RELEASED));
            }
            steps.push(() => held.slice().reverse().forEach(m => k.notify_keyval(this._t(), m, Clutter.KeyState.RELEASED)));
            this._seq(steps, 45);
        } catch (e) { console.error('glance-cursor: ClickWith failed', e); }
    }

    // "ctrl+shift+t", "enter", "alt+tab", "super"
    Key(combo) {
        try {
            const named = {enter: 'Return', return: 'Return', tab: 'Tab', esc: 'Escape', escape: 'Escape',
                space: 'space', backspace: 'BackSpace', delete: 'Delete', del: 'Delete', up: 'Up', down: 'Down',
                left: 'Left', right: 'Right', home: 'Home', end: 'End', pageup: 'Page_Up', pagedown: 'Page_Down'};
            const mods = {ctrl: 'Control_L', control: 'Control_L', alt: 'Alt_L', shift: 'Shift_L',
                super: 'Super_L', win: 'Super_L', cmd: 'Super_L', meta: 'Super_L'};
            const parts = String(combo).toLowerCase().split('+').map(p => p.trim()).filter(Boolean);
            if (!parts.length) return;
            const held = parts.slice(0, -1).map(p => this._sym(mods[p] ?? '')).filter(Boolean);
            const last = parts[parts.length - 1];
            const sym = this._sym(named[last] ?? mods[last] ?? (last.length === 1 ? last : last[0].toUpperCase() + last.slice(1)));
            if (!sym) return;
            const k = this._keyboard();
            for (const m of held) k.notify_keyval(this._t(), m, Clutter.KeyState.PRESSED);
            this._tap(sym);
            for (const m of held.reverse()) k.notify_keyval(this._t(), m, Clutter.KeyState.RELEASED);
        } catch (e) { console.error('glance-cursor: Key failed', e); }
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

    // ── windows (reliable, instant window control) ───────────────────────
    _isGlance(w) {
        const c = (w.get_wm_class() || '').toLowerCase();
        const a = (w.get_gtk_application_id() || '').toLowerCase();
        return c.includes('glance') || a.includes('glance');
    }

    _noteFocus() {
        const w = global.display.focus_window;
        if (w && !this._isGlance(w) && w.get_window_type() === Meta.WindowType.NORMAL)
            this._lastFocus = w;
    }

    _normalWindows() {
        return global.get_window_actors().map(a => a.meta_window).filter(w =>
            w && !w.is_skip_taskbar() &&
            [Meta.WindowType.NORMAL, Meta.WindowType.DIALOG, Meta.WindowType.MODAL_DIALOG]
                .includes(w.get_window_type()));
    }

    _isMaximized(w) {
        try { if (typeof w.is_maximized === 'function') return w.is_maximized(); } catch (_e) { /* old API */ }
        try { return w.get_maximized() === Meta.MaximizeFlags.BOTH; } catch (_e) { return false; }
    }

    _describe(w) {
        const r = w.get_frame_rect();
        const target = this._lastFocus ?? global.display.focus_window;
        return {
            id: w.get_id(), title: w.get_title() || '', wm_class: w.get_wm_class() || '',
            app: w.get_gtk_application_id() || '', x: r.x, y: r.y, w: r.width, h: r.height,
            focused: w === target, minimized: !!w.minimized, maximized: this._isMaximized(w),
            workspace: w.get_workspace()?.index() ?? -1, glance: this._isGlance(w),
        };
    }

    GetWindows() {
        try { return JSON.stringify(this._normalWindows().map(w => this._describe(w))); }
        catch (e) { return JSON.stringify([]); }
    }

    _findWindow(which) {
        if (!which || which === 'focused') {
            const f = this._lastFocus ?? global.display.focus_window;
            if (f && !f.minimized) return f;
            // nothing focused: the topmost visible normal window
            const vis = this._normalWindows().filter(w => !w.minimized && !this._isGlance(w));
            return vis.length ? vis[vis.length - 1] : null;
        }
        const ws = this._normalWindows();
        if (which.startsWith('title:') || which.startsWith('class:')) {
            const q = which.slice(which.indexOf(':') + 1).toLowerCase();
            const key = which.startsWith('title:') ? w => w.get_title() : w => w.get_wm_class();
            return ws.find(w => (key(w) || '').toLowerCase().includes(q)) ?? null;
        }
        const id = Number(which);
        return ws.find(w => w.get_id() === id) ?? null;
    }

    WindowAction(which, action) {
        try {
            const w = this._findWindow(which);
            if (!w) return JSON.stringify({ok: false, err: 'no such window'});
            const before = this._describe(w);
            switch (action) {
            case 'minimize': w.minimize(); break;
            case 'unminimize': w.unminimize(); break;
            case 'maximize':
                try { w.maximize(Meta.MaximizeFlags.BOTH); } catch (_e) { w.maximize(); } break;
            case 'unmaximize':
                try { w.unmaximize(Meta.MaximizeFlags.BOTH); } catch (_e) { w.unmaximize(); } break;
            case 'fullscreen': w.make_fullscreen(); break;
            case 'unfullscreen': w.unmake_fullscreen(); break;
            case 'close': w.delete(global.get_current_time()); break;
            case 'above': w.make_above(); break;
            case 'unabove': w.unmake_above(); break;
            case 'stick': w.stick(); break;
            case 'unstick': w.unstick(); break;
            case 'tile_left': case 'tile_right': case 'tile_top': case 'tile_bottom':
            case 'tile_center': case 'tile_topleft': case 'tile_topright':
            case 'tile_bottomleft': case 'tile_bottomright': {
                try { w.unmaximize(Meta.MaximizeFlags.BOTH); } catch (_e) { try { w.unmaximize(); } catch (_e2) { /* already */ } }
                const area = w.get_work_area_current_monitor();
                const hw = Math.floor(area.width / 2), hh = Math.floor(area.height / 2);
                const g = {
                    tile_left: [area.x, area.y, hw, area.height],
                    tile_right: [area.x + hw, area.y, area.width - hw, area.height],
                    tile_top: [area.x, area.y, area.width, hh],
                    tile_bottom: [area.x, area.y + hh, area.width, area.height - hh],
                    tile_topleft: [area.x, area.y, hw, hh],
                    tile_topright: [area.x + hw, area.y, area.width - hw, hh],
                    tile_bottomleft: [area.x, area.y + hh, hw, area.height - hh],
                    tile_bottomright: [area.x + hw, area.y + hh, area.width - hw, area.height - hh],
                    tile_center: [area.x + Math.floor(area.width * 0.15), area.y + Math.floor(area.height * 0.1),
                                  Math.floor(area.width * 0.7), Math.floor(area.height * 0.8)],
                }[action];
                w.move_resize_frame(true, g[0], g[1], g[2], g[3]);
                break;
            }
            case 'activate': Main.activateWindow(w); break;
            default: return JSON.stringify({ok: false, err: `unknown action ${action}`});
            }
            return JSON.stringify({ok: true, window: before});
        } catch (e) {
            console.error('glance-cursor: WindowAction failed', e);
            return JSON.stringify({ok: false, err: String(e)});
        }
    }

    // ── clipboard and workspaces (done in the compositor: exact, instant) ─
    GetClipboardAsync(params, invocation) {
        try {
            const kind = String(params[0]) === 'primary' ? St.ClipboardType.PRIMARY : St.ClipboardType.CLIPBOARD;
            St.Clipboard.get_default().get_text(kind, (_c, text) => {
                invocation.return_value(GLib.Variant.new('(s)', [text ?? '']));
            });
        } catch (e) {
            invocation.return_value(GLib.Variant.new('(s)', ['']));
        }
    }

    SetClipboard(text) {
        try { St.Clipboard.get_default().set_text(St.ClipboardType.CLIPBOARD, text); }
        catch (e) { console.error('glance-cursor: SetClipboard failed', e); }
    }

    SwitchWorkspace(index) {
        try {
            const wm = global.workspace_manager;
            const n = wm.get_n_workspaces();
            const i = Math.max(0, Math.min(n - 1, index));
            wm.get_workspace_by_index(i).activate(global.get_current_time());
        } catch (e) { console.error('glance-cursor: SwitchWorkspace failed', e); }
    }

    MoveWindowToWorkspace(which, index) {
        try {
            const w = this._findWindow(which);
            if (!w) return JSON.stringify({ok: false, err: 'no such window'});
            const n = global.workspace_manager.get_n_workspaces();
            w.change_workspace_by_index(Math.max(0, Math.min(n - 1, index)), false);
            return JSON.stringify({ok: true});
        } catch (e) { return JSON.stringify({ok: false, err: String(e)}); }
    }

    GetWorkspaces() {
        const wm = global.workspace_manager;
        return JSON.stringify({count: wm.get_n_workspaces(), current: wm.get_active_workspace_index()});
    }

    // ── stop key: Escape is only grabbed while Glance is acting ──────────
    SetStopGrab(on) {
        try {
            if (on && !this._stopAction) {
                const a = global.display.grab_accelerator('Escape', Meta.KeyBindingFlags.NONE);
                if (a && a !== Meta.KeyBindingFlags.NONE) {
                    this._stopAction = a;
                    Main.wm.allowKeybinding(Meta.external_binding_name_for_action(a),
                        Shell.ActionMode.NORMAL | Shell.ActionMode.OVERVIEW);
                }
            } else if (!on && this._stopAction) {
                Main.wm.allowKeybinding(Meta.external_binding_name_for_action(this._stopAction),
                    Shell.ActionMode.NONE);
                global.display.ungrab_accelerator(this._stopAction);
                this._stopAction = 0;
            }
        } catch (e) { console.error('glance-cursor: SetStopGrab failed', e); }
    }

    // ── input recording (workflow capture): every click/key the user makes ─
    SetRecording(on) {
        try {
            if (on && !this._recId) {
                this._recId = global.stage.connect('captured-event', (_a, ev) => {
                    const t = ev.type();
                    let o = null;
                    if (t === Clutter.EventType.BUTTON_PRESS) {
                        const [x, y] = ev.get_coords();
                        this._lastClickT = Date.now();
                        o = {kind: 'click', x: Math.round(x), y: Math.round(y), button: ev.get_button()};
                    } else if (t === Clutter.EventType.KEY_PRESS) {
                        let ch = '';
                        try {
                            const u = ev.get_key_unicode();
                            ch = typeof u === 'number' ? (u > 31 ? String.fromCodePoint(u) : '') : String(u ?? '');
                        } catch (_e) { ch = ''; }
                        o = {kind: 'key', key: Clutter.keyval_name(ev.get_key_symbol()) || '',
                             char: ch, mods: ev.get_state()};
                    } else if (t === Clutter.EventType.SCROLL) {
                        const [x, y] = ev.get_coords();
                        o = {kind: 'scroll', x: Math.round(x), y: Math.round(y)};
                    }
                    if (o) {
                        const w = this._lastFocus ?? global.display.focus_window;
                        o.window = w ? (w.get_title() || '') : '';
                        o.t = Date.now();
                        this._dbus.emit_signal('InputEvent', GLib.Variant.new('(s)', [JSON.stringify(o)]));
                    }
                    return Clutter.EVENT_PROPAGATE;
                });
                // Backstop: with several client windows open the stage did not always report
                // clicks, so also watch the pointer's button state (works for every window).
                this._btnPrev = 0;
                this._pollId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 20, () => {
                    const [x, y, mods] = global.get_pointer();
                    const m = mods & (Clutter.ModifierType.BUTTON1_MASK | Clutter.ModifierType.BUTTON2_MASK |
                                      Clutter.ModifierType.BUTTON3_MASK);
                    const pressed = m & ~this._btnPrev;
                    this._btnPrev = m;
                    if (pressed && Date.now() - (this._lastClickT ?? 0) > 150) {
                        const button = (pressed & Clutter.ModifierType.BUTTON1_MASK) ? 1
                            : (pressed & Clutter.ModifierType.BUTTON3_MASK) ? 3 : 2;
                        const w = this._lastFocus ?? global.display.focus_window;
                        const o = {kind: 'click', x: Math.round(x), y: Math.round(y), button,
                                   window: w ? (w.get_title() || '') : '', t: Date.now()};
                        this._dbus.emit_signal('InputEvent', GLib.Variant.new('(s)', [JSON.stringify(o)]));
                    }
                    return this._pollId ? GLib.SOURCE_CONTINUE : GLib.SOURCE_REMOVE;
                });
            } else if (!on && this._recId) {
                global.stage.disconnect(this._recId);
                this._recId = 0;
                if (this._pollId) { GLib.source_remove(this._pollId); this._pollId = 0; }
            }
        } catch (e) { console.error('glance-cursor: SetRecording failed', e); }
    }

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

    get Version() { return 4; }
}
