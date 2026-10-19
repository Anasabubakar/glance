sleep 4
O="gdbus call --session -d app.glance.Overlay -o /app/glance/Overlay -m app.glance.Overlay"
export WAYLAND_DISPLAY=$(ls $XDG_RUNTIME_DIR | grep -m1 '^wayland-[0-9]*$'); export GDK_BACKEND=wayland
REPO=${GLANCE_REPO:-$(cd "$(dirname "$0")/../.." && pwd)}
/usr/bin/python3 "$REPO/tools/headless_shell/canvas_app.py" >/dev/null 2>&1 &
sleep 4; $O.Key Escape >/dev/null; sleep 1
gnome-text-editor >/dev/null 2>&1 &
sleep 5
gdbus monitor --session -d app.glance.Overlay > "$ROOT/mon.txt" 2>&1 &
python3 "$REPO/tools/headless_shell/e2e_actions.py" >> "$OUT" 2>&1
echo "monitor saw $(grep -c InputEvent "$ROOT/mon.txt") input events" >> "$OUT"
grep InputEvent "$ROOT/mon.txt" | head -4 | cut -c1-160 >> "$OUT"
