// Catalog of the three EdgeSense-130 tracks, their blocks, whole_chip, and console views.
export type TrackId = "digital" | "analog" | "ams" | "integration";
export type ViewId = "results" | "schematic" | "layout" | "waveforms" | "die3d";

export interface BlockEntry {
  id: string;
  track: TrackId;
  role: string;
}

export const TRACKS: { id: TrackId; label: string; blocks: BlockEntry[] }[] = [
  {
    id: "digital",
    label: "Digital VLSI",
    blocks: [
      { id: "fifo_bridge", track: "digital", role: "Async FIFO + AXI4-Stream skid" },
      { id: "cpu", track: "digital", role: "5-stage RV32I + Zicsr" },
      { id: "tensor_core", track: "digital", role: "8x8 BF16/FP8/MX systolic array" },
      { id: "coherent_noc", track: "digital", role: "4-core MESI 2x2 mesh" },
    ],
  },
  {
    id: "analog",
    label: "Analog VLSI",
    blocks: [
      { id: "opamp", track: "analog", role: "Folded-cascode Miller opamp" },
      { id: "bandgap_ldo", track: "analog", role: "Bandgap reference + 1.2 V LDO" },
      { id: "serdes_frontend", track: "analog", role: "10 GBd SiGe TX + CTLE" },
      { id: "lc_vco", track: "analog", role: "10 GHz LC VCO" },
    ],
  },
  {
    id: "ams",
    label: "Analog / Mixed-Signal",
    blocks: [
      { id: "adc", track: "ams", role: "8-bit 1 MS/s SAR ADC" },
      { id: "power_manager", track: "ams", role: "Digital LDO + DVFS + droop" },
      { id: "serdes_link", track: "ams", role: "DFE + CDR NRZ/PAM4 link" },
      { id: "frac_n_pll", track: "ams", role: "10 GHz fractional-N PLL" },
    ],
  },
  {
    id: "integration",
    label: "Integration",
    blocks: [{ id: "whole_chip", track: "integration", role: "Full mixed-signal chip" }],
  },
];

export const ALL_BLOCKS: BlockEntry[] = TRACKS.flatMap((t) => t.blocks);

export const VIEWS: { id: ViewId; label: string }[] = [
  { id: "results", label: "Results" },
  { id: "schematic", label: "Schematic" },
  { id: "layout", label: "Layout" },
  { id: "waveforms", label: "Waveforms" },
  { id: "die3d", label: "3D Die" },
];
