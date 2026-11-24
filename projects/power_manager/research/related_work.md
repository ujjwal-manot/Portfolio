<!-- Draft related-work survey for power_manager (proportional kick on top of PI control in the digital LDO); not yet reviewed. -->
# power_manager: related work (draft)

## How the sources were checked

- Each citation below was taken from the DOI's Crossref record (https://api.crossref.org/works/DOI). Greek letters are written in ASCII (u for micro).
- "Abstract" means the abstract was read in the Semantic Scholar record for the same DOI.
- "Full text" applies to one paper (5): its HTML edition at https://www.jos.ac.cn/en/article/doi/10.1088/1674-4926/41/11/111405 was opened, and its tables and figure captions were read. No other full text could be opened; the IEEE and repository copies could not be opened.
- Numbers are quoted as the source states them. The page given is the paper's first page, or the table named.
- "Not verified" means only the Crossref record was opened, so no number is given.

## Verified

1. A. Singh, M. Kar, V. C. K. Chekuri, S. K. Mathew, A. Rajan, V. De, S. Mukhopadhyay, "A Digital Low-Dropout Regulator With Autotuned PID Compensator and Dynamic Gain Control for Improved Transient Performance Under Process Variations and Aging," IEEE TPEL, vol. 35, no. 3, pp. 3242-3253, 2020. https://doi.org/10.1109/tpel.2019.2930490
   - Numbers (abstract, p. 3242, "130-nm CMOS test-chip"):
     - "2.1x improvement in transient performance under process variations";
     - "30% improvement for aging-induced degradations";
     - "55-ns setting time for a 5 to 45 mA load step in 100 ps";
     - "97.8% peak current efficiency".
   - Relevance: the closest work found. It uses the same node and gain switching on top of PID.
2. M. Huang, Y. Lu, R. P. Martins, "An Analog-Proportional Digital-Integral Multiloop Digital LDO With PSR Improvement and LCO Reduction," IEEE JSSC, early access, pp. 1-14 in the Crossref record, 2020. https://doi.org/10.1109/jssc.2020.2967540
   - Numbers (abstract, p. 1, 65-nm):
     - "65-mV undershoot ... with a 0-10-mA load current step under 0.6-V supply voltage and 50-mV dropout";
     - "5-MHz operation clock";
     - "29 uA";
     - "0.37-ps figure of merit".
   - Relevance: splits the P and I paths. Here P is digital (kick units) and I is the count.
3. M. Huang, Y. Lu, "An Analog-Proportional Digital-Integral Multi-Loop Digital LDO with Fast Response, Improved PSR and Zero Minimum Load Current," CICC, pp. 1-4, 2019. https://doi.org/10.1109/cicc.2019.8780307
   - Numbers (abstract, p. 1, 65nm): "0.38ps Figure of merit (FoM) and 22dB PSR at 1MHz ... at 0.6V supply".
   - Relevance: the conference version of 2.
4. Y. Lu, M. Huang, R. P. Martins, "PID Control Considerations for Analog-Digital Hybrid Low-Dropout Regulators (Invited Paper)," EDSSC, pp. 1-3, 2019. https://doi.org/10.1109/edssc.2019.8754302
   - Numbers: none. The abstract uses PID theory "to discuss and categorize the existing LDOs" (abstract, p. 1).
   - Relevance: the framing behind P and PI.
5. M. Huang, Y. Lu, R. P. Martins, "A comparative study of digital low dropout regulators," J. Semicond., vol. 41, no. 11, art. 111405, 2020. https://doi.org/10.1088/1674-4926/41/11/111405
   - Numbers (full text, Table 2 "FoM of speed versus process nodes"): its row for ref. [39] (which is item 1 here) reads 2020, 130 nm, "ADC + PID", FoM 63.9 ps; other rows run down to 0.026 ps (28 nm, analog-assisted).
   - Relevance: Fig. 10's caption is "Output voltage transient response under I-only, P-only, PI, and PID control", so a P/PI comparison exists as an illustration. The data behind that figure was not read.
6. K. Z. Ahmed et al., "A Variation-Adaptive Integrated Computational Digital LDO in 22-nm CMOS With Fast Transient Response," IEEE JSSC, vol. 55, no. 4, pp. 977-987, 2020. https://doi.org/10.1109/jssc.2019.2961854
   - Numbers (abstract, p. 977): "10-bit PG design", "droop of 100 mV for 500 mA (2 A/ns di/dt) with settling times < 20 ns".
   - Relevance: computes the switch count directly instead of filtering it.
