#!/usr/bin/env python3
"""Count how Codex uses the explainer-guide skill, with or without feedback.

extract_explainer_feedback.py only looks at sessions where the user wrote a
feedback marker. This script looks at every Codex session since the guide was
installed and answers three questions:
- Did Codex read SKILL.md, and did it read it before its first reply?
- Did the user have to invoke the guide by name ("$explainer-guide")?
- Which files under references/ and sources/ did Codex open or search?

For the final reply of every turn the user started, it also records whether
SKILL.md was read in the same turn before the reply, earlier in the session,
or not at all. Turns started by another agent sending a message to the thread
are left out, because those replies are written for that agent.

Sessions that Codex starts on its own (subagents and automatic approval
reviews) are skipped, because their replies are not read by the user. The
totals also leave out sessions whose working directory is this project, where
Codex may be editing the guide rather than using it, and sessions whose
AGENTS.md did not yet tell Codex to read the guide.

Output files are written to work/explainer-feedback/ under the project root:
- guide-usage.jsonl: one JSON object per session;
- guide-usage.md: totals by day, how often each file was opened, and the
  sessions that opened files beyond SKILL.md or invoked the guide by name.

No conversation text is stored, only paths, times and counts. Paths under the
home directory are written as "~/...".

Usage:
    python3 -I scripts/explainer_guide_usage.py
    python3 -I scripts/explainer_guide_usage.py --since 2026-11-17
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

# -I leaves the script directory off sys.path, so add it to reuse the parser
# helpers of the feedback script.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_explainer_feedback import (  # noqa: E402
    DEFAULT_OUT,
    DEFAULT_SOURCES,
    GUIDE_INSTALLED,
    PROJECT_ROOT,
    SKILL_FILE_RE,
    SKILL_INJECTION,
    SKILL_NAME,
    USER_EVENT_RE,
    VERSION_RE,
    content_text,
    is_injected_user_text,
    is_subagent_session,
    iter_lines,
    session_files,
    tilde,
    tool_output_text,
)

INVOKE_TEXT = f"${SKILL_NAME}"
AGENTS_MD_HEAD = "# AGENTS.md instructions"
STARTED_RE = re.compile(r"rollout-(\d{4}-\d{2}-\d{2})T(\d{2}-\d{2}-\d{2})")
TURN_EVENT_RE = re.compile(r"\"type\":\s*\"task_started\"")
KIND_USER, KIND_SCRIPT, KIND_AGENT = "user", "script", "agent"
KIND_LABELS = {
    KIND_USER: "用户在 Codex 里发起的对话",
    KIND_SCRIPT: "脚本或命令启动的会话",
    KIND_AGENT: "另一个 Agent 开的线程",
}
TOOL_CALLS = ("custom_tool_call", "function_call", "local_shell_call")
TOOL_OUTPUTS = ("custom_tool_call_output", "function_call_output")


def new_turn(timestamp: str | None) -> dict:
    return {
        "start": timestamp, "from_user": False, "read_skill": False,
        "files": [], "reply": None, "read_before_reply": False,
    }


def session_kind(triggers: list[str | None], meta: dict) -> str:
    """Who started the session: the user chatting, a script, or another agent.

    Newer logs record what started each turn. "composer" is a message typed
    in the Codex app; "exec" is `codex exec`, which scripts use; "app_tool_*"
    is another agent creating the thread or sending it a message. Logs without
    this field count as the user's unless they come from `codex exec`.
    """
    if "composer" in triggers:
        return KIND_USER
    if not triggers:
        return KIND_SCRIPT if "exec" in str(meta.get("originator", "")) else KIND_USER
    if str(triggers[0]).startswith("app_tool"):
        return KIND_AGENT
    return KIND_SCRIPT


def started_from_name(path: Path) -> str | None:
    """Local start time from a file name like rollout-2026-11-10T20-52-57-<id>.jsonl."""
    match = STARTED_RE.search(path.name)
    return f"{match.group(1)} {match.group(2).replace('-', ':')}" if match else None


def scan_session(path: Path) -> dict | None:
    """Return one usage record for a session, or None for sessions Codex started itself."""
    meta = {}
    turns = [new_turn(None)]
    first_reads: dict[str, str] = {}
    versions: set[str] = set()
    invoked_by_name = False
    agents_md_names_guide = False
    seen_user_texts: set[str] = set()
    triggers: list[str | None] = []

    lines = list(iter_lines(path))
    has_user_events = any(USER_EVENT_RE.search(line) for line in lines)
    # Newer logs mark the start of every turn. A turn can be started by the
    # user, or by another agent sending a message to this thread; only turns
    # with a message typed by the user count as replies the user reads.
    has_turn_events = any(TURN_EVENT_RE.search(line) for line in lines)

    def user_message(timestamp: str, text: str):
        nonlocal invoked_by_name
        if text in seen_user_texts:
            return
        seen_user_texts.add(text)
        if INVOKE_TEXT in text:
            invoked_by_name = True
        if not has_turn_events:
            turns.append(new_turn(timestamp))
        turns[-1]["from_user"] = True

    def guide_used(timestamp: str, name: str):
        turn = turns[-1]
        first_reads.setdefault(name, timestamp)
        if name == "SKILL.md":
            turn["read_skill"] = True
        elif name not in turn["files"]:
            turn["files"].append(name)

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
                return None
            continue

        ptype = payload.get("type")

        if rtype == "event_msg" and ptype == "task_started":
            turns.append(new_turn(timestamp))
            attribution = payload.get("turn_attribution") or {}
            triggers.append(attribution.get("turn_trigger"))
            continue

        if rtype == "event_msg" and ptype == "item_completed":
            item = payload.get("item") or {}
            if item.get("type") == "UserMessage":
                text = content_text(item.get("content"))
                if text:
                    user_message(timestamp, text)
            continue

        if rtype != "response_item":
            continue

        if ptype == "message":
            role = payload.get("role")
            text = content_text(payload.get("content"))
            if role == "user" and text.lstrip().startswith(AGENTS_MD_HEAD) and SKILL_NAME in text:
                agents_md_names_guide = True
            if role in ("user", "developer") and SKILL_INJECTION in text:
                # Codex pastes SKILL.md as a "<skill>" block when the user
                # invokes the guide by name.
                invoked_by_name = True
                guide_used(timestamp, "SKILL.md")
                versions.update(VERSION_RE.findall(text))
            if role == "assistant" and text.strip() and payload.get("phase") in (None, "final_answer"):
                turn = turns[-1]
                if turn["reply"] is None:
                    turn["reply"] = timestamp
                    turn["read_before_reply"] = turn["read_skill"]
            elif role == "user" and text and not is_injected_user_text(text) and not has_user_events:
                user_message(timestamp, text)
            continue

        if ptype in TOOL_CALLS:
            call_text = json.dumps(payload, ensure_ascii=False)
            for name in SKILL_FILE_RE.findall(call_text):
                guide_used(timestamp, name)
            continue

        if ptype in TOOL_OUTPUTS:
            out = tool_output_text(payload.get("output"))
            if f"name: {SKILL_NAME}" in out:
                versions.update(VERSION_RE.findall(out))
            continue

    # Classify the final reply of every turn the user started by when SKILL.md
    # was read. Reads in turns started by other agents still count as "earlier".
    replies = {"read_this_turn": 0, "read_earlier": 0, "not_read": 0}
    agent_turn_replies = 0
    read_so_far = False
    for turn in turns:
        if turn["reply"] is not None and not turn["from_user"]:
            agent_turn_replies += 1
        elif turn["reply"] is not None:
            if turn["read_before_reply"]:
                replies["read_this_turn"] += 1
            elif read_so_far:
                replies["read_earlier"] += 1
            else:
                replies["not_read"] += 1
        read_so_far = read_so_far or turn["read_skill"]

    first_reply = next((t["reply"] for t in turns if t["reply"] is not None and t["from_user"]), None)
    skill_read_at = first_reads.get("SKILL.md")
    cwd = meta.get("cwd")
    return {
        "session_id": meta.get("id"),
        "session_file": tilde(str(path)),
        "started": started_from_name(path),
        "cwd": tilde(cwd),
        "in_this_project": bool(cwd) and Path(cwd).resolve() == PROJECT_ROOT,
        "originator": meta.get("originator"),
        "thread_source": meta.get("thread_source"),
        "kind": session_kind(triggers, meta),
        "turn_triggers": sorted({str(t) for t in triggers}),
        "agents_md_names_guide": agents_md_names_guide,
        "user_turns": sum(t["from_user"] for t in turns),
        "final_replies": sum(replies.values()),
        "agent_turn_replies": agent_turn_replies,
        "replies": replies,
        "invoked_by_name": invoked_by_name,
        "read_skill": skill_read_at is not None,
        "read_skill_before_first_reply": skill_read_at is not None
        and (first_reply is None or skill_read_at <= first_reply),
        "other_files": sorted(name for name in first_reads if name != "SKILL.md"),
        "versions_seen": sorted(versions),
    }


def day_of(rec: dict) -> str:
    return (rec["started"] or "")[:10] or "未知"


def percent(part: int, whole: int) -> str:
    return f"{part}（{round(100 * part / whole)}%）" if whole else "0"


def write_markdown(records: list[dict], skipped: int, since: str, out_path: Path):
    in_project = [r for r in records if r["in_this_project"]]
    rest = [r for r in records if not r["in_this_project"]]
    no_instruction = [r for r in rest if not r["agents_md_names_guide"]]
    with_instruction = [r for r in rest if r["agents_md_names_guide"]]
    user_sessions = [r for r in with_instruction if r["kind"] == KIND_USER]
    no_reply = [r for r in user_sessions if not r["final_replies"]]
    counted = [r for r in user_sessions if r["final_replies"]]

    lines = [
        "# 讲解者指南的使用情况",
        "",
        f"统计 {since} 以后开始的 Codex 会话，日期和时间都是本机时间。"
        f"没有算进去的有：Codex 自己开的子会话和自动审批会话 {skipped} 个，"
        f"在本项目里的会话 {len(in_project)} 个（可能是在改指南本身），"
        f"开始时载入的 AGENTS.md 里还没有提到这份指南的会话 {len(no_instruction)} 个。",
        "",
        "## 会话的来源",
        "",
        "AGENTS.md 对所有会话都生效，所以脚本启动的测试和另一个 Agent 开的线程也可能去读指南。",
        "",
        "| 来源 | 会话 | 读了 SKILL.md | 打开了查阅文件或摘录 |",
        "| --- | ---: | ---: | ---: |",
    ]
    for kind, label in KIND_LABELS.items():
        group = [r for r in with_instruction if r["kind"] == kind]
        lines.append(
            f"| {label} | {len(group)} "
            f"| {percent(sum(r['read_skill'] for r in group), len(group))} "
            f"| {percent(sum(bool(r['other_files']) for r in group), len(group))} |"
        )

    lines += [
        "",
        f"下面几节只统计用户在 Codex 里发起、并且得到了最终回复的对话，一共 {len(counted)} 个"
        f"（另有 {len(no_reply)} 个没有得到最终回复）。"
        "只算用户发了消息的轮次和这些轮次的最终回复；另一个 Agent 发消息触发的轮次不算。",
        "",
        "## 每天的会话",
        "",
        "“先读了”指在第一条最终回复之前就读了 SKILL.md。“指名”指用户在消息里写了 "
        f"`{INVOKE_TEXT}`。“查阅文件”和“摘录”指打开或搜索过 `references/` 和 `sources/` 里的文件。",
        "",
        "| 日期 | 会话 | 读了 SKILL.md | 先读了 | 指名 | 查阅文件 | 摘录 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    by_day: dict[str, list[dict]] = {}
    for rec in counted:
        by_day.setdefault(day_of(rec), []).append(rec)
    for day in sorted(by_day):
        group = by_day[day]
        total = len(group)
        lines.append(
            f"| {day} | {total} "
            f"| {percent(sum(r['read_skill'] for r in group), total)} "
            f"| {percent(sum(r['read_skill_before_first_reply'] for r in group), total)} "
            f"| {percent(sum(r['invoked_by_name'] for r in group), total)} "
            f"| {percent(sum(any(f.startswith('references') for f in r['other_files']) for r in group), total)} "
            f"| {percent(sum(any(f.startswith('sources') for f in r['other_files']) for r in group), total)} |"
        )

    lines += [
        "",
        "## 每天的最终回复",
        "",
        "每条最终回复按 SKILL.md 读的时间分成三类：这一轮在回复之前读了，前面几轮读过，整个会话到这里都没读过。",
        "",
        "| 日期 | 最终回复 | 这一轮读了 | 前面读过 | 没读过 |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for day in sorted(by_day):
        group = by_day[day]
        total = sum(r["final_replies"] for r in group)
        lines.append(
            f"| {day} | {total} "
            f"| {percent(sum(r['replies']['read_this_turn'] for r in group), total)} "
            f"| {percent(sum(r['replies']['read_earlier'] for r in group), total)} "
            f"| {percent(sum(r['replies']['not_read'] for r in group), total)} |"
        )

    files = Counter(name for rec in counted for name in rec["other_files"])
    lines += ["", "## 打开过的查阅文件和摘录", ""]
    if files:
        lines += ["“references”和“sources”不带文件名，表示搜索了整个目录。", "", "| 文件 | 会话数 |", "| --- | ---: |"]
        lines += [f"| {name} | {count} |" for name, count in sorted(files.items(), key=lambda kv: (-kv[1], kv[0]))]
    else:
        lines.append("没有会话打开过 SKILL.md 以外的文件。")

    notable = [r for r in counted if r["other_files"] or r["invoked_by_name"]]
    lines += ["", "## 值得细看的会话", ""]
    if notable:
        lines += [
            "下面的会话打开过 SKILL.md 以外的文件，或者是用户指名调用了指南。",
            "",
            "| 开始时间 | 项目目录 | 回复 | 先读了 | 指名 | 打开的文件 | 会话文件 |",
            "| --- | --- | ---: | --- | --- | --- | --- |",
        ]
        for rec in sorted(notable, key=lambda r: r["started"] or ""):
            lines.append(
                f"| {(rec['started'] or '')[:16]} | {rec['cwd']} | {rec['final_replies']} "
                f"| {'是' if rec['read_skill_before_first_reply'] else '否'} "
                f"| {'是' if rec['invoked_by_name'] else '否'} "
                f"| {'，'.join(rec['other_files']) or '无'} | {rec['session_file']} |"
            )
    else:
        lines.append("没有。")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--since", default=GUIDE_INSTALLED,
        help=f"only scan sessions started on or after this date (default: {GUIDE_INSTALLED}, when the guide was installed)",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output directory")
    parser.add_argument(
        "--source", type=Path, action="append",
        help="session directory to scan; can be given more than once (default: Codex sessions and archived sessions)",
    )
    args = parser.parse_args()

    records = []
    skipped = 0
    for path in session_files(args.source or DEFAULT_SOURCES, args.since):
        rec = scan_session(path)
        if rec is None:
            skipped += 1
        else:
            records.append(rec)
    records.sort(key=lambda r: r["started"] or "")

    args.out.mkdir(parents=True, exist_ok=True)
    jsonl_path = args.out / "guide-usage.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for rec in records:
            handle.write(json.dumps(rec, ensure_ascii=False) + "\n")
    md_path = args.out / "guide-usage.md"
    write_markdown(records, skipped, args.since, md_path)

    print(f"scanned {len(records) + skipped} session files, skipped {skipped} started by Codex itself")
    print(f"wrote {tilde(str(jsonl_path))}")
    print(f"wrote {tilde(str(md_path))}")


if __name__ == "__main__":
    main()
