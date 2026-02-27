#!/bin/bash
# Supprime le lock si il existe
rm -f /tmp/.X99-lock

Xvfb :99 -screen 0 1280x720x24 -ac &
sleep 1
exec python -u main.py