7. Y. K. Cherivirala, D. D. Wentzloff, "A Capacitor-Less Digital LDO Regulator With Synthesizable PID Controller Achieving 99.75% Efficiency and 93.3-ps Response Time in 65 nm," IEEE TCAS-II, vol. 70, no. 5, pp. 1769-1773, 2023. https://doi.org/10.1109/tcsii.2023.3257686
   - Numbers (abstract, p. 1769): "0.0925mm 2", "5mA - 80mA at 50mV dropout", "93.3ps response time with 99.75% current efficiency", "FOM of 233fs".
   - Relevance: a synthesizable PID DLDO.
8. Y. K. Cherivirala, M. Saligane, D. D. Wentzloff, "An Open Source Compatible Framework to Fully Autonomous Digital LDO Generation," ISCAS, pp. 1-5, 2023. https://doi.org/10.1109/iscas46773.2023.10181884
   - Numbers (abstract, p. 1): input range "1.8V-3.3V (Skywater 130nm)", maximum load "0.5mA-50mA (Skywater 130nm)"; a stochastic flash ADC "achieving 15x faster settling time" (65 nm silicon).
   - Relevance: a DLDO from up to 3.3 V in an open 130 nm PDK, so a 3.3 V input alone is not new.
9. S. Bang et al., "25.1 A Fully Synthesizable Distributed and Scalable All-Digital LDO in 10nm CMOS," ISSCC, pp. 380-382, 2020. https://doi.org/10.1109/isscc19947.2020.9063040
   - Numbers (abstract, p. 380): "9 DLDO units in 10nm CMOS"; a "fast digital PID-based controller".
   - Relevance: a digital PID DLDO.
10. J.-E. Park, D.-K. Jeong, "A Fully Integrated 700mA Event-Driven Digital Low-Dropout Regulator with Residue-Tracking Loop for Fine-Grained Power Management Unit," VLSI Symp., pp. 231-232, 2018. https://doi.org/10.1109/vlsic.2018.8502295
    - Numbers (abstract, p. 231, 65nm LP): "on-chip 100pF output capacitor", "load regulation of 0.1mV/mA", "output voltage error below 1.1% across a range from 0.5 to 1V", "figure-of-merit (FOM) of 6.74fs".
    - Relevance: an output range (0.5 to 1 V) that overlaps vdd_cpu's 0.9 to 1.2 V DVFS states.
11. Y. Yu, J. Yuan, S. Qiao, Y. Hei, "A Fast-Transient All-Digital LDO with Adaptive Clock Technique," Electronics, vol. 8, no. 12, art. 1422, 2019. https://doi.org/10.3390/electronics8121422
    - Numbers (abstract, art. 1422, SMIC 55 nm): "loop gain boost adaptively when the output voltage undershoot/overshoot is detected"; "5.03e-4 mm2"; "undershoot is 40 mV and transient response time is 500 ns with load step of 10 to 800 uA".
    - Relevance: gain boost on droop, the same idea as the coarse-window kick.
12. M. H. Farooq et al., "A Tri-loop Fast-transient Digital LDO with Adaptive-gain Control and Fine-loop Freezer," ISCAS, pp. 1-5, 2024. https://doi.org/10.1109/iscas58744.2024.10558004
    - Numbers (abstract, p. 1, 180-nm, simulation): "0.22 mm2", "≤ 130 uV of VRIPP", "minimum dropout voltage of 20 mV", "peak current efficiency of 99.96 %".
    - Relevance: an adaptive coarse loop and an undershoot limiter in a mature node.
13. G. Cai, C. Zhan, Y. Lu, "A Fast-Transient-Response Fully-Integrated Digital LDO with Adaptive Current Step Size Control," ISCAS, pp. 1-4, 2019. https://doi.org/10.1109/iscas.2019.8702758
    - Numbers (abstract, p. 1, 65-nm LP):
      - "0.6-V 100-mA", "0.17 mm2", "1nF";
      - "undershoot and overshoot voltages are only 53 mV and 37 mV" for "0 and 100 mA";
      - "34.6 μα" (as printed);
      - "99.96%".
    - Relevance: a step size that grows with load, a cousin of the BIG step.
