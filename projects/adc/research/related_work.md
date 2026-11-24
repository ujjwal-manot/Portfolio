<!-- Draft related-work survey for the adc (unit-capacitor placement in the 8-bit MIM cap DAC); not yet reviewed. -->
# adc: related work (draft)

## How the sources were checked

- Each citation below was taken from the DOI's Crossref record (https://api.crossref.org/works/DOI). Greek letters are written in ASCII (u for micro).
- "Abstract" means the abstract was read in the Semantic Scholar record for the same DOI. No full text could be opened; the publisher and repository copies could not be opened.
- Numbers are quoted as the abstract states them. The page given is the paper's first page, or its article number.
- One entry (8) is quoted from B. Murmann, "ADC Performance Survey 1997-2026," https://github.com/bmurmann/ADC-survey (local copy: third_party/adc-survey, file xls/ADCsurvey_latest.xlsx, commit 00b4b855). Those numbers are the survey's, not read from the paper.
- "Not verified" means only the Crossref record was opened, so no number is given.

## Verified (abstract read, or survey row)

1. N. Karmokar, A. K. Sharma, J. Poojary, M. Madhusudan, R. Harjani, S. S. Sapatnekar, "Constructive Placement and Routing for Common-Centroid Capacitor Arrays in Binary-Weighted and Split DACs," IEEE TCAD, vol. 42, no. 9, pp. 2782-2795, 2023. https://doi.org/10.1109/tcad.2023.3238880
   - Numbers: none in the abstract. It trades "via counts with dispersion" between 3-dB frequency and "DAC INL/DNL", targeting FinFET nodes (abstract, p. 2782).
   - Relevance: CC placement scored by INL/DNL together with the routing parasitics.
2. N. Karmokar et al., "Constructive Common-Centroid Placement and Routing for Binary-Weighted Capacitor Arrays," DATE, pp. 166-171, 2022. https://doi.org/10.23919/date54114.2022.9774640
   - Numbers: none in the abstract (abstract, p. 166).
   - Relevance: the conference version of 1.
3. N. Karmokar, M. Madhusudan, A. K. Sharma, R. Harjani, M. P.-H. Lin, S. S. Sapatnekar, "Common-Centroid Layout for Active and Passive Devices: A Review and the Road Ahead," ASP-DAC, pp. 114-121, 2022. https://doi.org/10.1109/asp-dac52403.2022.9712576
   - Numbers: none. The abstract says the best CC layout depends on "the relative impact of uncorrelated and systematic variations" and that non-CC layouts may sometimes be preferable (abstract, p. 114).
   - Relevance: it frames the ruler versus row-major versus spiral question.
4. M. Liu, X. Tang, K. Zhu, H. Chen, N. Sun, D. Z. Pan, "OpenSAR: An Open Source Automated End-to-end SAR ADC Compiler," ICCAD, pp. 1-9, 2021. https://doi.org/10.1109/iccad51958.2021.9643494
   - Numbers: none in the abstract. Its CDAC generator "interleaves capacitor rows and columns to reduce process gradient mismatch" (abstract, p. 1).
   - Relevance: an open SAR flow with its own placement rule, checked post-layout.
5. A. Olyanasab, P. Fath, L. Schreiner, C. Guger, H. Pretl, "An 8.1-uW 12-bit Non-Binary Self-Clocked SAR-ADC in 130 nm Open-Source PDK," Austrochip, pp. 45-48, 2025. https://doi.org/10.1109/austrochip67945.2025.11183685
   - Numbers (abstract, p. 45, SKY130, measured):
     - "2 kS/s", "OSR = 16", "8.1 uW";
     - "SNR, SNDR, and ENOB are 73.9 dB, 71.1 dB, and 11.5 bit";
     - layout size "0.214 um2", as printed in the abstract.
   - Relevance: a silicon SAR in an open 130 nm PDK.
