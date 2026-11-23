<!-- Draft related-work survey for bandgap_ldo (trim resolution against Monte Carlo yield, and the capacitor-less LDO); not yet reviewed. -->
# bandgap_ldo: related work (draft)

## How the sources were checked

- Each citation below was taken from the DOI's Crossref record (https://api.crossref.org/works/DOI). Greek letters are written in ASCII (u for micro).
- "Abstract" means the abstract was read in the Semantic Scholar record for the same DOI. No full text could be opened; the publisher copies could not be opened.
- Numbers are quoted as the abstract states them. The page given is the paper's first page, or its article number.
- "Not verified" means only the Crossref record was opened, so no number is given.

## Verified (abstract read)

1. J.-H. Boo et al., "A Single-Trim Switched Capacitor CMOS Bandgap Reference With a 3sigma Inaccuracy of +0.02%, -0.12% for Battery-Monitoring Applications," IEEE JSSC, vol. 56, no. 4, pp. 1197-1206, 2021. https://doi.org/10.1109/jssc.2020.3044165
   - Numbers (abstract, p. 1197, 0.18 um CMOS):
     - vertical PNP "beta of about 2.7 at 27 °C";
     - "3sigma inaccuracy of +0.02%, -0.12% from -40 °C to 125 °C";
     - "17 uA at 27 °C" from "1.8-V";
     - "0.38 mm2".
   - Relevance: removes the non-PTAT errors so that one room-temperature trim suffices.
2. A. Sakr, M. Atef Hassan, J. Anders, "A PVT-Tolerant, Curvature-Compensated CMOS Bandgap-Based Current Reference With Single-Point Batch Trim," IEEE OJ-SSCS, vol. 5, pp. 470-480, 2025. https://doi.org/10.1109/ojsscs.2025.3633660
   - Numbers (abstract, p. 470, 130-nm SOI CMOS):
     - "0.016 mm2", "1.6 to 3 V";
     - "Measurements from 10 chips yield a mean current of 1.1 uA", with sigma/mu given as about 4.4%;
     - "average TC of 110 ppm/°C from 0 °C to 100 °C without multitemperature trimming".
   - Relevance: the same node class; it targets trimming cost.
3. A. Aprile, M. Folz, D. Gardino, P. Malcovati, E. Bonizzoni, "A One-Point Exponential Trimming Technique for an Effective Suppression of Process Spread in BJT-based Temperature Processing Circuits," ISCAS, 2022 (no page numbers in the Crossref record). https://doi.org/10.1109/iscas48785.2022.9937631
   - Numbers (abstract, first page): "a 6-bit trimming circuit", "180-nm CMOS", "a reduction of the considered spread of about 90%" (simulated).
   - Relevance: it relates trim word width to the spread left after trim, which is the same question as here.
4. O. Bass, A. Feldman, J. Shor, "A Resistor-Less nW-Level Bandgap Reference With Fine-Grained Voltage and Temperature Coefficient Trims," IEEE OJCAS, vol. 3, pp. 192-198, 2022. https://doi.org/10.1109/ojcas.2022.3206326
   - Numbers (abstract, p. 192): "38nW", "0.0174 mm2"; TC trimmable "between 50-200 ppm/°C in either direction"; voltage trimmable "between 580-800mV".
   - Node: not stated in the abstract.
   - Relevance: separate voltage and TC trims, where this design has one trim that moves both.
5. V. McKinsey et al., "A Node Agnostic Methodology for Optimizing Reference Circuit Designs," MWSCAS, pp. 710-714, 2025. https://doi.org/10.1109/mwscas53549.2025.11244560
   - Numbers (abstract, p. 710):
     - "0.000723 mm2";
     - "worst case TC of 73.0 ppm/°C over -40 °C to 125 °C for a 1.8 V ± 10% supply without trimming";
     - "yield for all parameters ... greater than 95% (p=0.01, n=500)".
   - Node: not stated in the abstract.
   - Relevance: the same temperature range, with Monte Carlo yield stated with a confidence level.
