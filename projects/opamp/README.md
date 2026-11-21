# opamp

The amplifier in front of the ADC. It runs as an inverting amplifier with gain -1 around 0.6 V, so the sensor's 0.2 to 1.0 V becomes 1.0 to 0.2 V at the ADC, and it has to drive the ADC's 2.05 pF sampling capacitor and settle to half an LSB (1.56 mV) inside the ADC's sampling time.

## Spec

From `chip.md`. The test setup is the real loop: rhigh resistors Rin = Rf = 20 k, `inp` at 0.6 V, a 2.05 pF MIM load, a 10 uA bias current.

| Spec | Value |
|---|---|
| DC gain | >= 66 dB |
| GBW | >= 20 MHz |
| Phase margin, beta = 0.5 loop, every corner and Monte Carlo run | >= 60 deg |
| Slew rate | >= 10 V/us |
| Settling of a 0.8 V step to 1.56 mV | <= 200 ns |
| Supply current | <= 500 uA |
| Output range | 0.2 V to 1.0 V |

## How it works

```
            vdd
   M3,M4 (PMOS sources)          M8 (PMOS output)
     |          |                   |
   f1 +-M3C   f2 +-M4C (PMOS cascodes)   out ---+--- 2.05 pF
     |          |                   |       |
   M6C        M7C (NMOS cascodes)   M9      Rz + Cc back to o1
     |          |                   |
   M6 ===== M7 (mirror)            vss
 inn-M1    M2-inp  (NMOS pair, tail M5)
```

- Stage 1 is a folded cascode. The NMOS input pair sits at 0.6 V, where it has room above its tail at every corner; a PMOS pair would not (see `chip.md`, "Why the opamp is inverting"). The cascodes give the gain: without them the first stage alone would not reach 66 dB.
- Stage 2 is a PMOS common-source stage that can pull the output close to either rail.
- Miller compensation: Cc from the output back to the first-stage output, with a nulling resistor Rz (rhigh) that moves the right-half-plane zero out of the way.
- Every bias comes from the one 10 uA input through mirrors, so a corner that changes the current changes it everywhere in step.

## How it was sized

`helpers/transistor_charts.py` sweeps one IHP NMOS and one PMOS at every corner and length (`make charts`) and builds gm/Id tables: for each gm/Id it gives current density, intrinsic gain, fT and saturation voltage. `helpers/opamp_sizing.py` then picks a gm/Id and length for each role (input pair, mirrors, cascodes, output) and works the sizes out from the specs: the input pair's gm from GBW with a 1.8x margin, Cc from phase margin, the output current from the non-dominant pole and the slew rate. Cascodes use tables taken with 0.25 V source-to-bulk, because that is what they see in the circuit.

Two things the charts corrected. First, the threshold the model reports and the threshold read from the curves (extrapolated from the point of maximum gm) differ by about 30 to 110 mV, so headroom sums use the extrapolated one, which is what the circuit actually sees. Second, the first version predicted GBW as the unity-gain frequency, which overstated it; GBW is now open-loop gain times frequency at 1 MHz, between the poles, both in the prediction and in the measurement.

Before any of that is trusted, `make check_model` runs the measurement testbenches on an ideal two-pole opamp whose numbers are known from arithmetic:

| Quantity | Measured against arithmetic | Where |
|---|---|---|
| a0_db | measured 80, expected 80 | `results/check_model.log` |
| pm_deg | measured 55.9068, expected 56.4562 | `results/check_model.log` |
| gbw_hz | measured 1.59127e+08, expected 1.59127e+08 | `results/check_model.log` |

## Results

60 corners: tt, ss, ff, sf and fs devices (resistors and capacitors paired with them: wcs with ss, bcs with ff), at -40, 27 and 125 C, with supplies 1.08, 1.16, 1.2 and 1.32 V. Each corner runs the loop-gain, step, noise and swing testbenches. The table gives the worst corner for each spec.

| Spec (log name) | Worst of all corners | Where |
|---|---|---|
| DC gain (a0_db) | worst 66.14 at ss_125_lo, spec >= 66 | `results/corners.log` |
| GBW (gbw_hz) | worst 2.261e+07 at ss_125_lo, spec >= 2e+07 | `results/corners.log` |
| Phase margin (pm_deg) | worst 62.14 at ff_m40_lo, spec >= 60 | `results/corners.log` |
| Slew rate (slew_v_per_s) | worst 1.877e+07 at ss_125_lo, spec >= 1e+07 | `results/corners.log` |
| Settling (settle_s) | worst 1.97e-07 at sf_125_lo, spec <= 2e-07 | `results/corners.log` |
| Supply current (supply_a) | worst 0.0002247 at ff_125_hi, spec <= 0.0005 | `results/corners.log` |
| Lowest output (out_low_v) | worst 0.06707 at ff_125_min, spec <= 0.2 | `results/corners.log` |
| Highest output (out_high_v) | worst 1.024 at ss_125_min, spec >= 1 | `results/corners.log` |
| Output noise, 50 kHz band (band_v_rms) | worst 9.523e-05 at ss_125_hi | `results/corners.log` |
| Output noise, 1 Hz to 1 GHz (total_v_rms) | worst 0.0004654 at ff_125_hi | `results/corners.log` |
| Supply rejection at 1 kHz (psrr_1k_db) | worst 40.57 at ss_125_lo | `results/corners.log` |
| Supply rejection at 1 MHz (psrr_1m_db) | worst 21.57 at ss_125_lo | `results/corners.log` |
| Monte Carlo, 200 runs with local mismatch at tt | combined yield 100.0% of 200 runs | `results/mc.log` |
| Input offset, same 200 runs | offset sigma 0.002666 V, worst 0.008446 V | `results/mc.log` |

