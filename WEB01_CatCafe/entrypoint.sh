#!/bin/sh
set -e

# (Re)build the database on container start so the challenge is deterministic
python /app/init_db.py

# Start Flask (single process, keeps logs on stdout)
exec python /app/app.py
