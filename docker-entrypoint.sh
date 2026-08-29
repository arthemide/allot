#!/bin/sh
# Litestream supervises the application when off-site replication is on, which
# is the arrangement its own documentation recommends: replication is already
# running before the first write, and it stops cleanly with the app. Without a
# bucket configured there is nothing to replicate to, so the app runs alone.
set -eu

if [ -n "${LITESTREAM_BUCKET:-}" ]; then
    # -restore-if-db-not-exists rebuilds the database from the replica when the
    # volume is empty, which is what turns a dead SD card into a reboot.
    exec litestream replicate \
        -config /etc/litestream.yml \
        -restore-if-db-not-exists \
        -exec "python app.py"
fi

exec python app.py
