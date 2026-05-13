# Demo Guide

## What To Submit

Submit the repository or a compressed folder containing:

- `docs/project_proposal.md`
- `README.md`
- `src/scitrace_rl/`
- `data/`
- `outputs/demo_dashboard.html`
- `outputs/demo_trace.json`
- `outputs/demo_report.md`
- `outputs/validation_scorecard.json`
- `outputs/trace_to_reward_sample.json`

## How To Run

```bash
PYTHONPATH=src python3 -m scitrace_rl.cli --out outputs
```

Then open:

```bash
open outputs/demo_dashboard.html
```

Run tests:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

Optional AI API validation:

```bash
export SCITRACE_AI_JUDGE=1
export DEEPSEEK_API_KEY="your_api_key"
export DEEPSEEK_MODEL="deepseek-v4-flash"
export DEEPSEEK_BASE_URL="https://api.deepseek.com"
PYTHONPATH=src python3 -m scitrace_rl.cli --out outputs
```

This adds an `ai_claim_review` gate to the validation scorecard. Without these environment variables, that gate is skipped and the deterministic validators still run.

Run the 15-case eval suite:

```bash
PYTHONPATH=src python3 -m scitrace_rl.eval_suite --out outputs/eval
```

With DeepSeek enabled, the same command produces a model-backed semantic validation report.

## What The Reviewer Should Notice

1. The project is not a generic chatbot demo. It is infrastructure for scientific agents.
2. The trace contains structured tool calls, output hashes, artifacts, validations, metrics, and reward.
3. The report is grounded in retrieved source ids and every citation is checked.
4. The candidate ranking is replayable; the same inputs produce the same output hash.
5. The reward sample shows how execution traces can become training data.
6. The optional `ai_claim_review` gate shows how a real AI API can be used as an extra semantic judge without making the demo fragile.

## Demo Scenario

The demo screens three lithium-ion battery electrolyte additive candidates:

- Fluoroethylene carbonate
- Vinylene carbonate
- 1,3,2-Dioxathiolane-2,2-dioxide

The screening is deliberately lightweight. Its role is to prove the infrastructure path:

```text
scientific goal -> tools -> artifacts -> validation -> reward -> learning data
```

## Expected Result

The default run recommends fluoroethylene carbonate as the top candidate and produces:

- reward around `0.97`
- all validation gates passing
- `outputs/demo_dashboard.html` as a visual scorecard
- `outputs/validation_scorecard.json` as machine-readable validation output
- `outputs/trace_to_reward_sample.json` as training-ready feedback data
- `outputs/eval/eval_report.md` as the offline adversarial validation report
- `outputs/eval_deepseek_v7/eval_report.md` as the latest real DeepSeek-backed validation report

## How To Explain The Demo In An Interview

Use this short version:

> This demo targets the production bottleneck of scientific agents: not whether an agent can produce a plausible answer, but whether its workflow can be traced, replayed, validated, and converted into feedback for future improvement. I implemented a small dry-lab workflow for electrolyte additive screening. The scientific model is intentionally lightweight, but the infrastructure is the point: each tool call has structured inputs and outputs, each artifact is hashed, claims are checked against evidence, the run is replayed, and the final validation score becomes a reward label for future agent training.