6. D. M. Ellaithy, "A low-power 8-bit 1-MS/s single-ended SAR ADC in 130-nm CMOS for medical devices," J. Electr. Syst. Inf. Technol., vol. 11, art. 21, 2024. https://doi.org/10.1186/s43067-024-00147-z
   - Numbers (abstract, art. 21): "8-bit resolution at a sampling rate of 1 MS/s", "130-nm CMOS", "1.2 V supply", "ENOB ... of 7.3 dB" (unit as printed), "28.5 uW", "197 um x 377 um".
   - Relevance: the same resolution, rate and node as this ADC.
7. X. Yue, "Determining the reliable minimum unit capacitance for the DAC capacitor array of SAR ADCs," Microelectronics J., vol. 44, no. 6, pp. 473-478, 2013. https://doi.org/10.1016/j.mejo.2013.03.011
   - Numbers (abstract, p. 473): for a 10-bit DAC, "the matching error is 7 times bigger" than thermal noise, which "consumes 1/8 error budget"; validated with "an 89.44 fF poly-poly unit capacitor in the 0.35 um CMOS process".
   - Relevance: unit-size choice set by matching (here 7.95 fF MIM).
8. M. van Elzakker, E. van Tuijl, P. Geraedts, D. Schinkel, E. Klumperink, B. Nauta, "A 1.9uW 4.4fJ/Conversion-step 10b 1MS/s Charge-Redistribution ADC," ISSCC, pp. 244-610 (Crossref page field), 2008. https://doi.org/10.1109/isscc.2008.4523148
   - Numbers: the title (Crossref) gives 1.9 uW, 4.4 fJ/conversion-step, 10b, 1 MS/s. The survey (sheet ISSCC, row 163) lists 0.065 um, SNDR_hf 54.4 dB, Csamp 0.5 pF and area 0.0275 mm^2.
   - Relevance: an energy anchor for a 1 MS/s charge-redistribution SAR.
9. D. Khalil, M. Dessouky, V. Bourguet, M. Louerat, A. Cathelin, H. Ragai, "Evaluation of Capacitor Ratios in Automated Accurate Common-Centroid Capacitor Arrays," ISQED, pp. 143-147, 2005. https://doi.org/10.1109/isqed.2005.54
   - Numbers: none. A test chip compares layout techniques for unit-capacitor arrays; the abstract reports "significant improvements in ratio accuracy" from automatic CC (abstract, p. 143).
   - Relevance: measured silicon evidence that placement matters (node not stated in the abstract).
10. S. Bae, S. Lee, S. Seong, S. Kong, B. Park, M. Lee, "A 13-Bit 1-MS/s SAR ADC With Completion-Aware Background Capacitor Mismatch Calibration," IEEE Access, vol. 11, pp. 104323-104332, 2023. https://doi.org/10.1109/access.2023.3317888
    - Numbers (abstract, p. 104323, 55 nm): "1 MS/s", "43 uW", "peak DNL of +0.83/-0.62 LSB and INL of +1.89/-1.13 LSB", "SNDR of 68.5 dB", "FoM of 19.59 fJ/conv.-step".
    - Relevance: the alternative to placement, calibrating the mismatch.

## Not verified (Crossref record only, no number)