6. Y. Weng, J. Pan, Y. Zhao, J. Jiang, L. Qi, "A 2.3-ppm/°C High-Order Compensated Bandgap Reference With Low-Cost Current Trimming," ISCAS, pp. 1-5, 2024. https://doi.org/10.1109/iscas58744.2024.10558263
   - Numbers (abstract, p. 1, 180nm BCD, post-layout simulation):
     - "TC is lower than 2.3 ppm/°C" from "-40℃ to 125℃";
     - "PSRR of -69dB at 100Hz";
     - "383 um x 259 um", with the trim circuit taking "16%".
   - Relevance: the area cost of the trim network.
7. E. Nageib, S. Ibrahim, M. Dessouky, "Resistor Variation Compensation for Enhanced Current Matching in Bandgap References," Electronics, vol. 14, no. 19, art. 3808, 2025. https://doi.org/10.3390/electronics14193808
   - Numbers (abstract, art. 3808): current variation reduced "from 21% to 3% in worst-case corners (±3%)".
   - Node: not stated in the abstract.
   - Relevance: resistor spread, which is what the 16-tap R2 trim corrects here.
8. J. Wang, F. Zhang, Z. He, H. Zhang, L. Cheng, "A 2.69 ppm/°C bandgap reference with 42 ppm/V line sensitivity for battery management system," J. Semicond., vol. 46, no. 6, art. 062203, 2025. https://doi.org/10.1088/1674-4926/24120045
   - Numbers (abstract, art. 062203, 180 nm):
     - "average TC of 2.69 ppm/°C with two-point trimming and 0.81 ppm/°C with multi-point trimming" over "-40 to 125 °C";
     - "84 uA" from "5 V";
     - "0.548 mm²".
   - Relevance: TC against the number of trim points.
9. K. M. Canonero et al., "Design of a Bandgap Voltage Reference for an 8-bit SAR-ADC for Powerline Monitoring using SKY130 PDK," ICICM, pp. 427-432, 2025. https://doi.org/10.1109/icicm66614.2025.11315948
   - Numbers (abstract, p. 427, simulation):
     - "temperature coefficient of 19.3 ppm/°C";
     - "line sensitivity of 6.7%", "PSRR of 23.89 dB";
     - output "within 1.16 V to 1.25 V" over corners;
     - "257.47 uW".
   - Relevance: an open-PDK bandgap feeding an 8-bit SAR, the same use as here.
10. Y. Li, X. Ni, S. Achour, B. Murmann, "Open-ALOE: An Analog Layout Automation Flow for the Open-Source Ecosystem," ISQED, pp. 1-6, 2025. https://doi.org/10.1109/isqed65160.2025.11014456
    - Numbers (abstract, p. 1, SKY130, fabricated bandgap): "a voltage error of 7.8 mV".
    - Relevance: a measured open-PDK bandgap.
11. D. Arevalos, J. Marin, K. Herman, C. A. Rojas, "Leveraging Lookup Tables for Efficient LDO Design Exploration using Open-Source CAD Tools and IHP-Open130-G2 PDK," MIXDES, pp. 124-129, 2024. https://doi.org/10.23919/mixdes62605.2024.10614033
    - Numbers: none in the abstract (abstract, p. 124).
    - Relevance: an LDO in the same open PDK.
12. Y. Lu, M. Chen, K. Wang, Y. Yang, H. Wang, "A Capacitorless Flipped Voltage Follower LDO with Fast Transient Using Dynamic Bias," Electronics, vol. 11, no. 19, art. 3009, 2022. https://doi.org/10.3390/electronics11193009
    - Numbers (abstract, art. 3009, 0.18 um, simulation):
      - "recovery time is 52 ns when the load changes from 0.1 mA to 20 mA";
      - "quiescent current is 92 uA with 1 V regulated output";
      - "undershoot and overshoot voltage are 242 mV and 250 mV".
    - Relevance: the capacitor-less transient trade-off behind chip.md's LDO targets.

## Not verified (Crossref record only, no number)

