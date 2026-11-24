# Checks the digital LDO controller as ngspice runs it through d_cosim: from a table of lo, hi, far_lo, far_hi, rst_n, the eight count bits, the eight drive bits and the N unit enables (time and value pairs, as wrdata writes them), each clock edge's inputs (1 ns before it) give the count and drive the controller's rule expects, and 5 ns after the edge count and drive must match and the enables must be a thermometer code of drive units, so a port wired in the wrong order shows: python3 dldo_results.py cosim N BIG P PB table.txt
import sys

def cosim_check(path, n, big, p, pb, first=10e-9, period=20e-9):
    rows = [[float(v) for v in l.split()] for l in open(path) if l.strip()]
    at = lambda t: [r for r in rows if r[0] <= t][-1][1::2]
    word = lambda bits: sum(1 << i for i, b in enumerate(bits) if b > 0.6)
    count, problems, edges, edge = 0, [], 0, first
    while edge + 5e-9 <= rows[-1][0]:
        lo, hi, far_lo, far_hi, rst_n = (v > 0.6 for v in at(edge - 1e-9)[:5])
        up, down, far_up, far_down = lo and not hi, hi and not lo, far_lo and not far_hi, far_hi and not far_lo
        step = big if far_up else -big if far_down else 1 if up else -1 if down else 0
        count = min(max(count + step, 0), n) if rst_n else 0
        drive = min(max(count + (pb if far_up else -pb if far_down else p if up else -p if down else 0), 0), n) if rst_n else 0
        out = at(edge + 5e-9)
        got_count, got_drive, on = word(out[5:13]), word(out[13:21]), [v > 0.6 for v in out[21:21 + n]]
        if (got_count, got_drive) != (count, drive) or on != [i < drive for i in range(n)]:
            problems.append(f"edge at {edge:.4g} s: count {got_count} drive {got_drive} with {sum(on)} units on, expected count {count} drive {drive}")
        edges, edge = edges + 1, edge + period
    return problems, edges

if __name__ == "__main__":
    mode, args = sys.argv[1], sys.argv[2:]
    if mode == "cosim":
        problems, edges = cosim_check(args[4], int(args[0]), int(args[1]), int(args[2]), int(args[3]))
        print(f"{edges} clock edges checked")
    for f in problems:
        print("FAIL " + f)
    print("every check passes" if not problems else f"{len(problems)} failures")
    sys.exit(1 if problems else 0)
