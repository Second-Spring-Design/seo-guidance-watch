#!/usr/bin/env python3
"""LLM triage for guidance diffs.

Reads a git diff of snapshots/, asks an LLM whether the change matters for
an SEO/AEO content pipeline, and files a GitHub issue when it does.

Degrades gracefully: with no ANTHROPIC_API_KEY secret set, it files a plain
"change detected, review manually" issue instead — the watcher never
depends on the LLM to be useful.
"""

import json
import os
import subprocess
import sys
import urllib.request

MODEL = os.environ.get("TRIAGE_MODEL", "claude-haiku-4-5")
MAX_DIFF_CHARS = 60_000

PROMPT = """You triage changes to SEO/AEO guidance pages for a small team \
that runs an AI blog-content pipeline (Article JSON-LD, FAQ blocks, \
answer-first posts, WordPress export, AI-crawler policies).

Below is a unified diff of watched sources (Google Search Central docs & \
updates feed, schema.org releases, Bing blog RSS, OpenAI/Perplexity crawler \
docs). Classify it:

1. severity: "actionable" (we likely must change our pipeline or schema), \
"notable" (worth reading, no action yet), or "noise" (formatting/dates/churn).
2. summary: 2-4 sentences, plain language, what changed and why it matters.
3. affected: which watched source(s).

Respond with ONLY a JSON object: {"severity": ..., "summary": ..., "affected": [...]}

DIFF:
"""


def file_issue(title: str, body: str) -> None:
    subprocess.run(
        ["gh", "issue", "create", "--title", title, "--body", body,
         "--repo", os.environ.get("GITHUB_REPOSITORY", "")],
        check=True,
    )


def main() -> int:
    diff_path = sys.argv[1]
    with open(diff_path, encoding="utf-8", errors="replace") as f:
        diff = f.read().strip()
    if not diff:
        print("Empty diff — nothing to triage.")
        return 0

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        print("No ANTHROPIC_API_KEY secret — filing un-triaged issue.")
        file_issue(
            "Guidance change detected (untriaged)",
            "A watched SEO guidance source changed. No `ANTHROPIC_API_KEY` "
            "secret is configured, so review the latest snapshot commit diff "
            "manually.\n\nAdd the secret in repo Settings → Secrets → Actions "
            "to enable automatic LLM triage.",
        )
        return 0

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps({
            "model": MODEL,
            "max_tokens": 800,
            "messages": [{"role": "user",
                          "content": PROMPT + diff[:MAX_DIFF_CHARS]}],
        }).encode(),
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            payload = json.loads(resp.read())
        text = payload["content"][0]["text"]
        start, end = text.find("{"), text.rfind("}")
        verdict = json.loads(text[start:end + 1])
    except Exception as exc:  # noqa: BLE001 — triage must never block the watcher
        print(f"Triage call failed ({exc}) — filing un-triaged issue.")
        file_issue("Guidance change detected (triage failed)",
                   "LLM triage errored; review the latest snapshot commit "
                   f"diff manually.\n\nError: `{exc}`")
        return 0

    severity = verdict.get("severity", "notable")
    if severity == "noise":
        print(f"Triage verdict: noise — no issue filed. {verdict.get('summary','')}")
        return 0

    affected = ", ".join(verdict.get("affected", [])) or "unknown"
    file_issue(
        f"[{severity}] Guidance change: {affected}",
        f"**Severity:** {severity}\n\n**Summary:** {verdict.get('summary','')}\n\n"
        f"**Affected sources:** {affected}\n\n"
        "See the latest snapshot commit for the full diff.",
    )
    print(f"Issue filed ({severity}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
