from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from .utils import sha256_text


@dataclass(frozen=True)
class AIJudgeConfig:
    enabled: bool
    base_url: str
    model: str
    timeout_seconds: int
    api_key_env: str


def load_ai_judge_config() -> AIJudgeConfig:
    enabled = os.environ.get("SCITRACE_AI_JUDGE", "").strip().lower() in {"1", "true", "yes", "on"}
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
    api_key_env = "DEEPSEEK_API_KEY" if deepseek_key else "OPENAI_API_KEY"
    base_url = os.environ.get("OPENAI_BASE_URL") or os.environ.get("DEEPSEEK_BASE_URL")
    model = os.environ.get("OPENAI_MODEL") or os.environ.get("DEEPSEEK_MODEL")
    if not base_url:
        base_url = "https://api.deepseek.com" if deepseek_key else "https://api.openai.com/v1"
    if not model:
        model = "deepseek-v4-flash" if deepseek_key else "gpt-4.1-mini"
    return AIJudgeConfig(
        enabled=enabled,
        base_url=base_url.rstrip("/"),
        model=model,
        timeout_seconds=int(os.environ.get("SCITRACE_AI_TIMEOUT_SECONDS", "45")),
        api_key_env=api_key_env,
    )


def build_claim_review_prompt(
    report: dict[str, Any],
    sources: list[dict[str, Any]],
    artifacts: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    source_payload = [
        {
            "source_id": source["source_id"],
            "title": source["title"],
            "summary": source["summary"],
            "url": source["url"],
        }
        for source in sources
    ]
    review_payload = {
        "claims": report["claims"],
        "report_excerpt_for_context_only": report["markdown"][:6000],
        "retrieved_sources": source_payload,
        "allowed_artifacts": artifacts or {},
    }
    system = (
        "You are a strict scientific validation judge. Review whether each claim is supported "
        "only by the retrieved_sources and allowed_artifacts provided. Do not use outside knowledge. "
        "The report excerpt is context only and must not be treated as evidence. "
        "Return JSON only."
    )
    user = (
        "Evaluate claim-evidence support for this scientific-agent report. "
        "Return a JSON object with keys: status ('pass', 'warn', or 'fail'), score (0 to 1), "
        "rationale (short string), unsupported_claim_ids (array), and reviewed_claim_ids (array).\n\n"
        f"{json.dumps(review_payload, ensure_ascii=False, indent=2)}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def parse_json_object(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def call_openai_compatible_judge(messages: list[dict[str, str]], config: AIJudgeConfig) -> dict[str, Any]:
    api_key = os.environ.get(config.api_key_env, "").strip()
    if not api_key:
        return {
            "configured": False,
            "status": "skip",
            "score": 1.0,
            "rationale": f"SCITRACE_AI_JUDGE is enabled, but {config.api_key_env} is not set.",
            "unsupported_claim_ids": [],
            "reviewed_claim_ids": [],
        }

    request_body = {
        "model": config.model,
        "messages": messages,
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    request = urllib.request.Request(
        f"{config.base_url}/chat/completions",
        data=json.dumps(request_body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=config.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {
            "configured": True,
            "status": "warn",
            "score": 0.5,
            "rationale": f"AI judge request failed: {exc}",
            "unsupported_claim_ids": [],
            "reviewed_claim_ids": [],
        }

    content = payload["choices"][0]["message"]["content"]
    parsed = parse_json_object(content)
    parsed["configured"] = True
    parsed["provider"] = "openai_compatible_chat_completions"
    parsed["model"] = config.model
    parsed["base_url"] = config.base_url
    parsed["raw_response_hash"] = sha256_text(content)
    return parsed


def run_ai_claim_review(
    report: dict[str, Any],
    sources: list[dict[str, Any]],
    artifacts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = load_ai_judge_config()
    if not config.enabled:
        return {
            "configured": False,
            "status": "skip",
            "score": 1.0,
            "rationale": "Optional AI judge disabled. Set SCITRACE_AI_JUDGE=1 and OPENAI_API_KEY to enable.",
            "unsupported_claim_ids": [],
            "reviewed_claim_ids": [],
        }
    messages = build_claim_review_prompt(report, sources, artifacts)
    return call_openai_compatible_judge(messages, config)
