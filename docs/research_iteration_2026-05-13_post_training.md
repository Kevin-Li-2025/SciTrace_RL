# Research Iteration: 2026-05-13 Post-Training Bundle

## Question

After adding provenance export, what still made SciTrace-RL less convincing as a large-model infrastructure project?

## Finding

The project claimed that traces can become training data, but the first version only exported a compact `trace_to_reward_sample.json`. Recent agent training work is more concrete: it treats execution as trajectories, assigns credit across steps, and separates runtime execution from post-training data pipelines.

## Sources Checked

- Agent Lightning: https://arxiv.org/abs/2508.03680
- AgentPRM: https://arxiv.org/abs/2502.10325
- RLFactory: https://arxiv.org/abs/2509.06980
- AgentGym: https://arxiv.org/abs/2406.04151

## Decision

Add `post_training_bundle.json` with five data views:

- `sft_chat_record`: a grounded supervised fine-tuning example.
- `dpo_preference_pair`: chosen trace-backed answer versus an overclaimed rejected answer.
- `process_reward_steps`: per-tool-call rewards linked to validation gates.
- `tool_router_records`: route labels for retrieval, screening, and report generation.
- `credit_assignment`: validation failures mapped back to responsible tool classes.

## Why This Improves the Project

This makes the large-model part tangible. The demo no longer says "trace-to-reward" only in prose; it produces the actual records that a future planner, process reward model, or tool router could consume.
