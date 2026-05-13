# Optional AI API Validation

## Short Answer

The demo should not require a real AI API to run. A reviewer may not have your API key, network access, or the same model availability. The core demo therefore stays deterministic and local.

However, an optional AI judge strengthens the project because it shows the production pattern:

```text
symbolic validation gates + AI semantic review + trace-to-reward feedback
```

## What Was Added

SciTrace-RL includes an optional `ai_claim_review` validation gate.

Default behavior:

- no API call
- validation status is `skip`
- reward is not penalized
- all deterministic validation gates still run

When enabled:

- the report claims and retrieved evidence are sent to an OpenAI-compatible chat completions endpoint
- the model returns JSON with `status`, `score`, `rationale`, `unsupported_claim_ids`, and `reviewed_claim_ids`
- the result is stored in `demo_trace.json` and `validation_scorecard.json`
- the AI judge score participates in reward aggregation

## How To Enable

Set environment variables before running with DeepSeek:

```bash
export SCITRACE_AI_JUDGE=1
export DEEPSEEK_API_KEY="your_api_key"
export DEEPSEEK_MODEL="deepseek-v4-flash"
export DEEPSEEK_BASE_URL="https://api.deepseek.com"

PYTHONPATH=src python3 -m scitrace_rl.cli --out outputs
```

Run the larger eval suite:

```bash
PYTHONPATH=src python3 -m scitrace_rl.eval_suite --out outputs/eval_deepseek
```

Optional:

```bash
export SCITRACE_AI_TIMEOUT_SECONDS=45
```

The implementation uses Python standard library HTTP calls and does not add a package dependency.

The same adapter also supports OpenAI-compatible endpoints:

```bash
export SCITRACE_AI_JUDGE=1
export OPENAI_API_KEY="your_api_key"
export OPENAI_MODEL="your_supported_model"
export OPENAI_BASE_URL="https://api.openai.com/v1"
```

## Why This Design Is Better

A hard API dependency would make the demo fragile. A purely local demo would miss a realistic production layer. The optional judge gives both:

- deterministic local execution for reviewers
- production-style semantic validation when an API key is available

In a real Bohrium/SciMaster environment, this AI judge could be replaced or complemented by domain expert review, specialized scientific validators, or model-based evaluators trained on historical traces.

## Latest Real DeepSeek Run

The latest real DeepSeek-backed eval run is stored at:

```text
outputs/eval_deepseek_v7/eval_report.md
```

It used 15 cases and reached:

- deterministic detection rate: `1.000`
- AI semantic detection rate: `1.000`
- supported-case pass rate: `1.000`
- auto-resolvable coverage: `0.800`
- expert-required case share: `0.200`

The last two metrics are intentional. They show that SciTrace-RL does not pretend to fully automate scientific judgment when a claim requires high-fidelity simulation, wet-lab conditions, or domain-expert review.
