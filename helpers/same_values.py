# Compares two result files value by value (key value pairs, as the testbenches write them) and passes only if every named value is in both, is a number, and the two differ by no more than its tolerance: same_values.py key=tolerance[,key=tolerance...] a.txt b.txt.
import math, sys
from analog_results import parse

def compare(tolerances, a, b):
    x, y, ok = parse(a), parse(b), True
    for key, tol in tolerances.items():
        u, v = x.get(key, math.nan), y.get(key, math.nan)
        same = abs(u - v) <= tol
        ok &= same
        print(f"{key:16} {u:.6g} and {v:.6g}, differ by {abs(u - v):.3g}, tolerance {tol:g}: {'same' if same else 'DIFFERENT'}")
    print("the two runs agree" if ok else "the two runs differ")
    return ok

if __name__ == "__main__":
    spec, a, b = sys.argv[1:]
    sys.exit(0 if compare({k: float(v) for k, v in (p.split("=") for p in spec.split(","))}, a, b) else 1)