11. C.-W. Lin, J.-M. Lin, Y.-C. Chiu, C.-P. Huang, S.-J. Chang, "Common-centroid capacitor placement considering systematic and random mismatches in analog integrated circuits," DAC, pp. 528-533, 2011. https://doi.org/10.1145/2024724.2024847
12. C.-W. Lin et al., "Mismatch-Aware Common-Centroid Placement for Arbitrary-Ratio Capacitor Arrays Considering Dummy Capacitors," IEEE TCAD, vol. 31, no. 12, pp. 1789-1802, 2012. https://doi.org/10.1109/tcad.2012.2204993
13. M. P.-H. Lin, V. W.-H. Hsiao, C.-Y. Lin, N.-C. Chen, "Parasitic-Aware Common-Centroid Binary-Weighted Capacitor Layout Generation Integrating Placement, Routing, and Unit Capacitor Sizing," IEEE TCAD, vol. 36, no. 8, pp. 1274-1286, 2017. https://doi.org/10.1109/tcad.2017.2685598
14. P.-W. Luo et al., "Impact of Capacitance Correlation on Yield Enhancement of Mixed-Signal/Analog Integrated Circuits," IEEE TCAD, vol. 27, no. 11, pp. 2097-2101, 2008. https://doi.org/10.1109/tcad.2008.2006139
15. D. Sayed, M. Dessouky, "Automatic generation of common-centroid capacitor arrays with arbitrary capacitor ratio," DATE, pp. 576-580, 2002. https://doi.org/10.1109/date.2002.998358
16. V. Tripathi, B. Murmann, "Mismatch Characterization of Small Metal Fringe Capacitors," IEEE TCAS-I, vol. 61, no. 8, pp. 2236-2242, 2014. https://doi.org/10.1109/tcsi.2014.2332264
17. H. Omran, H. Alahmadi, K. N. Salama, "Matching Properties of Femtofarad and Sub-Femtofarad MOM Capacitors," IEEE TCAS-I, vol. 63, no. 6, pp. 763-772, 2016. https://doi.org/10.1109/tcsi.2016.2537824
18. H. Tuinhout, N. Wils, "A cross-coupled common centroid test structures layout method for high precision MIM capacitor mismatch measurements," ICMTS, pp. 243-248, 2014. https://doi.org/10.1109/icmts.2014.6841500
19. C.-C. Liu, S.-J. Chang, G.-Y. Huang, Y.-Z. Lin, "A 10-bit 50-MS/s SAR ADC With a Monotonic Capacitor Switching Procedure," IEEE JSSC, vol. 45, no. 4, pp. 731-740, 2010. https://doi.org/10.1109/jssc.2010.2042254
20. P. J. A. Harpe et al., "A 26 uW 8 bit 10 MS/s Asynchronous SAR ADC for Low Energy Radios," IEEE JSSC, vol. 46, no. 7, pp. 1585-1595, 2011. https://doi.org/10.1109/jssc.2011.2143870

## Gap (one sentence)

CC placement of binary capacitor arrays is a mature CAD topic (1 to 3, 9, 11 to 15), with the abstracts read scoring it by dispersion and INL/DNL (1, 2, FinFET-targeted) or by measured ratio accuracy (9). No source found compares ruler-ordered CC, row-major and spiral placement by post-layout INL/DNL and Monte Carlo yield of an 8-bit MIM DAC in IHP SG13G2. At 8 bits with 7.95 fF MIM units the true effect may be close to zero, so the useful contribution may be a measured null result.

## Proposed claim (fixed before any run)

- **Claim:** at 8 bits in IHP SG13G2, the ruler-ordered common-centroid MIM array gives lower post-layout INL than row-major placement, and spiral placement falls between the two.
- **Metric:** worst |INL| and worst |DNL| in LSB, from the project's levels or convert targets run on the extracted cap DAC (post_layout), plus the Monte Carlo yield on DNL within +-0.5 LSB and INL within +-1 LSB from chip.md.
- **Styles compared:**
  - (a) ruler order, the current layout/adc_core.py;
  - (b) row-major: units assigned bit by bit, filling rows from one corner;
  - (c) spiral: units assigned by distance from the centre, bit 7 innermost.
  - Same unit, same pitch, same routing rules.
- **Baseline:** row-major (b) in the same flow, at the same corners.
- **Pass:**
  - (a) improves worst |INL| over (b) by at least 0.1 LSB at tt 27 and at every corner on the project's post_layout list;
  - and the MC yield lower bound of (a) is not below that of (b).
  - 200 seeds at tt 27, yield with its one-sided 95% lower bound.
- **Null:** if the INL difference between styles stays under 0.1 LSB everywhere, the result is the null "placement does not matter at this resolution and unit size", and it is reported as such.
- **Caveat:** if the PDK's MIM mismatch model draws each unit independently with no spatial gradient (to be confirmed in the PDK model files before the run), any difference in this flow comes only from extracted routing capacitance. A gradient study would need a measured IHP MIM gradient, and none was found in the sources opened.