14. G. Koo, J. Kim, S. Lee, J. H. Shim, K. Cho, "An Ultrawide Load-Range Fast-Transient Output Capacitor-Less Digital LDO With Adaptive Gate Modulation and Droop Detection," IEEE SSC-L, vol. 7, pp. 199-202, 2024. https://doi.org/10.1109/lssc.2024.3420117
    - Numbers (abstract, p. 199, 28-nm): ripple "under 17 mV", "response time of less than 10 ns and a recovery time of less than 30 ns".
    - Relevance: asynchronous droop detection.
15. I. A. Wahla et al., "A Fast-Transient Digital LDO With Asynchronous Coarse and Dual-Mode Fine Regulation Loops," IEEE OJ-PEL, vol. 7, pp. 330-341, 2026. https://doi.org/10.1109/ojpel.2025.3647801
    - Numbers (abstract, p. 330, 65-nm):
      - "0.098 mm2", input "0.6 V to 1.2 V";
      - "recovery time of ≤ 30 ns for a 109 mV voltage droop when a (0 mA → 25 mA)" step "with an edge timing of 10 ns";
      - "overall figure-of-merit of 1.106 ns" (squared, as a superscript in the abstract), "VRIPP of ≤ 2 mV".
    - Relevance: coarse plus fine loops, as here.

## Not verified (Crossref record only, no number)

16. Y. Okuma et al., "0.5-V input digital LDO with 98.7% current efficiency and 2.7-uA quiescent current in 65nm CMOS," CICC, pp. 1-4, 2010. https://doi.org/10.1109/cicc.2010.5617586
17. S. B. Nasir, S. Gangopadhyay, A. Raychowdhury, "5.6 A 0.13um fully digital low-dropout regulator with adaptive control and reduced dynamic stability for ultra-wide dynamic range," ISSCC, pp. 1-3, 2015. https://doi.org/10.1109/isscc.2015.7062944
18. D. Kim, M. Seok, "8.2 Fully integrated low-drop-out regulator based on event-driven PI control," ISSCC, pp. 148-149, 2016. https://doi.org/10.1109/isscc.2016.7417950
19. Y.-J. Lee et al., "A 200-mA Digital Low Drop-Out Regulator With Coarse-Fine Dual Loop in Mobile Application Processor," IEEE JSSC, vol. 52, no. 1, pp. 64-76, 2017. https://doi.org/10.1109/jssc.2016.2614308

## Gap (one sentence)

PI and PID digital control (1, 7, 9), gain boost on droop (1, 11 to 13) and 3.3 V-input DLDOs in an open 130 nm PDK (8) all exist, so neither the kick nor the input range is new. What was not found is a controlled ablation of a proportional kick against the same PI loop, run on transistor-level switches with the thick-oxide level shifters, at PVT corners and with Monte Carlo, in IHP SG13G2. Item 5 shows a P/PI comparison only as an illustration, and items 17 and 18 were not read.

## Proposed claim (fixed before any run)

- **Claim:** the proportional kick (P = 1, PB = 8 in design/dldo_ctrl.sv) reduces the worst droop of vdd_cpu without slowing its recovery.
- **Metric:**
  - droop: the lowest rail voltage below the setpoint after a load step;
  - settling time: from the step until the rail stays inside the fine comparator window;
  - steady-state ripple: limit-cycle peak to peak.
  - Step: 0 to 7.5 mA (the cpu's typical current at 1.2 V in chip.md), with a 1 ns edge (proposed, fixed before the run), at the 1.2 V DVFS state; whether the cpu activity file in uses.txt (projects/cpu/build/cpu_gates.vcd) is used instead of the plain step is for the lead to decide before the run.
- **Baseline:** the same controller and switch array with P = 0 and PB = 0 (PI only, with the same BIG step), in the same loop simulation (tests/make_loop.py), at each corner on the project's fixed list.
- **Pass:** at every corner,
  - PI plus kick's worst droop is <= 0.8 times PI-only's;
  - its settling time is no longer than PI-only's plus one 20 ns clock;
  - its ripple is no larger than PI-only's plus the fine comparator window width (in mV, read from the design before the run).
- **Monte Carlo:** 100 seeds at tt 27 on comparator offsets and switch mismatch. The droop ratio is reported with its spread, and the pass rate with its one-sided 95% lower bound.
- **Fail:** any corner where the droop ratio exceeds 0.8, or where kick lengthens settling or adds ripple beyond the limits above. A fail is reported as a negative result.
- **Published context, not a baseline:** item 1 (the same node) reports "55-ns setting time for a 5 to 45 mA load step in 100 ps". The process, load and output capacitance differ, so the comparison is qualitative.
