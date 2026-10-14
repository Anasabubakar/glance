# Glance Cursor (GNOME Shell extension)

Draws Glance's buddy cursor inside GNOME Shell so it stays **above every window
and workspace**, never appears in the taskbar/alt-tab, and follows the pointer on
the compositor's frame clock. Ordinary app windows can't do this on GNOME/Wayland.

- Glance installs it to `~/.local/share/gnome-shell/extensions/` on first run
  (see `ui/overlay_backend.py`). GNOME on Wayland loads new extensions at the next
  login; until then Glance uses its normal overlay window.
- The buddy shows only while Glance owns the D-Bus name `app.glance.Companion`,
  so it disappears the moment Glance quits or crashes.
- Control API: `app.glance.Overlay` at `/app/glance/Overlay` (see `extension.js`).
- `motion.js` is pure (no GNOME imports); test it with `node motion.test.mjs`.
- Supports GNOME Shell 45–49. Force the old window overlay with `GLANCE_OVERLAY=qt`.
