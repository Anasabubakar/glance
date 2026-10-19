#!/bin/bash
# Headless gnome-shell with the Glance extension, in a throwaway HOME. Usage: run.sh <script.sh to run inside>
set -e
ROOT=$(mktemp -d /tmp/glance-hs.XXXXXX)
export HOME=$ROOT/home XDG_CONFIG_HOME=$ROOT/home/.config XDG_DATA_HOME=$ROOT/home/.local/share XDG_CACHE_HOME=$ROOT/home/.cache
export XDG_RUNTIME_DIR=$ROOT/run; mkdir -p $HOME $XDG_RUNTIME_DIR $XDG_CONFIG_HOME/glib-2.0/settings $XDG_DATA_HOME/gnome-shell/extensions
chmod 700 $XDG_RUNTIME_DIR
cp -r ${GLANCE_REPO:-$(cd "$(dirname "$0")/../.." && pwd)}/glance/shell/gnome_ext/glance-cursor@glance.app $XDG_DATA_HOME/gnome-shell/extensions/
cat > $XDG_CONFIG_HOME/glib-2.0/settings/keyfile <<KF
[org/gnome/shell]
enabled-extensions=['glance-cursor@glance.app']
disable-user-extensions=false
disable-extension-version-validation=true
welcome-dialog-last-shown-version='99'
KF
export GSETTINGS_BACKEND=keyfile
export XDG_SESSION_TYPE=wayland
export SHELL_LOG=$ROOT/shell.log
export ROOT
export OUT=${OUT:-/tmp/glance-hs-out.txt}; : > $OUT
exec dbus-run-session -- bash -c '
  gnome-shell --headless --wayland --no-x11 --virtual-monitor 1280x720 > $SHELL_LOG 2>&1 &
  SP=$!
  for i in $(seq 1 60); do gdbus call --session -d app.glance.Overlay -o /app/glance/Overlay -m org.freedesktop.DBus.Peer.Ping >/dev/null 2>&1 && break; sleep 0.5; done
  bash "'"$1"'" ; RC=$?
  kill $SP 2>/dev/null; wait $SP 2>/dev/null; exit $RC'