13. V. Gupta, G. A. Rincon-Mora, "Predicting and Designing for the Impact of Process Variations and Mismatch on the Trim Range and Yield of Bandgap References," ISQED, pp. 503-508, 2005. https://doi.org/10.1109/isqed.2005.99
14. G. Ge, C. Zhang, G. Hoogzaad, K. A. A. Makinwa, "A Single-Trim CMOS Bandgap Reference With a 3sigma Inaccuracy of ±0.15% From -40°C to 125°C," IEEE JSSC, vol. 46, no. 11, pp. 2693-2701, 2011. https://doi.org/10.1109/jssc.2011.2165235
15. D. Adjei, B. Gadogbe, D. Chen, R. Geiger, "Novel Single-Temperature Trim Techniques for Bandgap Voltage References," MWSCAS, pp. 683-687, 2024. https://doi.org/10.1109/mwscas60917.2024.10658732
16. N. Ekekwe, R. Etienne-Cummings, "A 5-bits precision CMOS bandgap reference with on-chip bi-directional resistance trimming," MWSCAS, pp. 257-260, 2008. https://doi.org/10.1109/mwscas.2008.4616785
17. R. Paul, A. Patra, "Trimming process and temperature variation in second-order bandgap voltage reference circuits," Microelectronics J., vol. 42, no. 2, pp. 271-276, 2011. https://doi.org/10.1016/j.mejo.2010.10.006
18. K. N. Leung, P. K. T. Mok, "A capacitor-free CMOS low-dropout regulator with damping-factor-control frequency compensation," IEEE JSSC, vol. 38, no. 10, pp. 1691-1702, 2003. https://doi.org/10.1109/jssc.2003.817256
19. R. J. Milliken, J. Silva-Martinez, E. Sanchez-Sinencio, "Full On-Chip CMOS Low-Dropout Voltage Regulator," IEEE TCAS-I, vol. 54, no. 9, pp. 1879-1890, 2007. https://doi.org/10.1109/tcsi.2007.902615
20. P. Hazucha et al., "Area-efficient linear regulator with ultra-fast load regulation," IEEE JSSC, vol. 40, no. 4, pp. 933-940, 2005. https://doi.org/10.1109/jssc.2004.842831

## Gap (one sentence)

No clear gap was found. Trim range against yield is the exact title of 13, and trim width against residual spread is studied in 3, 4 and 8, so a new method cannot be claimed without reading 13 first.

Change of angle: a reproducible answer, in IHP SG13G2's open PDK and with its vertical PNP and rppd Monte Carlo models, to "how many trim bits does a -40 to 125 C, 30 ppm/C box-method spec need?". The answer would be stated with seed count and confidence bound, and none of the open-PDK references (9 to 11) report it.

## Proposed claim (fixed before any run)

- **Claim:** 4 trim bits (16 taps on R2) is the minimum that meets the chip.md tempco spec in Monte Carlo, and 3 bits is not enough.
- **Metric:** box-method tempco from -40 to 125 C after choosing the tap per Monte Carlo run by a single room-temperature rule: the tap whose vref at 27 C is closest to the nominal design's vref at 27 C (a single-trim rule, as in items 1 and 14; picking the tap by full tempco would be an oracle). The rule is proposed here and is for the lead to approve. The fraction of runs at or under 30 ppm/C is the yield.
- **Ablation:**
  - 3 bits: every second tap only;
  - 2 bits: every fourth tap;
  - 0 bits: the nominal tap fixed.
  - All are taken from the same runs, so no extra simulation is needed per width.
- **Baseline:** the untrimmed design (nominal tap) in the same runs.
- **Seeds:** 300 Monte Carlo seeds at tt 27. With 0 failures in 300, the one-sided 95% lower bound on yield is 0.990.
- **Pass:** at 4 bits, the one-sided 95% lower bound on yield >= 99%; at 3 bits, the same lower bound < 99%.
- **Corners:** every corner on the project's fixed list is checked at the tap the same rule picks, at 4 bits and at 3 bits.
- **Fail:**
  - if 3 bits also reaches a lower bound of 99%, the claim is false and the minimum is lower (a positive result: a cheaper trim);
  - if 4 bits misses, the claim is false and the design needs more resolution.
