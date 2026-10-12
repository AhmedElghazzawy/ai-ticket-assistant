#!/bin/sh
# Hosting volumes (e.g. on Fly.io) can arrive owned by root. Fix that once, then drop root and run
# the app as the normal user "app": the app itself never runs as root.
set -eu
if [ "$(id -u)" = "0" ]; then
    chown app:app /app/var
    exec setpriv --reuid=app --regid=app --init-groups -- "$@"
fi
exec "$@"
