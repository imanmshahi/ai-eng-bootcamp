# Traces v1

20 questions from `evals/questions_v1.txt` run against local `POST /ask`.
Retrieval shown is `POST /search` with `k=5`, the same `k` `/ask` uses internally,
so the chunks listed are the ones the answer was generated from.

No pass/fail judgement is recorded here - these are raw observations.

---

## q01

**Question**

> Under RED Article 25, what obligation must each Member State place on fuel suppliers?

**Answer**

Each Member State must set an obligation on fuel suppliers to ensure that the amount of renewable fuels and renewable electricity supplied to the transport sector leads to a share of renewable energy within the final consumption of energy in the transport sector of at least 29% by 2030, or a greenhouse gas intensity reduction of at least 14.5% by 2030, compared to the baseline set out in Article 27(1), point (b) [RED3-ART25#0000].

| | |
| --- | --- |
| refused | `False` |
| citations | `RED3-ART25#0000` |
| tokens_used | 1016 |

**Retrieved (k=5)**

| # | chunk | score | cited | text |
| --- | --- | --- | --- | --- |
| 1 | `RED3-ART25#0000` | 0.6268 | yes | # Renewable Energy Directive (RED), Directive (EU) 2018/2001, Art. 25 - consolidated version dated 16/07/2024 (CELEX 02018L2001-20240716, as amended by Directive (EU) 2023/2413 'RE |
| 2 | `RED3-ART25#0006` | 0.6001 |  | on set by the Member State on fuel suppliers, and may sell those credits to fuel suppliers, which shall be allowed to use the credits to fulfil the obligation set out in paragraph  |
| 3 | `RED3-ART25#0005` | 0.5978 |  | s and biogas produced from the feedstock listed in Part A of Annex IX with respect to those fuels; (b) set the obligation by means of measures targeting volumes, energy content or  |
| 4 | `RED3-ART25#0004` | 0.5472 |  | d that the greenhouse gas emissions reduction achieved by the use of renewable fuels of non-biological origin is not counted in the calculation of the greenhouse gas emissions savi |
| 5 | `REFUELEU-ART4#0000` | 0.5470 |  | # ReFuelEU Aviation, Regulation (EU) 2023/2405 of 18 October 2023, Art. 4 + Annex I - original OJ text, CELEX 32023R2405, no consolidation applied (retrieved from EUR-Lex 2026-10-1 |

---

## q02

**Question**

> What must aviation fuel suppliers ensure about the aviation fuel they make available at each Union airport?

**Answer**

Aviation fuel suppliers must ensure that all aviation fuel made available to aircraft operators at each Union airport contains the minimum shares of sustainable aviation fuel (SAF), including the minimum shares of synthetic aviation fuel, according to the values and dates of application set out in Annex I. Additionally, over the periods from 1 January 2030 until 31 December 2031 and from 1 January 2032 until 31 December 2034, aviation fuel suppliers must ensure that all aviation fuel contains at least the average shares of synthetic aviation fuels as specified [REFUELEU-ART4#0000][REFUELEU-ART4#0001].

| | |
| --- | --- |
| refused | `False` |
| citations | `REFUELEU-ART4#0000`, `REFUELEU-ART4#0001` |
| tokens_used | 1216 |

**Retrieved (k=5)**

| # | chunk | score | cited | text |
| --- | --- | --- | --- | --- |
| 1 | `REFUELEU-ART4#0000` | 0.6302 | yes | # ReFuelEU Aviation, Regulation (EU) 2023/2405 of 18 October 2023, Art. 4 + Annex I - original OJ text, CELEX 32023R2405, no consolidation applied (retrieved from EUR-Lex 2026-10-1 |
| 2 | `REFUELEU-ART4#0001` | 0.5902 | yes | Union airport over the periods from 1 January 2030 until 31 December 2031 and from 1 January 2032 until 31 December 2034 contains at least the average shares of synthetic aviation  |
| 3 | `REFUELEU-ART4#0005` | 0.5846 |  | where an aviation fuel supplier fails to supply the minimum shares set out in Annex I for a given reporting period, it shall at least complement that shortfall in the subsequent re |
| 4 | `REFUELEU-ART4#0003` | 0.5788 |  | erring also to low-carbon aviation fuels and to renewable hydrogen for aviation. 4. For each reporting period, aviation biofuels other than advanced biofuels as defined in Article  |
| 5 | `REFUELEU-ART4#0002` | 0.5734 |  | 7(2), points (f) and (g) of, and Annex III to, Directive (EU) 2018/2001 or relevant international aviation standards regarding fuels not included in that Annex; and (b) the energy  |

---

## q03

**Question**

> Which feedstocks are excluded from the calculation of the minimum shares of SAF?

**Answer**

The feedstocks excluded from the calculation of the minimum shares of SAF are: ‘food and feed crops’ as defined in Article 2, second paragraph, point (40), of Directive (EU) 2018/2001, and SAF produced from the feedstock listed in Part B of Annex IX to that Directive [REFUELEU-ART4#0003].

| | |
| --- | --- |
| refused | `False` |
| citations | `REFUELEU-ART4#0003` |
| tokens_used | 1196 |

**Retrieved (k=5)**

| # | chunk | score | cited | text |
| --- | --- | --- | --- | --- |
| 1 | `REFUELEU-ART4#0004` | 0.6667 |  | s of SAF set out in Annex I to this Regulation: ‘food and feed crops’ as defined in Article 2, second paragraph, point (40), of Directive (EU) 2018/2001, intermediate crops, palm f |
| 2 | `REFUELEU-ART4#0006` | 0.6411 |  | nt reporting period. ANNEX I Shares of SAF referred to in Article 4 (a) From 1 January 2025, each year a minimum share of 2 % of SAF; (b) From 1 January 2030, each year a minimum s |
| 3 | `REFUELEU-ART4#0003` | 0.6244 | yes | erring also to low-carbon aviation fuels and to renewable hydrogen for aviation. 4. For each reporting period, aviation biofuels other than advanced biofuels as defined in Article  |
| 4 | `REFUELEU-ART4#0000` | 0.6098 |  | # ReFuelEU Aviation, Regulation (EU) 2023/2405 of 18 October 2023, Art. 4 + Annex I - original OJ text, CELEX 32023R2405, no consolidation applied (retrieved from EUR-Lex 2026-10-1 |
| 5 | `REFUELEU-ART4#0005` | 0.6051 |  | where an aviation fuel supplier fails to supply the minimum shares set out in Annex I for a given reporting period, it shall at least complement that shortfall in the subsequent re |

---

## q04

**Question**

> What happens if an aviation fuel supplier fails to supply the minimum shares for a given reporting period?

**Answer**

If an aviation fuel supplier fails to supply the minimum shares set out in Annex I for a given reporting period, it shall at least complement that shortfall in the subsequent reporting period. Exceptionally, if the supplier fails to supply the average shares of synthetic aviation fuel over the period from 1 January 2030 until 31 December 2031, it shall at least complement that shortfall before the end of the period from 1 January 2032 until 31 December 2034. Similarly, if the supplier fails to supply the average shares of synthetic aviation fuel over the period from 1 January 2032 until 31 December 2034, it shall complement that shortfall in the subsequent reporting period [REFUELEU-ART4#0005].

| | |
| --- | --- |
| refused | `False` |
| citations | `REFUELEU-ART4#0005` |
| tokens_used | 1275 |

**Retrieved (k=5)**

| # | chunk | score | cited | text |
| --- | --- | --- | --- | --- |
| 1 | `REFUELEU-ART4#0005` | 0.7488 | yes | where an aviation fuel supplier fails to supply the minimum shares set out in Annex I for a given reporting period, it shall at least complement that shortfall in the subsequent re |
| 2 | `REFUELEU-ART4#0006` | 0.5629 |  | nt reporting period. ANNEX I Shares of SAF referred to in Article 4 (a) From 1 January 2025, each year a minimum share of 2 % of SAF; (b) From 1 January 2030, each year a minimum s |
| 3 | `REFUELEU-ART4#0000` | 0.5529 |  | # ReFuelEU Aviation, Regulation (EU) 2023/2405 of 18 October 2023, Art. 4 + Annex I - original OJ text, CELEX 32023R2405, no consolidation applied (retrieved from EUR-Lex 2026-10-1 |
| 4 | `REFUELEU-ART4#0003` | 0.5522 |  | erring also to low-carbon aviation fuels and to renewable hydrogen for aviation. 4. For each reporting period, aviation biofuels other than advanced biofuels as defined in Article  |
| 5 | `REFUELEU-ART4#0001` | 0.5311 |  | Union airport over the periods from 1 January 2030 until 31 December 2031 and from 1 January 2032 until 31 December 2034 contains at least the average shares of synthetic aviation  |

---

## q05

**Question**

> What must a company present to Member State customs authorities to receive its individual anti-dumping duty rate?

**Answer**

A company must present a valid commercial invoice to the Member States’ customs authorities, on which shall appear a declaration dated and signed by an official of the entity issuing such invoice, stating that the biodiesel sold for export to the European Union was manufactured by the specified company in the People’s Republic of China [TRADE-BIODIESEL#0004].

| | |
| --- | --- |
| refused | `False` |
| citations | `TRADE-BIODIESEL#0004` |
| tokens_used | 1285 |

**Retrieved (k=5)**

| # | chunk | score | cited | text |
| --- | --- | --- | --- | --- |
| 1 | `TRADE-BIODIESEL#0004` | 0.5747 | yes | p: \| — Zhejiang EastRiver Energy S&T Co., Ltd \| — Zhejiang Jiaao Enproenergy Co., Ltd \| — Jiaao International Trading (SINGAPORE) PTE. Ltd \| 35,6 \| 89EE Zhuoyue Group: \| — Longyan  |
| 2 | `TRADE-BIODIESEL#0003` | 0.5660 |  | the following TARIC codes shall be subject to monitoring, in addition to the codes mentioned in paragraph 1 which were excluded from the scope of the measure: TARIC code 2710 19 11 |
| 3 | `TRADE-BIODIESEL#0005` | 0.5324 |  | such invoice, identified by name and function, drafted as follows: ‘I, the undersigned, certify that the (volume in tonnes) of biodiesel sold for export to the European Union cover |
| 4 | `TRADE-BIODIESEL#0000` | 0.3942 |  | # Biodiesel from China anti-dumping, Commission Implementing Regulation (EU) 2025/261, Art. 1 + Annex (cooperating exporting producers not sampled) - consolidated version dated 16/ |
| 5 | `TRADE-BIODIESEL#0021` | 0.3647 |  | ut feedstocks and the CFPP value, the Commission disagreed to the extent such information is not generally available at fuelling stations. 2.3. Conclusion (30) In the absence of an |

---

## q06

**Question**

> What credit exchange mechanism must Member States establish for fuel suppliers in the transport sector?

**Answer**

Member States must establish a mechanism allowing fuel suppliers in their territory to exchange credits for supplying renewable energy to the transport sector. Economic operators that supply renewable electricity to electric vehicles through public recharging points shall receive credits, irrespective of whether they are subject to the obligation set by the Member State on fuel suppliers. They may sell those credits to fuel suppliers, who shall be allowed to use the credits to fulfill the obligation set out in the directive [RED3-ART25#0005][RED3-ART25#0006].

| | |
| --- | --- |
| refused | `False` |
| citations | `RED3-ART25#0005`, `RED3-ART25#0006` |
| tokens_used | 996 |

**Retrieved (k=5)**

| # | chunk | score | cited | text |
| --- | --- | --- | --- | --- |
| 1 | `RED3-ART25#0005` | 0.7189 | yes | s and biogas produced from the feedstock listed in Part A of Annex IX with respect to those fuels; (b) set the obligation by means of measures targeting volumes, energy content or  |
| 2 | `RED3-ART25#0006` | 0.6794 | yes | on set by the Member State on fuel suppliers, and may sell those credits to fuel suppliers, which shall be allowed to use the credits to fulfil the obligation set out in paragraph  |
| 3 | `RED3-ART25#0002` | 0.5378 |  | el in order to fulfil the obligation set out in the first subparagraph, point (b), of this paragraph, in a way that the development of both fuels is promoted and expanded. Member S |
| 4 | `RED3-ART25#0004` | 0.5359 |  | d that the greenhouse gas emissions reduction achieved by the use of renewable fuels of non-biological origin is not counted in the calculation of the greenhouse gas emissions savi |
| 5 | `RED3-ART25#0000` | 0.5160 |  | # Renewable Energy Directive (RED), Directive (EU) 2018/2001, Art. 25 - consolidated version dated 16/07/2024 (CELEX 02018L2001-20240716, as amended by Directive (EU) 2023/2413 'RE |

---

## q07

**Question**

> What is the minimum share of synthetic aviation fuel required each year in 2030 and 2031?

**Answer**

The minimum share of synthetic aviation fuel required each year in 2030 is 0.7%, and in 2031 it is also 0.7% [REFUELEU-ART4#0006].

| | |
| --- | --- |
| refused | `False` |
| citations | `REFUELEU-ART4#0006` |
| tokens_used | 1160 |

**Retrieved (k=5)**

| # | chunk | score | cited | text |
| --- | --- | --- | --- | --- |
| 1 | `REFUELEU-ART4#0007` | 0.7801 |  | 2034 until 31 December 2034 of synthetic aviation fuels; (c) From 1 January 2035, each year a minimum share of 20 % of SAF, of which a minimum share of 5 % of synthetic aviation fu |
| 2 | `REFUELEU-ART4#0005` | 0.7253 |  | where an aviation fuel supplier fails to supply the minimum shares set out in Annex I for a given reporting period, it shall at least complement that shortfall in the subsequent re |
| 3 | `REFUELEU-ART4#0001` | 0.7148 |  | Union airport over the periods from 1 January 2030 until 31 December 2031 and from 1 January 2032 until 31 December 2034 contains at least the average shares of synthetic aviation  |
| 4 | `REFUELEU-ART4#0006` | 0.6791 | yes | nt reporting period. ANNEX I Shares of SAF referred to in Article 4 (a) From 1 January 2025, each year a minimum share of 2 % of SAF; (b) From 1 January 2030, each year a minimum s |
| 5 | `REFUELEU-ART4#0000` | 0.6646 |  | # ReFuelEU Aviation, Regulation (EU) 2023/2405 of 18 October 2023, Art. 4 + Annex I - original OJ text, CELEX 32023R2405, no consolidation applied (retrieved from EUR-Lex 2026-10-1 |

---

## q08

**Question**

> What definitive anti-dumping duty rate applies to the Jiaao Group?

**Answer**

The definitive anti-dumping duty rate applicable to the Jiaao Group is 35.6% [TRADE-BIODIESEL#0004].

| | |
| --- | --- |
| refused | `False` |
| citations | `TRADE-BIODIESEL#0004` |
| tokens_used | 1233 |

**Retrieved (k=5)**

| # | chunk | score | cited | text |
| --- | --- | --- | --- | --- |
| 1 | `TRADE-BIODIESEL#0003` | 0.6659 |  | the following TARIC codes shall be subject to monitoring, in addition to the codes mentioned in paragraph 1 which were excluded from the scope of the measure: TARIC code 2710 19 11 |
| 2 | `TRADE-BIODIESEL#0004` | 0.5508 | yes | p: \| — Zhejiang EastRiver Energy S&T Co., Ltd \| — Zhejiang Jiaao Enproenergy Co., Ltd \| — Jiaao International Trading (SINGAPORE) PTE. Ltd \| 35,6 \| 89EE Zhuoyue Group: \| — Longyan  |
| 3 | `TRADE-BIODIESEL#0005` | 0.4417 |  | such invoice, identified by name and function, drafted as follows: ‘I, the undersigned, certify that the (volume in tonnes) of biodiesel sold for export to the European Union cover |
| 4 | `TRADE-BIODIESEL#0000` | 0.4020 |  | # Biodiesel from China anti-dumping, Commission Implementing Regulation (EU) 2025/261, Art. 1 + Annex (cooperating exporting producers not sampled) - consolidated version dated 16/ |
| 5 | `TRADE-BIODIESEL#0021` | 0.3933 |  | ut feedstocks and the CFPP value, the Commission disagreed to the extent such information is not generally available at fuelling stations. 2.3. Conclusion (30) In the absence of an |

---

## q09

**Question**

> What is the TARIC additional code for Tangshan Jinlihai Biodiesel Co., Ltd?

**Answer**

I don't have enough information in the provided documents to answer that.

| | |
| --- | --- |
| refused | `True` |
| citations | none |
| tokens_used | 1471 |

**Retrieved (k=5)**

| # | chunk | score | cited | text |
| --- | --- | --- | --- | --- |
| 1 | `TRADE-BIODIESEL#0002` | 0.6321 |  | 92 14 and 3824 99 92 17 ), 3826 00 10 and ex 3826 00 90 (TARIC codes 3826 00 90 11 , 3826 00 90 19 and 3826 00 90 33 ), excluding sustainable aviation fuels meeting the requirement |
| 2 | `TRADE-BIODIESEL#0003` | 0.6087 |  | the following TARIC codes shall be subject to monitoring, in addition to the codes mentioned in paragraph 1 which were excluded from the scope of the measure: TARIC code 2710 19 11 |
| 3 | `TRADE-BIODIESEL#0001` | 0.5848 |  | luded in a blend, currently falling under CN codes ex 1516 20 98 (TARIC codes 1516 20 98 21 , 1516 20 98 29 and 1516 20 98 33 ), ex 1518 00 91 (TARIC codes 1518 00 91 21 , 1518 00  |
| 4 | `TRADE-BIODIESEL#0021` | 0.5783 |  | ut feedstocks and the CFPP value, the Commission disagreed to the extent such information is not generally available at fuelling stations. 2.3. Conclusion (30) In the absence of an |
| 5 | `TRADE-BIODIESEL#0005` | 0.5201 |  | such invoice, identified by name and function, drafted as follows: ‘I, the undersigned, certify that the (volume in tonnes) of biodiesel sold for export to the European Union cover |

---

## q10

**Question**

> What share of SAF applies from 1 January 2050, and how much of it must be synthetic aviation fuel?

**Answer**

From 1 January 2050, each year a minimum share of 70 % of SAF is required, of which a minimum share of 35 % must be synthetic aviation fuels [REFUELEU-ART4#0007].

| | |
| --- | --- |
| refused | `False` |
| citations | `REFUELEU-ART4#0007` |
| tokens_used | 1169 |

**Retrieved (k=5)**

| # | chunk | score | cited | text |
| --- | --- | --- | --- | --- |
| 1 | `REFUELEU-ART4#0007` | 0.8374 | yes | 2034 until 31 December 2034 of synthetic aviation fuels; (c) From 1 January 2035, each year a minimum share of 20 % of SAF, of which a minimum share of 5 % of synthetic aviation fu |
| 2 | `REFUELEU-ART4#0006` | 0.7730 |  | nt reporting period. ANNEX I Shares of SAF referred to in Article 4 (a) From 1 January 2025, each year a minimum share of 2 % of SAF; (b) From 1 January 2030, each year a minimum s |
| 3 | `REFUELEU-ART4#0000` | 0.7454 |  | # ReFuelEU Aviation, Regulation (EU) 2023/2405 of 18 October 2023, Art. 4 + Annex I - original OJ text, CELEX 32023R2405, no consolidation applied (retrieved from EUR-Lex 2026-10-1 |
| 4 | `REFUELEU-ART4#0005` | 0.7235 |  | where an aviation fuel supplier fails to supply the minimum shares set out in Annex I for a given reporting period, it shall at least complement that shortfall in the subsequent re |
| 5 | `REFUELEU-ART4#0001` | 0.6993 |  | Union airport over the periods from 1 January 2030 until 31 December 2031 and from 1 January 2032 until 31 December 2034 contains at least the average shares of synthetic aviation  |

---

## q11

**Question**

> What duty rate applies to cooperating companies listed in the Annex that were not sampled?

**Answer**

I don't have enough information in the provided documents to answer that.

| | |
| --- | --- |
| refused | `True` |
| citations | none |
| tokens_used | 1413 |

**Retrieved (k=5)**

| # | chunk | score | cited | text |
| --- | --- | --- | --- | --- |
| 1 | `TRADE-BIODIESEL#0004` | 0.5559 |  | p: \| — Zhejiang EastRiver Energy S&T Co., Ltd \| — Zhejiang Jiaao Enproenergy Co., Ltd \| — Jiaao International Trading (SINGAPORE) PTE. Ltd \| 35,6 \| 89EE Zhuoyue Group: \| — Longyan  |
| 2 | `TRADE-BIODIESEL#0003` | 0.5096 |  | the following TARIC codes shall be subject to monitoring, in addition to the codes mentioned in paragraph 1 which were excluded from the scope of the measure: TARIC code 2710 19 11 |
| 3 | `TRADE-BIODIESEL#0021` | 0.4770 |  | ut feedstocks and the CFPP value, the Commission disagreed to the extent such information is not generally available at fuelling stations. 2.3. Conclusion (30) In the absence of an |
| 4 | `TRADE-BIODIESEL#0001` | 0.4241 |  | luded in a blend, currently falling under CN codes ex 1516 20 98 (TARIC codes 1516 20 98 21 , 1516 20 98 29 and 1516 20 98 33 ), ex 1518 00 91 (TARIC codes 1518 00 91 21 , 1518 00  |
| 5 | `TRADE-BIODIESEL#0005` | 0.4184 |  | such invoice, identified by name and function, drafted as follows: ‘I, the undersigned, certify that the (volume in tonnes) of biodiesel sold for export to the European Union cover |

---

## q12

**Question**

> How does the 2030 renewable energy target for transport in RED Article 25 compare with the SAF share aviation fuel suppliers must reach from 2030?

**Answer**

The 2030 renewable energy target for transport in RED Article 25 specifies that each Member State shall ensure that the share of renewable energy within the final consumption of energy in the transport sector is at least 29% by 2030, or there must be a greenhouse gas intensity reduction of at least 14.5% by 2030 compared to a baseline [RED3-ART25#0000].

In comparison, aviation fuel suppliers are required to ensure that all aviation fuel made available at Union airports contains minimum shares of Sustainable Aviation Fuel (SAF). Specifically, from 1 January 2030 until 31 December 2031, aviation fuel must contain an average share of synthetic aviation fuels as outlined in Annex I, although the specific percentage for these years is not detailed in the provided excerpts [REFUELEU-ART4#0001]. 

Therefore, while both regulations set ambitious targets for renewable energy usage, they pertain to different sectors (transport at large vs. aviation specifically) and have different mechanisms and metrics for measuring compliance.

| | |
| --- | --- |
| refused | `False` |
| citations | `RED3-ART25#0000`, `REFUELEU-ART4#0001` |
| tokens_used | 1308 |

**Retrieved (k=5)**

| # | chunk | score | cited | text |
| --- | --- | --- | --- | --- |
| 1 | `RED3-ART25#0000` | 0.7102 | yes | # Renewable Energy Directive (RED), Directive (EU) 2018/2001, Art. 25 - consolidated version dated 16/07/2024 (CELEX 02018L2001-20240716, as amended by Directive (EU) 2023/2413 'RE |
| 2 | `REFUELEU-ART4#0000` | 0.6888 |  | # ReFuelEU Aviation, Regulation (EU) 2023/2405 of 18 October 2023, Art. 4 + Annex I - original OJ text, CELEX 32023R2405, no consolidation applied (retrieved from EUR-Lex 2026-10-1 |
| 3 | `REFUELEU-ART4#0007` | 0.6886 |  | 2034 until 31 December 2034 of synthetic aviation fuels; (c) From 1 January 2035, each year a minimum share of 20 % of SAF, of which a minimum share of 5 % of synthetic aviation fu |
| 4 | `REFUELEU-ART4#0003` | 0.6474 |  | erring also to low-carbon aviation fuels and to renewable hydrogen for aviation. 4. For each reporting period, aviation biofuels other than advanced biofuels as defined in Article  |
| 5 | `REFUELEU-ART4#0001` | 0.6422 | yes | Union airport over the periods from 1 January 2030 until 31 December 2031 and from 1 January 2032 until 31 December 2034 contains at least the average shares of synthetic aviation  |

---

## q13

**Question**

> Are sustainable aviation fuels excluded from the Chinese biodiesel anti-dumping duties, and what SAF share does ReFuelEU Aviation require from 2030?

**Answer**

Sustainable aviation fuels (SAF) are excluded from the scope of the anti-dumping investigation, as stated in [TRADE-BIODIESEL#0006]. 

Regarding the ReFuelEU Aviation requirements, from 1 January 2030 until 31 December 2031, the aviation fuel suppliers must ensure a minimum share of SAF, though the specific percentage for that period is not detailed in the provided context. However, starting from 1 January 2035, a minimum share of 20% of SAF is required each year, with additional percentages specified for later years [REFUELEU-ART4#0007].

| | |
| --- | --- |
| refused | `False` |
| citations | `TRADE-BIODIESEL#0006`, `REFUELEU-ART4#0007` |
| tokens_used | 1168 |

**Retrieved (k=5)**

| # | chunk | score | cited | text |
| --- | --- | --- | --- | --- |
| 1 | `REFUELEU-ART4#0000` | 0.6887 |  | # ReFuelEU Aviation, Regulation (EU) 2023/2405 of 18 October 2023, Art. 4 + Annex I - original OJ text, CELEX 32023R2405, no consolidation applied (retrieved from EUR-Lex 2026-10-1 |
| 2 | `TRADE-BIODIESEL#0007` | 0.6539 |  | alleged that the exclusion of SAF could make operators meet decarbonisation targets in the road sector via Chinese SAF, which are counting double towards EU targets, rather than vi |
| 3 | `REFUELEU-ART4#0007` | 0.6495 | yes | 2034 until 31 December 2034 of synthetic aviation fuels; (c) From 1 January 2035, each year a minimum share of 20 % of SAF, of which a minimum share of 5 % of synthetic aviation fu |
| 4 | `TRADE-BIODIESEL#0009` | 0.6339 |  | (20) In Neste’s view, HVO and HEFA-SAF would be in competition to the extent EU Renewable Energy Directives (‘RED’ (14)) foresee an opt-in possibility for Member States to use HEFA |
| 5 | `TRADE-BIODIESEL#0006` | 0.6275 | yes | Commission accepted the exclusion of SAF from the scope of the present investigation, as stated in recital 41 of the provisional Regulation. (18) Following provisional disclosure,  |

---

## q14

**Question**

> What does RED Article 25 require for renewable fuels of non-biological origin, and what synthetic aviation fuel shares does ReFuelEU Annex I set?

**Answer**

I don't have enough information in the provided documents to answer that.

| | |
| --- | --- |
| refused | `True` |
| citations | none |
| tokens_used | 1132 |

**Retrieved (k=5)**

| # | chunk | score | cited | text |
| --- | --- | --- | --- | --- |
| 1 | `REFUELEU-ART4#0000` | 0.6712 |  | # ReFuelEU Aviation, Regulation (EU) 2023/2405 of 18 October 2023, Art. 4 + Annex I - original OJ text, CELEX 32023R2405, no consolidation applied (retrieved from EUR-Lex 2026-10-1 |
| 2 | `REFUELEU-ART4#0003` | 0.6432 |  | erring also to low-carbon aviation fuels and to renewable hydrogen for aviation. 4. For each reporting period, aviation biofuels other than advanced biofuels as defined in Article  |
| 3 | `REFUELEU-ART4#0001` | 0.6395 |  | Union airport over the periods from 1 January 2030 until 31 December 2031 and from 1 January 2032 until 31 December 2034 contains at least the average shares of synthetic aviation  |
| 4 | `RED3-ART25#0000` | 0.6349 |  | # Renewable Energy Directive (RED), Directive (EU) 2018/2001, Art. 25 - consolidated version dated 16/07/2024 (CELEX 02018L2001-20240716, as amended by Directive (EU) 2023/2413 'RE |
| 5 | `REFUELEU-ART4#0004` | 0.6256 |  | s of SAF set out in Annex I to this Regulation: ‘food and feed crops’ as defined in Article 2, second paragraph, point (40), of Directive (EU) 2018/2001, intermediate crops, palm f |

---

## q15

**Question**

> The biodiesel investigation refers to the EU Renewable Energy Directive - what transport obligation does RED Article 25 actually set?

**Answer**

The Renewable Energy Directive (RED) Article 25 sets an obligation on fuel suppliers in each Member State to ensure that the amount of renewable fuels and renewable electricity supplied to the transport sector leads to either: 

1. A share of renewable energy within the final consumption of energy in the transport sector of at least 29% by 2030; or 
2. A greenhouse gas intensity reduction of at least 14.5% by 2030, compared to the baseline set out in Article 27(1), point (b) [RED3-ART25#0000]. 

Additionally, Member States are encouraged to promote the development of advanced biofuels and biogas, with specific targets for their share in the transport sector by 2025 and 2030 [RED3-ART25#0001].

| | |
| --- | --- |
| refused | `False` |
| citations | `RED3-ART25#0000`, `RED3-ART25#0001` |
| tokens_used | 1256 |

**Retrieved (k=5)**

| # | chunk | score | cited | text |
| --- | --- | --- | --- | --- |
| 1 | `RED3-ART25#0000` | 0.6912 | yes | # Renewable Energy Directive (RED), Directive (EU) 2018/2001, Art. 25 - consolidated version dated 16/07/2024 (CELEX 02018L2001-20240716, as amended by Directive (EU) 2023/2413 'RE |
| 2 | `RED3-ART25#0005` | 0.5710 |  | s and biogas produced from the feedstock listed in Part A of Annex IX with respect to those fuels; (b) set the obligation by means of measures targeting volumes, energy content or  |
| 3 | `RED3-ART25#0001` | 0.5633 | yes | 30, compared to the baseline set out in Article 27(1), point (b), in accordance with an indicative trajectory set by the Member State; (b) the combined share of advanced biofuels a |
| 4 | `RED3-ART25#0002` | 0.5606 |  | el in order to fulfil the obligation set out in the first subparagraph, point (b), of this paragraph, in a way that the development of both fuels is promoted and expanded. Member S |
| 5 | `TRADE-BIODIESEL#0000` | 0.5440 |  | # Biodiesel from China anti-dumping, Commission Implementing Regulation (EU) 2025/261, Art. 1 + Annex (cooperating exporting producers not sampled) - consolidated version dated 16/ |

---

## q16

**Question**

> What anti-dumping duty applies to Indonesian palm oil biodiesel?

**Answer**

I don't have enough information in the provided documents to answer that.

| | |
| --- | --- |
| refused | `True` |
| citations | none |
| tokens_used | 1154 |

**Retrieved (k=5)**

| # | chunk | score | cited | text |
| --- | --- | --- | --- | --- |
| 1 | `TRADE-BIODIESEL#0000` | 0.5355 |  | # Biodiesel from China anti-dumping, Commission Implementing Regulation (EU) 2025/261, Art. 1 + Annex (cooperating exporting producers not sampled) - consolidated version dated 16/ |
| 2 | `TRADE-BIODIESEL#0003` | 0.4791 |  | the following TARIC codes shall be subject to monitoring, in addition to the codes mentioned in paragraph 1 which were excluded from the scope of the measure: TARIC code 2710 19 11 |
| 3 | `TRADE-BIODIESEL#0005` | 0.4710 |  | such invoice, identified by name and function, drafted as follows: ‘I, the undersigned, certify that the (volume in tonnes) of biodiesel sold for export to the European Union cover |
| 4 | `TRADE-BIODIESEL#0018` | 0.3928 |  | nd HVO as sustainable alternative fuels for diesel engines in transport sector. CCCMC recalled the position of the Commission in a dispute concerning palm oil from Malaysia (DS600  |
| 5 | `TRADE-BIODIESEL#0004` | 0.3802 |  | p: \| — Zhejiang EastRiver Energy S&T Co., Ltd \| — Zhejiang Jiaao Enproenergy Co., Ltd \| — Jiaao International Trading (SINGAPORE) PTE. Ltd \| 35,6 \| 89EE Zhuoyue Group: \| — Longyan  |

---

## q17

**Question**

> What SAF mandate applies to maritime shipping under FuelEU Maritime?

**Answer**

I don't have enough information in the provided documents to answer that.

| | |
| --- | --- |
| refused | `True` |
| citations | none |
| tokens_used | 1028 |

**Retrieved (k=5)**

| # | chunk | score | cited | text |
| --- | --- | --- | --- | --- |
| 1 | `REFUELEU-ART4#0000` | 0.6025 |  | # ReFuelEU Aviation, Regulation (EU) 2023/2405 of 18 October 2023, Art. 4 + Annex I - original OJ text, CELEX 32023R2405, no consolidation applied (retrieved from EUR-Lex 2026-10-1 |
| 2 | `TRADE-BIODIESEL#0014` | 0.5883 |  | ductions for the purpose of the road mandate obligations for the use of SAF. Neste stated that, when using SAF, an airline could apply for a certificate for reducing emissions and  |
| 3 | `REFUELEU-ART4#0004` | 0.5781 |  | s of SAF set out in Annex I to this Regulation: ‘food and feed crops’ as defined in Article 2, second paragraph, point (40), of Directive (EU) 2018/2001, intermediate crops, palm f |
| 4 | `TRADE-BIODIESEL#0007` | 0.5728 |  | alleged that the exclusion of SAF could make operators meet decarbonisation targets in the road sector via Chinese SAF, which are counting double towards EU targets, rather than vi |
| 5 | `RED3-ART25#0002` | 0.5527 |  | el in order to fulfil the obligation set out in the first subparagraph, point (b), of this paragraph, in a way that the development of both fuels is promoted and expanded. Member S |

---

## q18

**Question**

> What penalty in euros per tonne applies to aviation fuel suppliers that miss their SAF target?

**Answer**

I don't have enough information in the provided documents to answer that.

| | |
| --- | --- |
| refused | `True` |
| citations | none |
| tokens_used | 1129 |

**Retrieved (k=5)**

| # | chunk | score | cited | text |
| --- | --- | --- | --- | --- |
| 1 | `REFUELEU-ART4#0000` | 0.5901 |  | # ReFuelEU Aviation, Regulation (EU) 2023/2405 of 18 October 2023, Art. 4 + Annex I - original OJ text, CELEX 32023R2405, no consolidation applied (retrieved from EUR-Lex 2026-10-1 |
| 2 | `REFUELEU-ART4#0005` | 0.5843 |  | where an aviation fuel supplier fails to supply the minimum shares set out in Annex I for a given reporting period, it shall at least complement that shortfall in the subsequent re |
| 3 | `REFUELEU-ART4#0004` | 0.5770 |  | s of SAF set out in Annex I to this Regulation: ‘food and feed crops’ as defined in Article 2, second paragraph, point (40), of Directive (EU) 2018/2001, intermediate crops, palm f |
| 4 | `REFUELEU-ART4#0006` | 0.5562 |  | nt reporting period. ANNEX I Shares of SAF referred to in Article 4 (a) From 1 January 2025, each year a minimum share of 2 % of SAF; (b) From 1 January 2030, each year a minimum s |
| 5 | `REFUELEU-ART4#0007` | 0.5535 |  | 2034 until 31 December 2034 of synthetic aviation fuels; (c) From 1 January 2035, each year a minimum share of 20 % of SAF, of which a minimum share of 5 % of synthetic aviation fu |

---

## q19

**Question**

> saf 2030 how much

**Answer**

From 1 January 2030, there is a minimum share of 6% of SAF, which includes a specific average share of synthetic aviation fuels over two periods: 
(i) From 1 January 2030 until 31 December 2031, an average share of 1.2% of synthetic aviation fuels, with a minimum share of 0.7% each year; 
(ii) From 1 January 2032 until 31 December 2034, an average share of 2.0% of synthetic aviation fuels, with a minimum share of 1.2% from 1 January 2032 until 31 December 2033 and a minimum share of 2.0% from 1 January 2034 until 31 December 2034 of synthetic aviation fuels [REFUELEU-ART4#0006].

| | |
| --- | --- |
| refused | `False` |
| citations | `REFUELEU-ART4#0006` |
| tokens_used | 1236 |

**Retrieved (k=5)**

| # | chunk | score | cited | text |
| --- | --- | --- | --- | --- |
| 1 | `REFUELEU-ART4#0007` | 0.5551 |  | 2034 until 31 December 2034 of synthetic aviation fuels; (c) From 1 January 2035, each year a minimum share of 20 % of SAF, of which a minimum share of 5 % of synthetic aviation fu |
| 2 | `REFUELEU-ART4#0006` | 0.5163 | yes | nt reporting period. ANNEX I Shares of SAF referred to in Article 4 (a) From 1 January 2025, each year a minimum share of 2 % of SAF; (b) From 1 January 2030, each year a minimum s |
| 3 | `REFUELEU-ART4#0000` | 0.4789 |  | # ReFuelEU Aviation, Regulation (EU) 2023/2405 of 18 October 2023, Art. 4 + Annex I - original OJ text, CELEX 32023R2405, no consolidation applied (retrieved from EUR-Lex 2026-10-1 |
| 4 | `TRADE-BIODIESEL#0006` | 0.4683 |  | Commission accepted the exclusion of SAF from the scope of the present investigation, as stated in recital 41 of the provisional Regulation. (18) Following provisional disclosure,  |
| 5 | `REFUELEU-ART4#0005` | 0.4580 |  | where an aviation fuel supplier fails to supply the minimum shares set out in Annex I for a given reporting period, it shall at least complement that shortfall in the subsequent re |

---

## q20

**Question**

> what about the duties

**Answer**

The application of the individual duty rates specified for certain companies is conditional upon the presentation of a valid commercial invoice to the Member States’ customs authorities. Until such an invoice is presented, the duty applicable to all other imports originating in the People’s Republic of China shall apply [TRADE-BIODIESEL#0005]. Additionally, the rates of the definitive anti-dumping duty applicable to specific products produced by listed companies are detailed, with specific percentages assigned to each company [TRADE-BIODIESEL#0003].

| | |
| --- | --- |
| refused | `False` |
| citations | `TRADE-BIODIESEL#0005`, `TRADE-BIODIESEL#0003` |
| tokens_used | 1158 |

**Retrieved (k=5)**

| # | chunk | score | cited | text |
| --- | --- | --- | --- | --- |
| 1 | `TRADE-BIODIESEL#0004` | 0.3437 |  | p: \| — Zhejiang EastRiver Energy S&T Co., Ltd \| — Zhejiang Jiaao Enproenergy Co., Ltd \| — Jiaao International Trading (SINGAPORE) PTE. Ltd \| 35,6 \| 89EE Zhuoyue Group: \| — Longyan  |
| 2 | `TRADE-BIODIESEL#0005` | 0.3416 | yes | such invoice, identified by name and function, drafted as follows: ‘I, the undersigned, certify that the (volume in tonnes) of biodiesel sold for export to the European Union cover |
| 3 | `TRADE-BIODIESEL#0003` | 0.3139 | yes | the following TARIC codes shall be subject to monitoring, in addition to the codes mentioned in paragraph 1 which were excluded from the scope of the measure: TARIC code 2710 19 11 |
| 4 | `TRADE-BIODIESEL#0014` | 0.2810 |  | ductions for the purpose of the road mandate obligations for the use of SAF. Neste stated that, when using SAF, an airline could apply for a certificate for reducing emissions and  |
| 5 | `TRADE-BIODIESEL#0013` | 0.2671 |  | Commission’s overall conclusion in recital 22. The Commission considered that the diverging views as to whether the technical properties of HVO and FAME make them (un)suitable for  |

---

