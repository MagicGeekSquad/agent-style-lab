#!/usr/bin/env python3
"""Export what the user typed and Codex's final replies from one session log.

The explainer-guide skill quotes real Codex replies and the user's feedback on
them. Like every other cited source, the quoted text is copied by machine:
this script writes the conversation to a Markdown file in the project, and
scripts/excerpt_source.py then builds the excerpt under the skill's sources/.

Only messages the user typed and Codex's final replies are kept, in order.
Tool calls, progress notes and text that Codex injects (AGENTS.md, skill
contents, environment details) are left out. Each message is written as a
quote block under a heading that names the speaker and the local time. The
export replaces the current home directory prefix with "~/". The messages
can still contain identifying details. Keep exports under the ignored work/
directory for local review.

Usage:
    python3 -I scripts/export_codex_session.py SESSION.jsonl work/explainer-feedback/examples/OUTPUT.md
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# -I leaves the script directory off sys.path, so add it to reuse the parser
# helpers of the feedback script.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_explainer_feedback import (  # noqa: E402
    HOME,
    USER_EVENT_RE,
    content_text,
    is_injected_user_text,
    iter_lines,
)


def local_time(timestamp: str) -> str:
    """2026-11-11T03:02:15.389Z -> 2026-11-11 11:02 in local time."""
    try:
        moment = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return timestamp
    return moment.astimezone().strftime("%Y-%m-%d %H:%M")


def hide_home(text: str) -> str:
    return text.replace(str(HOME) + "/", "~/")


def messages(path: Path):
    """Yield (speaker, timestamp, text) for user messages and final replies."""
    lines = list(iter_lines(path))
    has_user_events = any(USER_EVENT_RE.search(line) for line in lines)
    seen_user_texts: set[str] = set()
    for line in lines:
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        payload = rec.get("payload") or {}
        if not isinstance(payload, dict):
            continue
        timestamp = rec.get("timestamp", "")
        rtype, ptype = rec.get("type"), payload.get("type")

        if rtype == "event_msg" and ptype == "item_completed":
            item = payload.get("item") or {}
            if item.get("type") == "UserMessage":
                text = content_text(item.get("content"))
                if text and text not in seen_user_texts:
                    seen_user_texts.add(text)
                    yield "用户", timestamp, text
            continue

        if rtype != "response_item" or ptype != "message":
            continue
        role = payload.get("role")
        text = content_text(payload.get("content"))
        if role == "assistant" and text.strip() and payload.get("phase") in (None, "final_answer"):
            yield "Codex", timestamp, text
        elif role == "user" and not has_user_events and text and not is_injected_user_text(text):
            if text not in seen_user_texts:
                seen_user_texts.add(text)
                yield "用户", timestamp, text


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("session", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    out = [f"# Codex 对话记录：{args.session.name}", ""]
    for speaker, timestamp, text in messages(args.session):
        # Quote each message, so headings inside a message are not mistaken
        # for the headings of this file.
        body = ["> " + row if row else ">" for row in hide_home(text.strip()).splitlines()]
        out += [f"## {speaker}（{local_time(timestamp)}）", "", *body, ""]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(out), encoding="utf-8")
    print(f"wrote {hide_home(str(args.output.resolve()))}")


if __name__ == "__main__":
    main()
