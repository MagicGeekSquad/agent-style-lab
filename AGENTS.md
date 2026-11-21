# 言式则例：维护约定

这是一个公开仓库，收集让 Agent 用中文写作的风格 skill。讲解者指南（`skills/explainer-guide`）是其中一种，以后还会加入别的风格。

## 目录

- `skills/<name>/`：每种风格一个 skill，`SKILL.md` 写要点，`references/` 写细节。
- `scripts/codex/<name>/agents/`：这个 skill 在 Codex 里的设置，安装时才加进去。
- `scripts/install_codex.sh <name>`：把 skill 装进 Codex，改完源文件后重新运行。
- `scripts/` 里其余的 Python 脚本是讲解者指南的维护工具，见下面“收集反馈”。
- `work/`、`docs/` 和 `skills/*/sources/` 只留在本机，不进仓库。本地资料的索引见 `work/README.md`。

## skill 内容必须是纯内容

- skill 要分发给别人，里面不提具体的 Agent 产品、模型或用户自己的项目名称，不写本机路径和用户的使用环境。Git 这类通用工具可以拿来举例。
- Agent 专用的设置放进 `scripts/<agent>/<name>/`，不放进 skill 目录。
- 例子来自真实对话时，只引用不涉及使用环境的句子，必要时用省略号略去项目名和工具名，转述的地方在出处里说明。对话原文留在 `work/`。
- 第三方资料的原文摘录放在 `skills/<name>/sources/`，只在本机用来核对。转载许可确认之前，不要把它们加进仓库。
- 提交前用 grep 检查要进仓库的文件里没有本机路径、用户名和私人项目名，skill 目录里也没有 Agent 产品和模型的名称。安装和维护脚本可以写明它们对应的 Agent。

## 改动 skill 的流程

1. 改源文件，保持各 skill 自己的写作要求（讲解者指南要求一组并列最多一个顿号，能用连贯的句子就不用粗体标签和表格）。
2. 新增或改了真实引文，运行 `python3 -I scripts/check_source_quotes.py` 核对；带省略号的引文要逐段手动核对。
3. 把 `SKILL.md` 里的 `metadata.version` 加一，重新运行安装脚本。
4. 设计上的变化记进本地的设计文档（见 `work/README.md`）。

## 收集反馈（讲解者指南）

- 用户在 Codex 对话里写“【讲解反馈】”并指出问题。`python3 -I scripts/extract_explainer_feedback.py` 把这些反馈连同前一条回复取出来，写进 `work/explainer-feedback/`。
- `python3 -I scripts/explainer_guide_usage.py` 统计 Codex 有没有读指南，读了哪些文件。
- 要把某次对话用作例子，先用 `python3 -I scripts/export_codex_session.py 会话文件 输出文件` 导出到 `work/explainer-feedback/examples/`。
- 摘录由 `python3 -I scripts/excerpt_source.py build scripts/explainer_sources/*.json` 生成，依赖本机 `docs/refs/` 里的原文。

## 其他约束

- `work/failure-mode-exam` 里的题库已冻结，未经用户明确要求，不新增、替换或改写题目。
- 提交、推送和发布要先得到用户同意。
