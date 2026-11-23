<!-- Draft related-work survey for the opamp (gm/Id sizing that survives layout); not yet reviewed. -->
# opamp: related work (draft)

## How the sources were checked

- Each citation below was taken from the DOI's Crossref record (https://api.crossref.org/works/DOI), not typed by hand. Greek letters are written in ASCII (u for micro).
- "Abstract" means the abstract was read in the Semantic Scholar record for the same DOI. No full text could be opened for this block; the IEEE, KAUST, TUM and Udelar copies were behind bot checks.
- Numbers are quoted as the abstract states them. The page given is the paper's first page, where the abstract sits.
- "Not verified" means only the Crossref record was opened, so nothing is said about the content and no number is given.
- Copies of the records are in third_party/literature/evidence/ (git-ignored).

## Verified (abstract read)

1. F. Silveira, D. Flandre, P. G. A. Jespers, "A gm/ID based methodology for the design of CMOS analog circuits and its application to the synthesis of a silicon-on-insulator micropower OTA," IEEE JSSC, vol. 31, no. 9, pp. 1314-1319, 1996. https://doi.org/10.1109/4.535416
   - Numbers: none in the abstract. It states that gm/ID "is a universal characteristic of all the transistors belonging to a same process" (abstract, p. 1314).
   - Relevance: this is the method helpers/opamp_sizing.py follows.
2. M. De Matteis, "MATLAB-Assisted EKV-gm/ID Design Procedure for Two-Stage Miller-Compensated CMOS OTAs Starting from Closed-Loop Specifications," J. Low Power Electron. Appl., vol. 16, no. 4, art. 53, 2026. https://doi.org/10.3390/jlpea16040053
   - Numbers (abstract, art. 53, 0.18 um CMOS):
     - The model and nominal simulation give "61.80 and 59.27 dB DC gain, 430.78 and 431.52 MHz unity-gain bandwidth, 69.24° and 68.81° phase margin".
     - Model errors are "below 5%" in the design region.
     - The design was checked over "45 process-voltage-temperature corners".
   - Relevance: it measures model-to-schematic error, but not schematic-to-layout.
3. Y. Li, X. Ni, S. Achour, B. Murmann, "Open-ALOE: An Analog Layout Automation Flow for the Open-Source Ecosystem," ISQED, pp. 1-6, 2025. https://doi.org/10.1109/isqed65160.2025.11014456
   - Numbers (abstract, p. 1, SKY130 bandgap): "560 candidate layouts" in "approximately 30 minutes"; the fabricated part shows "a voltage error of 7.8 mV with 100x speedup compared to the manual layout".
   - Relevance: open-PDK layout search scored by post-layout performance.
4. M. Scherzer, M. Auer, "CORA-OpAmp: A Compact Open-Source Reinforcement-Learning Approach for Operational Amplifier Optimization in IHP SG13G2," ICECS, pp. 1-4, 2025. https://doi.org/10.1109/icecs66544.2025.11270673
   - Numbers: none in the abstract. It optimizes a folded cascode in IHP SG13G2 with gm/Id as the state input (abstract, p. 1).
   - Relevance: the same PDK and topology, but sizing only; the abstract says nothing about layout.
5. S. A. Khalid, S. E. Maestre, K. M. Madrid-Khalid, "Open-LUT: Interactive gm/ID Lookup Tables for MOSFET Sizing in Open-Source PDKs," ICICM, pp. 344-353, 2025. https://doi.org/10.1109/icicm66614.2025.11316023
   - Numbers: none. The abstract lists "incorporating parasitic analysis" and lookup tables "across different temperatures and process corners" as future work (abstract, p. 344).
   - Relevance: gm/Id tables in SKY130 without corners or parasitics.
6. D. Arevalos, J. Marin, K. Herman, C. A. Rojas, "Leveraging Lookup Tables for Efficient LDO Design Exploration using Open-Source CAD Tools and IHP-Open130-G2 PDK," MIXDES, pp. 124-129, 2024. https://doi.org/10.23919/mixdes62605.2024.10614033
   - Numbers: none in the abstract (abstract, p. 124).
   - Relevance: lookup-table sizing in IHP's open PDK.
7. K. Herman, D. Warning, "Open-Source Approach to IC Development: Validation Against Measurements of Selected Devices from the IHP-Open-PDK," VLSI-SoC, pp. 1-4, 2025. https://doi.org/10.1109/vlsi-soc64688.2025.11421720
   - Numbers: none. The abstract reports "key discrepancies" between ngspice/Xyce results and the PDK's reference data (abstract, p. 1).
   - Relevance: it bounds how far the charts behind the sizing can be trusted.
8. K. Herman, R. Scholz, S. Andreev, "Reflections on the First European Open Source PDK by IHP - Experiences After One Year and Future Activities," MIXDES, pp. 19-22, 2024. https://doi.org/10.23919/mixdes62605.2024.10614043
   - Numbers: the PDK "was released to the public in February 2023" (abstract, p. 19).
   - Relevance: the PDK's status.
