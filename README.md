# 言式则例

一组让 Agent 用中文写作的风格 skill。每种风格是一个独立的 skill，放在 `skills/` 下面，规定 Agent 在某一类场合该怎样写。目前有一种风格，以后还会加入别的风格。

## 现有的风格

- [讲解者指南](skills/explainer-guide/SKILL.md)（`explainer-guide`）：Agent 汇报进展、回答问题或者请用户做决定时，把事情讲得让用户读一遍就能明白。语气像一位有礼貌的同事当面说事情，不堆砌术语和自造的代号，也不把句子压缩得只剩名词。`SKILL.md` 只写要点和写完以后的检查清单，具体做法和例子放在 `references/` 里，Agent 需要时才会去读。

## 安装

每个 skill 都是一个目录，把它放进 Agent 的 skills 目录就可以用。下面以讲解者指南为例。

Claude Code：

```sh
git clone https://github.com/MagicGeekSquad/agent-style-lab.git
mkdir -p ~/.claude/skills
cp -R agent-style-lab/skills/explainer-guide ~/.claude/skills/
```

Codex：

```sh
git clone https://github.com/MagicGeekSquad/agent-style-lab.git
cd agent-style-lab
sh scripts/install_codex.sh explainer-guide
```

这个脚本会同时装上 Codex 专用的设置，包括显示名称，以及允许 Codex 在合适的时候自动使用这个 skill。以后拉取了新版本，再运行一次就会更新。

其他支持 skill 的 Agent，把 `skills/explainer-guide` 目录复制到它读取 skill 的位置即可。

## 引用的资料

讲解者指南的每个查阅文件末尾都列了出处，能在网上找到的附了网址。出处里提到的 `sources/` 目录是作者核对引文用的原文摘录，因为不少资料的转载许可还没有确认，这个目录没有放进仓库。指南里的引文都是附带出处的短引，版权归原作者。部分例子来自作者和 Agent 的真实对话，已经去掉了项目名和使用环境。

Codex 的安装脚本需要系统里有 `rsync`。

## 许可

本仓库自己的内容采用 [MIT 许可](LICENSE)。
