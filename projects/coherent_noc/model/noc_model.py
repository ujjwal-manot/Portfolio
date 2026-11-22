# Reference models for projects/coherent_noc: 2x2 XY credit-based mesh router, 4-core directory MESI protocol coherence checker, and CRC-16-CCITT go-back-N die-to-die replay link.

def xy_route_path(src, dst):
    x, y = src
    dx, dy = dst
    path = [(x, y)]
    while x != dx:
        x += 1 if dx > x else -1
        path.append((x, y))
    while y != dy:
        y += 1 if dy > y else -1
        path.append((x, y))
    return path

def simulate_mesh(pattern="uniform", n_packets=64, credits=4, early_credit=False):
    nodes = [(0, 0), (1, 0), (0, 1), (1, 1)]
    channels = [(n, n) for n in nodes]
    for a in nodes:
        for b in nodes:
            if abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1:
                channels.append((a, b))
    queues = {ch: [] for ch in channels}
    avail = {ch: credits for ch in channels}
    pending = []
    for idx in range(n_packets):
        src = nodes[idx % 4]
        if pattern == "hotspot":
            dst = (1, 1)
        elif pattern == "transpose":
            dst = (src[1], src[0])
        else:
            dst = nodes[(idx * 3 + 1) % 4]
        pending.append(xy_route_path(src, dst))
    delivered = 0
    max_occ = 0
    overflows = 0
    for _ in range(n_packets * 8):
        if not pending and all(len(q) == 0 for q in queues.values()):
            break
        for _inj in range(4):
            if not pending:
                break
            ch = (pending[0][0], pending[0][0])
            if avail[ch] > 0:
                queues[ch].append(pending.pop(0))
                avail[ch] -= 1
                if early_credit:
                    avail[ch] += 1
            else:
                break
        for ch in channels:
            occ = len(queues[ch])
            if occ > max_occ:
                max_occ = occ
            if occ > credits:
                overflows += 1
        for ch in channels:
            if not queues[ch]:
                continue
            path = queues[ch][0]
            if len(path) == 1:
                queues[ch].pop(0)
                delivered += 1
                if not early_credit:
                    avail[ch] += 1
            else:
                nxt_ch = (path[0], path[1])
                if avail[nxt_ch] > 0:
                    queues[ch].pop(0)
                    queues[nxt_ch].append(path[1:])
                    avail[nxt_ch] -= 1
                    if early_credit:
                        avail[nxt_ch] += 1
                    else:
                        avail[ch] += 1
        for ch in channels:
            occ = len(queues[ch])
            if occ > max_occ:
                max_occ = occ
            if occ > credits:
                overflows += 1
    return {
        "delivered": delivered,
        "max_occupancy": max_occ,
        "overflows": overflows,
        "deadlocked": delivered < n_packets,
    }

class MesiDirectory:
    def __init__(self, n_cores=4, miss_invalidate=False):
        self.n_cores = n_cores
        self.miss_invalidate = miss_invalidate
        self.mem = {}
        self.oracle = {}
        self.caches = [{} for _ in range(n_cores)]

    def read(self, core, addr):
        if addr in self.caches[core]:
            return self.caches[core][addr][1]
        owners = [c for c in range(self.n_cores) if addr in self.caches[c] and self.caches[c][addr][0] in ("M", "E")]
        if owners:
            owner = owners[0]
            val = self.caches[owner][addr][1]
            self.mem[addr] = val
            self.caches[owner][addr] = ("S", val)
            self.caches[core][addr] = ("S", val)
            return val
        val = self.mem.get(addr, 0)
        sharers = [c for c in range(self.n_cores) if addr in self.caches[c]]
        state = "S" if sharers else "E"
        self.caches[core][addr] = (state, val)
        return val

    def write(self, core, addr, val):
        self.oracle[addr] = val
        for other in range(self.n_cores):
            if other != core and addr in self.caches[other]:
                if self.caches[other][addr][0] == "M":
                    self.mem[addr] = self.caches[other][addr][1]
                if not self.miss_invalidate:
                    del self.caches[other][addr]
        self.caches[core][addr] = ("M", val)

    def check_swmr(self, addr):
        states = [self.caches[c][addr][0] for c in range(self.n_cores) if addr in self.caches[c]]
        writers = sum(1 for s in states if s in ("M", "E"))
        if writers > 1:
            return False
        if writers == 1 and len(states) > 1:
            return False
        return True

def crc16_ccitt(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if (crc & 0x8000) else (crc << 1) & 0xFFFF
    return crc

def d2d_transfer(flits, corrupt_indices=None, skip_on_replay=False):
    bad_left = set(corrupt_indices or ())
    received = []
    idx = 0
    replays = 0
    tx_count = 0
    while idx < len(flits):
        payload = flits[idx].to_bytes(4, "big")
        crc = crc16_ccitt(payload)
        wire = bytearray(payload)
        if tx_count in bad_left:
            bad_left.remove(tx_count)
            wire[-1] ^= 0x01
        tx_count += 1
        if crc16_ccitt(bytes(wire)) == crc:
            received.append(int.from_bytes(bytes(wire), "big"))
            idx += 1
        else:
            replays += 1
            if skip_on_replay:
                idx += 1
    return {"received": received, "replays": replays}