9. U. Jaramillo-Toral et al., "Analog Blocks for 8-Bit SAR ADC: Rail-to-Rail Comparator and Two-Stage Operational Amplifier Designed with Open-Source Tools and Sky130 PDK," APCCAS, pp. 1-5, 2025. https://doi.org/10.1109/apccas67402.2025.11378356
   - Numbers: none in the abstract (abstract, p. 1).
   - Relevance: the same application (an opamp for an 8-bit SAR) in an open 130 nm PDK.
10. S. Suarez et al., "A Python-Based Semi-Automatic Layout Generation Flow for Multiple Folded-Cascode Designs in an Open-Source Environment," SBCCI, pp. 1-5, 2026. https://doi.org/10.1109/sbcci69725.2026.11706768
    - Numbers (abstract, p. 1, GF180): "four different Folded-Cascode OTA designs, operating at 1.8 V and 3.3 V"; generation times are "within tens to hundreds of seconds".
    - Relevance: parameterized placement matrices for folded cascodes in an open PDK. The abstract gives no schematic-to-extracted numbers.
11. N. Czepl, D. Zupan, "Noise Behaviour of EMI Improved Folded Cascode Amplifier Input Stages Including Layout Parasitics," Austrochip, pp. 1-4, 2021. https://doi.org/10.1109/austrochip53290.2021.9576855
    - Numbers: "seven EMI improved differential input pair structures" compared at the design and layout stages (abstract, p. 1).
    - Relevance: a design-to-layout comparison for folded-cascode input stages.
12. N. Karmokar, M. Madhusudan, A. K. Sharma, R. Harjani, M. P.-H. Lin, S. S. Sapatnekar, "Common-Centroid Layout for Active and Passive Devices: A Review and the Road Ahead," ASP-DAC, pp. 114-121, 2022. https://doi.org/10.1109/asp-dac52403.2022.9712576
    - Numbers: none. The abstract says CC layout must account for "routing parasitics, layout-dependent effects" and "examines scenarios where non-CC layouts may be preferable" (abstract, p. 114).
    - Relevance: this is exactly the question of which placement style to use.

## Not verified (Crossref record only, no number)

13. H. Habal, H. Graeb, "Constraint-Based Layout-Driven Sizing of Analog Circuits," IEEE TCAD, vol. 30, no. 8, pp. 1089-1102, 2011. https://doi.org/10.1109/tcad.2011.2158732
14. N. Lourenco, R. Martins, N. Horta, "Layout-Aware Sizing of Analog ICs using Floorplan & Routing Estimates for Parasitic Extraction," DATE, pp. 1156-1161, 2015. https://doi.org/10.7873/date.2015.0411
15. N. Lourenco, R. Martins, A. Canelas, R. Povoa, N. Horta, "AIDA: Layout-aware analog circuit-level sizing with in-loop layout generation," Integration, vol. 55, pp. 316-329, 2016. https://doi.org/10.1016/j.vlsi.2016.04.009
16. T. Liao, L. Zhang, "Layout-dependent effects aware gm/iD-based many-objective sizing optimization for analog integrated circuits," ISCAS, pp. 1-5, 2018. https://doi.org/10.1109/iscas.2018.8351431
17. E. Chang et al., "BAG2: A process-portable framework for generator-based AMS circuit design," CICC, pp. 1-8, 2018. https://doi.org/10.1109/cicc.2018.8357061
18. K. Kunal et al., "ALIGN," Proc. 56th DAC, pp. 1-4, 2019. https://doi.org/10.1145/3316781.3323471 (the title as the Crossref record gives it)

## Gap (one sentence)

In the abstracts read, the IHP SG13G2 and other open-PDK opamp work (4, 5, 6, 9, 10) stops at schematic sizing or at a single layout, and layout-aware sizing (13 to 16) is not verified here. No source found reports how a gm/Id-sized folded cascode shifts from schematic to extracted netlist across more than one placement style, at PVT corners, in IHP SG13G2. This rests on abstracts only, so 13 to 16 must be read before it is called a gap.

## Proposed claim (fixed before any run)

- **Claim:** the gm/Id sizing survives layout, and the placement style is a second-order effect.
- **Metric:** phase margin and GBW of the beta = 0.5 loop with the 2.05 pF load, from the project's post_layout target, compared with the schematic run on the same sizes and corner.
- **Styles compared:**
  - (a) the current one: ABBA common-centroid input pair and mirror, alternating folded pair;
  - (b) the same devices placed in netlist order with no centroid;
  - (c) each matched pair split into two single blocks side by side.
- **Baseline:** the schematic (no parasitics) at each of the project's fixed corners.
- **Pass:** for style (a), at every corner on the project's list:
  - the worst phase-margin drop (schematic minus extracted) is <= 5 deg;
  - the worst GBW drop is <= 10%;
  - the extracted design still meets PM >= 60 deg and GBW >= 20 MHz from chip.md.
- **Placement effect:** if the worst phase-margin drop of (a), (b) and (c) differs by less than 2 deg, the result is the null "placement style does not matter for this sizing", and it is reported as such.
- **Monte Carlo:** 200 seeds at tt 27 on the extracted netlist for style (a), with yield on PM >= 60 deg stated with its one-sided 95% lower bound. The PDK's mismatch model has no spatial gradient, so MC cannot separate the styles; only the extracted parasitics can.
- **Fail:** any corner breaks the 5 deg, 10% or spec limits above.
