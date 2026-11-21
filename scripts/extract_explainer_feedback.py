#!/usr/bin/env python3
"""Collect "【讲解反馈】" feedback from Codex session logs.

The marker uses the Chinese brackets 【】 (typed with the [ and ] keys in a
Chinese input method) because "#" is too common: it starts Markdown headings
and code comments, so a "#..." marker would match text the user only pasted.

For every user message that contains the marker, this script records:
- when and in which project the feedback was given;
- the Codex reply the feedback most likely refers to (the last reply
  before the feedback, preferring final answers over progress notes);
- whether Codex had read the explainer-guide skill earlier in the same
  session, which of its files it read, and which skill version it saw.

Sessions that Codex starts on its own (subagents and automatic approval
reviews) are skipped, because the user never types into them.

By default only session files modified on or after the day the guide was
installed are read. The check uses the modification time rather than the
start date in the file name, because the user can resume an older session and
write feedback there. A file is parsed only if its raw text contains the
marker, so sessions without feedback cost one read and no JSON parsing.

Output files are written to work/explainer-feedback/ under the project root:
- feedback.jsonl: one JSON object per feedback message;
- feedback.md: the same records in a readable form.

Both files contain conversation text, so keep them out of anything you
publish. Paths under the home directory are written as "~/...".

Usage:
    python3 -I scripts/extract_explainer_feedback.py
    python3 -I scripts/extract_explainer_feedback.py --since 2026-11-17
    python3 -I scripts/extract_explainer_feedback.py --since 2000-01-01  # every log
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HOME = Path.home()
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCES = [HOME / ".codex" / "sessions", HOME / ".codex" / "archived_sessions"]
DEFAULT_OUT = PROJECT_ROOT / "work" / "explainer-feedback"
DEFAULT_MARKER = "【讲解反馈】"
SKILL_NAME = "explainer-guide"
# The day the guide was first installed into Codex. No earlier log can hold
# feedback on it.
GUIDE_INSTALLED = "2026-11-10"

SKILL_INJECTION = f"<name>{SKILL_NAME}</name>"
# A file under references/ or sources/, or one of those directories as a whole
# (Codex often searches a directory with rg instead of opening one file).
SKILL_FILE_RE = re.compile(
    SKILL_NAME + r"/(SKILL\.md|(?:references|sources)(?:/[A-Za-z0-9_-]+\.md)?)(?![A-Za-z0-9_-])"
)
# The quote may be escaped when the tool output is itself a JSON string, as
# with Codex's exec tool: version: \"0.1.1\".
VERSION_RE = re.compile(r"version:\s*\\?[\"']?([0-9][0-9A-Za-z.\-]*)")
USER_EVENT_RE = re.compile(r"\"type\":\s*\"UserMessage\"")


def tilde(path: str | None) -> str | None:
    """Replace the home directory prefix with "~" so no user name is stored."""
    if not path:
        return path
    home = str(HOME)
    if path == home:
        return "~"
    if path.startswith(home + "/"):
        return "~" + path[len(home):]
    return path


def read_session_text(path: Path) -> str | None:
    """Return the whole text of a .jsonl or .jsonl.zst file, or None."""
    if path.name.endswith(".zst"):
        result = subprocess.run(
            ["zstd", "-dc", str(path)], capture_output=True, check=False
        )
        if result.returncode != 0:
            print(f"skip (cannot decompress): {tilde(str(path))}", file=sys.stderr)
            return None
        return result.stdout.decode("utf-8", errors="replace")
    return path.read_text(encoding="utf-8", errors="replace")


def iter_lines(path: Path):
    """Yield text lines from a .jsonl or .jsonl.zst file."""
    if path.name.endswith(".zst"):
        text = read_session_text(path)
        if text is not None:
            yield from text.splitlines()
    else:
        with path.open(encoding="utf-8", errors="replace") as handle:
            yield from handle


def marker_forms(marker: str) -> tuple[str, ...]:
    """The marker as it may appear in raw JSON: as is, or with \\u escapes."""
    return (marker, json.dumps(marker)[1:-1])


def content_text(content) -> str:
    """Join the text parts of a message content list."""
    if isinstance(content, str):
        return content
    parts = []
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
    return "\n".join(parts)


def tool_output_text(output) -> str:
    """Tool outputs are either a string or a list of text parts."""
    if isinstance(output, str):
        return output
    return content_text(output)


def is_injected_user_text(text: str) -> bool:
    """User-role messages that Codex injects rather than the user typing them."""
    head = text.lstrip()[:200]
    return (
        head.startswith("# AGENTS.md instructions")
        or head.startswith("<environment_context>")
        or head.startswith("<user_instructions>")
        or head.startswith("<skill>")
    )


def is_subagent_session(meta: dict) -> bool:
    """Sessions that Codex starts on its own, such as automatic approval reviews.

    Their logs contain prompts written by Codex in the user role, and the user
    never types into them, so they cannot hold feedback.
    """
    source = meta.get("source")
    if isinstance(source, dict) and "subagent" in source:
        return True
    return meta.get("thread_source") == "guardian_review"


def scan_session(path: Path, marker: str):
    """Return the feedback records found in one session file."""
    meta = {}
    guide_files: list[str] = []
    versions: list[str] = []
    last_final = None
    last_any = None
    seen_user_texts: set[str] = set()
    records = []

    text = read_session_text(path)
    # Most sessions hold no feedback. Skip them before the slow JSON parsing.
    if text is None or not any(form in text for form in marker_forms(marker)):
        return []
    lines = text.splitlines()
    # Newer logs record what the user typed as UserMessage events. Older logs
    # only have user-role response items, so fall back to those when needed.
    has_user_events = any(USER_EVENT_RE.search(line) for line in lines)

    def handle_user(timestamp: str, text: str):
        if marker not in text:
            return
        reply = last_final or last_any
        records.append(
            {
                "session_id": meta.get("id"),
                "session_file": tilde(str(path)),
                "cwd": tilde(meta.get("cwd")),
                "originator": meta.get("originator"),
                "timestamp": timestamp,
                "feedback": text.strip(),
                "reply": reply["text"] if reply else None,
                "reply_phase": reply["phase"] if reply else None,
                "reply_timestamp": reply["timestamp"] if reply else None,
                "guide_read_before": bool(guide_files),
                "guide_files_read": sorted(set(guide_files)),
                "guide_versions_seen": sorted(set(versions)),
            }
        )

    for line in lines:
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        rtype = rec.get("type")
        payload = rec.get("payload") or {}
        timestamp = rec.get("timestamp", "")
        if not isinstance(payload, dict):
            continue

        if rtype == "session_meta":
            meta = payload
            if is_subagent_session(meta):
                return []
            continue

        ptype = payload.get("type")

        if rtype == "event_msg" and ptype == "item_completed":
            item = payload.get("item") or {}
            if item.get("type") == "UserMessage":
                text = content_text(item.get("content"))
                if text and text not in seen_user_texts:
                    seen_user_texts.add(text)
                    handle_user(timestamp, text)
            continue

        if rtype != "response_item":
            continue

        if ptype == "message":
            role = payload.get("role")
            text = content_text(payload.get("content"))
            # When the user invokes a skill by name, Codex pastes its SKILL.md
            # into the conversation as a "<skill>" block instead of reading the
            # file with a tool.
            if role in ("user", "developer") and SKILL_INJECTION in text:
                guide_files.append("SKILL.md")
                versions.extend(VERSION_RE.findall(text))
            if role == "assistant" and text.strip():
                entry = {
                    "text": text.strip(),
                    "phase": payload.get("phase"),
                    "timestamp": timestamp,
                }
                last_any = entry
                if payload.get("phase") in (None, "final_answer"):
                    last_final = entry
            elif role == "user" and text and not is_injected_user_text(text):
                if not has_user_events and text not in seen_user_texts:
                    seen_user_texts.add(text)
                    handle_user(timestamp, text)
            continue

        if ptype in ("custom_tool_call", "function_call", "local_shell_call"):
            call_text = json.dumps(payload, ensure_ascii=False)
            guide_files.extend(SKILL_FILE_RE.findall(call_text))
            continue

        if ptype in ("custom_tool_call_output", "function_call_output"):
            out = tool_output_text(payload.get("output"))
            if f"name: {SKILL_NAME}" in out:
                versions.extend(VERSION_RE.findall(out))
            continue

    return records


def session_files(sources: list[Path], since: str | None):
    for source in sources:
        if not source.exists():
            continue
        for path in sorted(source.rglob("rollout-*.jsonl*")):
            if since:
                match = re.search(r"rollout-(\d{4}-\d{2}-\d{2})", path.name)
                if match and match.group(1) < since:
                    continue
            yield path


def modified_files(sources: list[Path], since: str):
    """Session files whose local modification date is on or after since."""
    for source in sources:
        if not source.exists():
            continue
        for path in sorted(source.rglob("rollout-*.jsonl*")):
            modified = datetime.fromtimestamp(path.stat().st_mtime).date().isoformat()
            if modified >= since:
                yield path


def write_markdown(records: list[dict], out_path: Path, marker: str):
    lines = [f"# {marker} 汇总", ""]
    if not records:
        lines.append("没有找到带这个标记的消息。")
    for index, rec in enumerate(records, 1):
        guide = "读过" if rec["guide_read_before"] else "没有读过"
        files = "，".join(rec["guide_files_read"]) or "无"
        versions = "，".join(rec["guide_versions_seen"]) or "没有在日志里看到"
        lines += [
            f"## {index}. {rec['timestamp']}",
            "",
            f"- 项目目录：{rec['cwd']}",
            f"- 会话文件：{rec['session_file']}",
            f"- 反馈之前 Codex {guide}这份指南。读过的文件：{files}。看到的版本：{versions}。",
            "",
            "Codex 的回复：",
            "",
        ]
        reply = rec["reply"] or "（没有找到反馈之前的回复）"
        lines += ["> " + row if row else ">" for row in reply.splitlines()]
        lines += ["", "用户的反馈：", ""]
        lines += ["> " + row if row else ">" for row in rec["feedback"].splitlines()]
        lines.append("")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--since", default=GUIDE_INSTALLED,
        help=f"only read session files modified on or after this local date (default: {GUIDE_INSTALLED}, when the guide was installed)",
    )
    parser.add_argument("--marker", default=DEFAULT_MARKER, help="text that marks a feedback message")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output directory")
    parser.add_argument(
        "--source", type=Path, action="append",
        help="session directory to scan; can be given more than once (default: Codex sessions and archived sessions)",
    )
    args = parser.parse_args()

    sources = args.source or DEFAULT_SOURCES
    records = []
    scanned = 0
    for path in modified_files(sources, args.since):
        scanned += 1
        records.extend(scan_session(path, args.marker))
    records.sort(key=lambda r: r["timestamp"] or "")

    args.out.mkdir(parents=True, exist_ok=True)
    jsonl_path = args.out / "feedback.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for rec in records:
            handle.write(json.dumps(rec, ensure_ascii=False) + "\n")
    md_path = args.out / "feedback.md"
    write_markdown(records, md_path, args.marker)

    print(
        f"read {scanned} session files modified since {args.since}, "
        f"found {len(records)} feedback messages"
    )
    print(f"wrote {tilde(str(jsonl_path))}")
    print(f"wrote {tilde(str(md_path))}")


if __name__ == "__main__":
    main()