The sizing script's prediction at tt against the measurement at tt, 27 C, 1.2 V:

| Quantity | Predicted | Where | 
|---|---|---|
| Gain | predicted gain_db 81.67 | `results/sizing.log` |
| Phase margin | predicted pm_deg 71.63 | `results/sizing.log` |
| Supply current | predicted supply_a 0.000175 | `results/sizing.log` |
| Measured at review_opamp_tt_27_nom | a0_db 77.08, pm_deg 65.1, supply_a 0.0002112 | `results/review_opamp.log` |

The prediction is 4.6 dB high on gain (the gds values in the charts come from a single drain voltage, and the real devices sit at others), 6.5 degrees high on phase margin (the mirror pole in the folded branch is not in the model), and it leaves out the bias network's current, which is why the measured supply is higher.

## Design review: Miller or indirect compensation

Indirect compensation (Cc into the low-impedance cascode node instead of the first-stage output) is the usual better choice: no right-half-plane zero, so less current for the same phase margin. Both were built (`design/opamp.cir`, `design/opamp_indirect.cir`, the indirect one sized by the same script) and run at the six corners that set the worst cases (`make review`):

| Design at tt, 27 C, 1.2 V | supply_a | pm_deg | band_v_rms | total_v_rms | Where |
|---|---|---|---|---|---|
| review_opamp_tt_27_nom (Miller) | 0.0002112 | 65.1 | 7.455e-05 | 0.0003877 | `results/review_opamp.log` |
| review_opamp_indirect_tt_27_nom | 0.0001614 | 82.3 | 7.456e-05 | 0.0009405 | `results/review_opamp_indirect.log` |
| Predicted area, Miller and indirect | predicted area_um2 944.6, predicted indirect_area_um2 871.9 | | | | `results/sizing.log` |

Indirect wins on current, phase margin and area, and both meet every spec. But its total output noise is 2.4 times higher, from a noise peak near 100 MHz where the indirect loop's gain falls off. The ADC samples the opamp output with no filter in between, so that noise lands in every sample. Damping resistors from 2 to 20 k in the indirect branch made the peak worse in every case tried. Miller stays.

## A requirement this block puts on the supply

At 1.08 V (the "lo" supply), the output cannot reach 1.0 V at the hot corners, and no sizing fixes that: the PMOS output device needs its saturation voltage, and 1.08 V leaves too little above 1.0 V. The rows below are the swing at the supplies where it is and is not met.

| Corner | Output range | Where |
|---|---|---|
| ss_125_lo, supply 1.08 V, not required | out_high_v 0.9097 | `results/corners.log` |
| ss_125_min, supply 1.16 V | out_high_v worst 1.024 at ss_125_min | `results/corners.log` |

So the analog supply must never fall below 1.16 V. That is now written into `chip.md` as a requirement on `bandgap_ldo`: with a 1.2 V target, regulation error plus load-step droop must stay under 40 mV.

## Broken copies

`make broken` applies each patch in `broken/` to a copy, runs the tests at tt, and the patch counts as caught only if the spec check fails with the line its first line names.

| Patch | What it breaks | Caught by | Where |
|---|---|---|---|
| `cascodes_removed` | first stage without cascodes | a0_db worst 44.53, spec >= 66: FAIL | `results/broken_cascodes_removed.log` |
| `no_nulling_resistor_small_cc` | no Rz, a third of Cc | pm_deg worst -1.351, spec >= 60: FAIL | `results/broken_no_nulling_resistor_small_cc.log` |
| `tail_current_cut_to_a_third` | input pair starved | slew_v_per_s worst 7.962e+06, spec >= 1e+07: FAIL | `results/broken_tail_current_cut_to_a_third.log` |

## Not covered yet

- No layout, so no parasitic wiring capacitance in the results.
- The load is a fixed 2.05 pF; the real ADC input switches between the sampling capacitor and its own switch resistance, so settling should be rerun against the ADC netlist once it exists.
- The noise that matters to the ADC is the noise inside its sampling bandwidth (the switch resistance times the sampling capacitor), not the 1 GHz figure above. That will be integrated once the ADC switch is sized.
- No common-mode rejection measurement: the inputs sit at 0.6 V in this loop, so it matters less than supply rejection, but it is not measured.

## Run it

```
make charts       # transistor sweeps at 15 corners and the gm/Id tables
make sizing       # sizes.inc from the charts and the specs
make check_model  # the testbenches against an ideal two-pole opamp
make corners      # 60 corners
make mc           # 200 Monte Carlo runs
make review       # Miller against indirect compensation
make broken       # each patch in broken/ must fail the spec it names
make all
```

## Interview questions

1. Why is this opamp inverting instead of a unity-gain buffer?
2. What does the nulling resistor do, and what happens to phase margin without it?
3. Indirect compensation needed less current and had more phase margin. Why was it still the wrong choice here?
4. Why does the output swing set a minimum on the supply, and which device sets it?
