#!/bin/bash
# Starts Docker if it is not running and pulls the pinned chip tool image.
set -e
if ! docker info >/dev/null 2>&1; then
  (dockerd >/tmp/dockerd.log 2>&1 &)
  for i in $(seq 30); do docker info >/dev/null 2>&1 && break; sleep 1; done
fi
docker image inspect hpretl/iic-osic-tools:2026.10 >/dev/null 2>&1 || docker pull hpretl/iic-osic-tools:2026.10
echo "tools ready: hpretl/iic-osic-tools:2026.10"
