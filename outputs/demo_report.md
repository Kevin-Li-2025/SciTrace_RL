# Agent-Grounded Candidate Report

## Task
Screen a small set of lithium-ion battery electrolyte additive candidates and produce a traceable, citation-grounded recommendation for the next validation loop.

## Recommendation
Prioritize **Fluoroethylene carbonate** (`FEC`) for the next dry-lab or wet-lab validation loop. The recommendation is provisional: it is based on a lightweight, reproducible proxy screen, not on high-fidelity quantum chemistry or real battery cycling data.

## Evidence Chain
- [fec_vc_reduction] Fluoroethylene Carbonate and Vinylene Carbonate Reduction: Understanding Lithium-Ion Battery Electrolyte Additives and Solid Electrolyte Interphase Formation (https://doi.org/10.1021/acs.chemmater.6b02282)
- [electrolyte_additives_review] How electrolyte additives work in Li-ion batteries (https://doi.org/10.1016/j.ensm.2018.11.015)

## Candidate Ranking
| Rank | Candidate | Formula | Score | Key evidence |
|---:|---|---|---:|---|
| 1 | Fluoroethylene carbonate | C3H3FO3 | 0.890 | fec_vc_reduction, electrolyte_additives_review |
| 2 | 1,3,2-Dioxathiolane-2,2-dioxide | C2H4O4S | 0.760 | electrolyte_additives_review, battery_safety_additives |
| 3 | Vinylene carbonate | C3H2O3 | 0.710 | fec_vc_reduction, vc_rechargeable_review, electrolyte_additives_review |

## Validation Hooks
- Re-run `molecule_screening` with the same candidates and constraints; the output hash should match.
- Check every cited source id in the report against the retrieval results.
- Promote the top candidate only if the molecular-weight constraint, evidence coverage, and claim-evidence alignment gates pass.

## Next Step
Replace the proxy screening tool with a Bohrium/Lebesgue job adapter for molecular simulation, then feed validated results back into the trace-to-reward dataset.
