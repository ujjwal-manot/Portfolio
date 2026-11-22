# Builds compare_with_papers/report.md by joining verified primary-source entries in published.json against measured logs under projects/*/results: python3 make_report.py published.json .. report.md.
import json, re, sys
from pathlib import Path

def parse_charts_vth(charts_log):
    p = Path(charts_log)
    if not p.exists():
        return {}
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    cols = []
    for line in lines:
        if line.startswith("corner"):
            cols = re.findall(r"[NP]\s+L=[0-9.]+", line)
        elif cols and line.startswith("tt_27"):
            pairs = re.findall(r"([0-9.]+)/([0-9.]+)", line)
            mapped = dict(zip(cols, pairs))
            out = {}
            if "N L=0.13" in mapped:
                out["VTN10x013"] = float(mapped["N L=0.13"][1])
            if "P L=0.13" in mapped:
                out["VTP10x013"] = -float(mapped["P L=0.13"][1])
            return out
    return {}

def _fmt_pub(pub, units):
    if pub is None:
        return "not published"
    if isinstance(pub, dict):
        if "target" in pub and pub["target"] is not None:
            lo = "" if pub.get("min") is None else f"{pub['min']}"
            hi = "" if pub.get("max") is None else f"{pub['max']}"
            rng = f" [{lo}, {hi}]" if (lo or hi) else ""
            return f"{pub['target']} {units}{rng}".strip()
        if "typ" in pub and pub["typ"] is not None:
            return f"{pub['typ']} {units} (min {pub.get('min')}, max {pub.get('max')})".strip()
        return ", ".join(f"{k}={v}" for k, v in pub.items() if v is not None) or "not published"
    return f"{pub} {units}".strip()

def _target_num(pub):
    if isinstance(pub, dict):
        for key in ("target", "typ"):
            if pub.get(key) is not None:
                return float(pub[key])
    elif isinstance(pub, (int, float)):
        return float(pub)
    return None

def build_report(published_path, repo_root):
    data = json.loads(Path(published_path).read_text(encoding="utf-8"))
    root = Path(repo_root)
    measured_vth = parse_charts_vth(root / "projects" / "opamp" / "results" / "charts.log")
    out = [
        "# Comparison with Published Work",
        "",
        "Generated from `compare_with_papers/published.json` and measured logs on disk. Entries with no local measurement state `not run yet`; entries absent from primary sources state `not published`.",
        "",
        "## 1. IHP SG13G2 Process Specification",
        "",
        "| Parameter | Our Value | Published Value | Difference | Source |",
        "|---|---|---|---|---|",
    ]
    spec = data["sg13g2_process_spec"]
    for group_name, entries in spec.items():
        if isinstance(entries, dict):
            entries = [entries]
        for item in entries:
            param = item.get("parameter", group_name)
            pub = item.get("published")
            units = item.get("units", "")
            pub_str = _fmt_pub(pub, units)
            ours = measured_vth.get(param)
            tgt = _target_num(pub)
            if ours is None:
                our_str, diff_str = "not run yet", "n/a"
            else:
                our_str = f"{ours:.3f} {units}".strip()
                diff_str = f"{ours - tgt:+.3f} {units}".strip() if tgt is not None else "n/a"
            src = f"{item.get('document', '')}, {item.get('location', '')}".strip(", ")
            out.append(f"| `{param}` | {our_str} | {pub_str} | {diff_str} | {src} |")

    out += [
        "",
        "## 2. JKU 5-Transistor OTA (IHP SG13G2 Tutorial)",
        "",
        "| Spec | Our Value | Published Value | Difference | Source |",
        "|---|---|---|---|---|",
    ]
    for item in data["jku_5t_ota"]["simulated_specs"]:
        pub_str = _fmt_pub(item.get("published"), item.get("units", ""))
        src = f"{item.get('document', '')}, {item.get('location', '')}".strip(", ")
        out.append(f"| `{item['parameter']}` | not run yet | {pub_str} | n/a | {src} |")

    cum = data["cummings_snug2002_fifo1"]
    out += [
        "",
        "## 3. Cummings SNUG-2002 Async FIFO (FIFO1)",
        "",
        f"- **Source:** {cum['document']} ({cum['author']}, {cum['revision']}, {cum['location']})",
        f"- **Modules referenced:** {', '.join(m['module'] for m in cum['modules'])}",
        "- **Status:** not run yet against `compare_with_papers/cummings_fifo/`.",
        "",
        "## 4. LibreLane Reference Block",
        "",
        "| Reference | Our Value | Published Value | Source |",
        "|---|---|---|---|",
    ]
    for key, item in data["librelane_reference_block"].items():
        if isinstance(item, dict):
            pub_cells = item.get("cells")
            pub_str = "not published" if pub_cells is None else f"cells={pub_cells}, area={item.get('area')}, fmax={item.get('fmax')}"
            src = f"{item.get('document', key)}, {item.get('location', '')}".strip(", ")
            out.append(f"| `{key}` | not run yet | {pub_str} | {src} |")

    mur = data["murmann_adc_survey_8bit_sar_1_to_100_msps"]
    out += [
        "",
        "## 5. Murmann ADC Survey (8-bit Nyquist SAR, 1 to 100 MS/s)",
        "",
        f"Source: {mur['document']} ({mur['revision']}, {mur['location']}). EdgeSense-130 ADC silicon comparison: not run yet.",
        "",
        "| Paper | Tech (um) | Fs (MS/s) | SNDR HF (dB) | Power (uW) | Walden FoM (fJ/step) | Schreier FoM (dB) |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in mur["rows"]:
        p = row["published"]
        fs_msps = p["fs_hz"] / 1e6
        pw_uw = p["power_w"] * 1e6
        out.append(
            f"| {row['sheet']} {row['year']} {row['paper_id']} ({row['authors'].split(',')[0]}) | "
            f"{row['technology_um']} | {fs_msps:.2f} | {p['sndr_hf_db']:.1f} | "
            f"{pw_uw:.1f} | {p['fomw_hf_fj_per_step']:.1f} | {p['foms_hf_db']:.1f} |"
        )
    return "\n".join(out) + "\n"

if __name__ == "__main__":
    pub = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("published.json")
    root = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("..")
    dst = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("report.md")
    dst.write_text(build_report(pub, root), encoding="utf-8", newline="\n")
    print(f"wrote {dst}")
