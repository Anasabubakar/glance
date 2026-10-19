sleep 4
O="gdbus call --session -d app.glance.Overlay -o /app/glance/Overlay -m app.glance.Overlay"
gdbus monitor --session -d app.glance.Overlay > $ROOT/mon.txt 2>&1 &
MP=$!
sleep 1
$O.SetRecording true >/dev/null
$O.Click 300 200 1 1 >/dev/null; sleep 1
$O.Key "a" >/dev/null; sleep 1
$O.Scroll 300 200 -2 >/dev/null; sleep 1
$O.SetRecording false >/dev/null
$O.Click 310 210 1 1 >/dev/null; sleep 1
kill $MP 2>/dev/null
{ echo "== signals seen"; grep -c "InputEvent" $ROOT/mon.txt; grep "InputEvent" $ROOT/mon.txt | cut -c1-230; } >> $OUT
