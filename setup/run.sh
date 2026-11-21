#!/bin/bash
# Runs a command with the chip tools, inside the image unless we are already in it.
set -e
if [ -d /foss/tools ]; then source /etc/profile >/dev/null 2>&1; exec "$@"; fi
root=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
exec docker run --rm -i -u "$(id -u):$(id -g)" -e HOME=/tmp -v "$root:$root" -w "$PWD" --entrypoint bash \
  hpretl/iic-osic-tools:2026.10 -c 'source /etc/profile >/dev/null 2>&1; exec "$@"' _ "$@"
