#!/bin/bash
Xvfb :99 -screen 0 1280x720x24 -ac &
sleep 1
exec python -u main.py
