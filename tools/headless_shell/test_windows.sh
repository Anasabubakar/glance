sleep 4
O="gdbus call --session -d app.glance.Overlay -o /app/glance/Overlay -m app.glance.Overlay"
ls $XDG_RUNTIME_DIR | head -3 >> $OUT
export WAYLAND_DISPLAY=$(ls $XDG_RUNTIME_DIR | grep -m1 '^wayland-[0-9]*$')
export GDK_BACKEND=wayland
gnome-text-editor >/dev/null 2>&1 &
sleep 6
{
echo "== windows"; $O.GetWindows | cut -c1-400
echo "== minimize focused"; $O.WindowAction focused minimize | cut -c1-200
sleep 1; $O.GetWindows | cut -c1-300
echo "== unminimize by title"; $O.WindowAction "class:text" unminimize | cut -c1-120
sleep 1; echo "== maximize"; $O.WindowAction "class:text" maximize | cut -c1-100
sleep 1; $O.GetWindows | cut -c1-300
echo "== stopgrab on/off"; $O.SetStopGrab true; $O.SetStopGrab false
echo "== recording on/off"; $O.SetRecording true; $O.SetRecording false
echo "== close"; $O.WindowAction "class:text" close | cut -c1-100
sleep 2; $O.GetWindows | cut -c1-200
echo "== version"; gdbus call --session -d app.glance.Overlay -o /app/glance/Overlay -m org.freedesktop.DBus.Properties.Get app.glance.Overlay Version
} >> $OUT 2>&1
