<div align="center">

# 言式则例

### 给 Agent 用的中文写作 skill

让 Agent 汇报进展、回答问题或请你做决定时，把事情讲得让你读一遍就明白。

[![中文写作](https://img.shields.io/badge/writing-Chinese-2b6cb0)](#现有风格)
[![MIT 许可](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

[English](README.md) | 简体中文

[现有风格](#现有风格) · [工作原理](#工作原理) · [安装](#安装) · [快速开始](#快速开始) · [常见问题](#常见问题)

</div>

## 为什么需要言式则例

Agent 做了一件耗时很长的事，已经看过不少你没见过的细节。等它来汇报，回复里常常堆满自己起的代号、压缩过的句子和粗体标签。你得先猜这些话在说什么，才能判断事情跟你有什么关系，需不需要你出面处理。

讲解者指南让 Agent 站在你的位置上写回复。它先告诉你结果，再用你熟悉的词把事情讲清楚，句子之间也要接得上。写完以后，Agent 会再读一遍，看看你能不能一次读懂。

### 改写前后

[讲解者指南](skills/explainer-guide/SKILL.md)里有一组例子，讲的是 Agent 建议怎样处理旧材料。

改写前

> D3：建议仓外受控存档，仓内保留匿名派生版

改写后

> 我建议把旧材料移出仓库另外保存，仓库里只留下匿名处理过的版本

改写后，你一眼就知道哪些材料要移走，哪些版本要留下，也就能直接判断是否同意这个建议。

## 指南管哪些事

讲解者指南从四个方面约束 Agent 的写法，写完以后再按一份清单逐条检查。

- **讲什么**：最要紧的结果放在开头，问了问题就先回答。只写会改变你理解或决定的事，细节给出文件链接。还没做完的事和每个数字，都要说清它意味着什么。需要你做决定时，Agent 要给出推荐和理由。
- **用哪些名称**：自己起的代号和你没用过的术语，要换成你能看懂的说法。像“回归”这样看起来普通、在工作里却有专门意思的词，也要讲出实际发生了什么。
- **句子怎样写**：不把句子压缩成“已停止，未提交”这样只报状态的短语，保留主语和关联词，每句话都接得上前面的内容。
- **语气和格式**：像一位有礼貌的同事当面说事情，既不压缩，也不刻意装口语。能用几句连贯的话讲清楚的，就不拆成粗体标签和表格。

## 现有风格

- [讲解者指南](skills/explainer-guide/SKILL.md)（`explainer-guide`）适合用来写进展汇报、回答问题和请用户做决定。语气像一位有礼貌的同事当面说明情况。

每种风格在 [`skills/`](skills/) 下都有自己的目录。讲解者指南是第一种，以后还会加入别的风格。

## 工作原理

- [`SKILL.md`](skills/explainer-guide/SKILL.md)写了动笔时要注意的要点，也给了写完以后逐项核对的清单。
- [`references/`](skills/explainer-guide/references/)里有具体做法和例子。比如，Agent 需要解释陌生术语或者说明一项结果还有哪些不确定的地方时，再去读对应的文件。

## 安装

先克隆仓库，再进入仓库目录，按照你用的 Agent 选择下面的步骤。

```sh
git clone https://github.com/MagicGeekSquad/agent-style-lab.git
cd agent-style-lab
```

### Claude Code

把整个 skill 目录复制到个人 skills 目录。

```sh
mkdir -p ~/.claude/skills
cp -R skills/explainer-guide ~/.claude/skills/
```

### Codex

如果系统里还没有 `rsync`，先安装它，再运行脚本。

```sh
sh scripts/install_codex.sh explainer-guide
```

脚本默认装到 `~/.codex/skills/explainer-guide/`。如果你设置了 `CODEX_HOME`，就会装到 `$CODEX_HOME/skills/explainer-guide/`。脚本也会装上 [Codex 专用的设置](scripts/codex/explainer-guide/agents/openai.yaml)，让 Codex 显示 skill 的名称，并能在合适的时候自动使用它。以后拉取了新版本，再运行一次这个命令就能更新。

### 其他 Agent

如果你的 Agent 支持 skill，把整个 `skills/explainer-guide/` 目录复制到它读取 skill 的位置。

## 快速开始

装好以后，Agent 用中文汇报进展、回答问题或请你做决定时，可以自动使用这份指南。你也可以在对话里点名请它使用。比如，在 Codex 里可以这样说。

> 按 $explainer-guide 的要求，把这件事讲给我听。

## 常见问题

<details>
<summary>我已经有自己的写作要求，可以一起用吗？</summary>

你在对话里提出的要求优先。如果你指定了格式或语气，比如要写成学术文章，Agent 就按这种文章的要求来写。

</details>

<details>
<summary>平时留作备查的工作记录也适合用这份指南吗？</summary>

这份指南适合写给用户马上读的内容。平时留作备查的工作记录，按你项目里的文档约定来写就可以。

</details>

## 卸载

从 Agent 的 skills 目录里删除装进去的 `explainer-guide/` 目录。Claude Code 的安装位置是 `~/.claude/skills/explainer-guide/`。Codex 的位置取决于你有没有设置 `CODEX_HOME`，可以按上面的 [Codex 安装说明](#codex) 找到。

## 引用资料和版权

指南的每个查阅文件都在末尾列了出处，能在网上找到的也附了网址。出处里提到的 `sources/` 目录存放着核对引文用的原文摘录。因为部分资料的转载许可还没有确认，这个目录留在仓库之外。

指南里的引文都很短，并且附了出处，版权归原作者。部分例子来自和 Agent 的真实对话，已经去掉了项目名和使用环境。

## 反馈和贡献

如果你发现哪段写得难懂，或者想建议一种新的写作风格，欢迎[提 issue](https://github.com/MagicGeekSquad/agent-style-lab/issues)。

## 许可

仓库里的原创内容采用 [MIT 许可](LICENSE)。
