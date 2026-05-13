# Research Iteration: 2026-05-13 Escalation Packet

## Question

After provenance export and post-training records, what was still missing from SciTrace-RL?

## Finding

The project could validate a trace and turn it into training data, but it still needed a concrete mechanism for the moments when the right scientific answer is "not enough evidence yet." Current AI-for-science systems repeatedly point toward human-in-the-loop review, simulation, experimental protocols, and physical feedback as part of the discovery loop.

## Sources Checked

- Google AI co-scientist: https://research.google/blog/accelerating-scientific-breakthroughs-with-an-ai-co-scientist/
- Scientific Hypothesis Generation and Validation survey: https://arxiv.org/abs/2505.04651
- Embodied Science / PLAD framework: https://arxiv.org/abs/2603.19782
- DP Technology Uni-Lab-OS: https://github.com/dptech-corp/Uni-Lab-OS

## Decision

Add `escalation_packet.json` with four handoff tasks:

- `computational_validation` for Bohrium/Lebesgue-style high-fidelity checks.
- `wet_lab_validation` for Uni-Lab-OS-style protocol and cell-testing loops.
- `expert_boundary_review` for claim promotion and unresolved assumptions.
- `feedback_ingestion` for converting external results back into trace artifacts and learning signals.

## Why This Improves the Project

This makes the system more honest and more production-shaped. It does not pretend that a proxy chemistry score is a final scientific result. It stops at the boundary, names the uncertainty, and emits the next executable tasks needed to close the loop.
