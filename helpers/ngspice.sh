#!/bin/bash
# Runs one ngspice bench in batch mode (ngspice.sh bench.cir run.log) through setup/run.sh, writes its log, and exits nonzero if ngspice did or if spice_log_check fails that log.
here=$(cd "$(dirname "$0")" && pwd)
"$here/../setup/run.sh" ngspice -b "$1" > "$2" 2>&1
e=$?
"$here/../setup/run.sh" python3 "$here/spice_log_check.py" "$2" || exit 1
exit $e
