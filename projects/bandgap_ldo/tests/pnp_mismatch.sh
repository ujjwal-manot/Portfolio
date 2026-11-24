# Shows whether IHP's pnpMPA has a mismatch model: for the typical, worst and best HBT corners in $PDK_ROOT it prints the pnpMPA parameters of the plain corner and of its mismatch twin, and exits 0 only if each pair is the same, so a Monte Carlo draws no device-to-device spread for the pnps.
set -eo pipefail
lib=$PDK_ROOT/$PDK/libs.tech/ngspice/models/cornerHBT.lib
same=0
for c in typ wcs bcs; do
  plain=$(sed -n "/^\.LIB hbt_$c\$/,/^\.ENDL/p" "$lib" | grep sgp_mpa)
  mm=$(sed -n "/^\.LIB hbt_${c}_mismatch\$/,/^\.ENDL/p" "$lib" | grep sgp_mpa)
  echo "hbt_$c and hbt_${c}_mismatch, pnpMPA parameters:"; paste <(echo "$plain") <(echo "$mm")
  if [ -n "$plain" ] && [ "$plain" = "$mm" ]; then echo "hbt_${c}_mismatch sets every pnpMPA parameter to its hbt_$c value"; else echo "hbt_${c}_mismatch differs from hbt_$c"; same=1; fi
done
[ $same = 0 ] && echo "no pnpMPA mismatch is drawn in any Monte Carlo corner"
exit $same
