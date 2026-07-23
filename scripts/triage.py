#!/usr/bin/env python3

"""Produce advisory-only OpenAI triage from a sanitized validation log."""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


RESPONSES_URL = "https://api.openai.com/v1/responses"
MAX_LOG_CHARS = 120_000


def sanitize(text):
    replacements = (
        (r"(?i)(authorization:\s*bearer\s+)[^\s]+", r"\1<redacted>"),
        (
            r"(?i)\b(api[_-]?key|token|password|secret)=([^\s]+)",
            r"\1=<redacted>",
        ),
        (r"github_pat_[A-Za-z0-9_]+", "<redacted-github-token>"),
        (r"sk-[A-Za-z0-9_-]{16,}", "<redacted-api-key>"),
        (r"/home/[^/\s]+", "/home/<user>"),
        (r"/nix/store/[a-z0-9]{32}-", "/nix/store/<hash>-"),
    )
    result = text
    for pattern, replacement in replacements:
        result = re.sub(pattern, replacement, result)
    if len(result) > MAX_LOG_CHARS:
        result = (
            "[Earlier output omitted; only the final validation output follows.]\n"
            + result[-MAX_LOG_CHARS:]
        )
    return result


def response_text(payload):
    texts = []
    for item in payload.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                texts.append(content.get("text", ""))
    if not texts:
        raise ValueError("OpenAI response contained no output_text")
    return "\n".join(texts)


def triage(log, api_key, model):
    body = {
        "model": model,
        "instructions": (
            "You are reviewing a failed Nixpkgs Liquorix kernel maintenance run. "
            "Return concise Markdown with: failure classification, first causal "
            "error, evidence, likely upstream or Nixpkgs cause, safe diagnostic "
            "steps, and a proposed patch as a unified diff only when evidence is "
            "sufficient. Never claim the patch was tested or approved. Do not "
            "recommend bypassing tests, changing hashes without prefetching, or "
            "automatic merge."
        ),
        "input": sanitize(log),
        "reasoning": {"effort": "medium"},
        "text": {"verbosity": "low"},
        "store": False,
    }
    request = Request(
        RESPONSES_URL,
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urlopen(request, timeout=90) as response:
        return response_text(json.load(response))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("log", type=Path)
    parser.add_argument(
        "--model", default=os.environ.get("OPENAI_MODEL", "gpt-5.6-terra")
    )
    args = parser.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY is not set; AI triage was skipped.", file=sys.stderr)
        return 2

    try:
        print(triage(args.log.read_text(errors="replace"), api_key, args.model))
    except (HTTPError, URLError, TimeoutError, ValueError) as error:
        print(f"AI triage failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
