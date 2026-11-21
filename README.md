<div align="center">

# agent-style-lab

### Writing skills for agents that reply in Chinese

Help your agent write progress updates, answers and requests for decisions that people can understand on the first read.

[![Chinese writing](https://img.shields.io/badge/writing-Chinese-2b6cb0)](#available-styles)
[![MIT license](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

English | [简体中文](README_ZH.md)

[Styles](#available-styles) · [How it works](#how-it-works) · [Installation](#installation) · [Quick start](#quick-start) · [FAQ](#faq)

</div>

## Why agent-style-lab?

After a long task, an agent has spent hours looking at details you may never have seen. Its update can turn into a list of invented codes, clipped sentences and bold labels. You have to decipher what happened before you can tell whether it matters or whether you need to act.

The Explainer Guide helps the agent write from your point of view. It puts the outcome first, uses terms you know and connects the facts in complete sentences. Before sending the reply, the agent checks whether you can understand it on the first read.

### Before and after

The [Explainer Guide](skills/explainer-guide/SKILL.md) uses this Chinese example of an agent recommending what to do with old materials.

Before

> D3：建议仓外受控存档，仓内保留匿名派生版

In English, this reads “D3: Recommend controlled archiving outside the repository, with an anonymized derivative retained in the repository.”

After

> 我建议把旧材料移出仓库另外保存，仓库里只留下匿名处理过的版本

In English, this reads “I suggest moving the old materials out of the repository and saving them separately, keeping only the anonymized versions in the repository.”

The rewrite says what should move and what should stay. The reader can assess the recommendation without having to decode “D3.”

## What the guide covers

The Explainer Guide shapes a reply in four areas, then has the agent check the draft against a checklist before sending it.

- **What to say**: the outcome comes first, and a question gets answered in the opening sentence. Only facts that change your understanding or decision go in; details stay in linked files. Unfinished work and numbers come with what they mean for you, and decisions come with a recommendation and its reasons.
- **Which names to use**: codes the agent invented and terms you have never used are replaced with words you know. Ordinary-looking words that carry a special meaning in the work, such as “regression,” are spelled out as what actually happened.
- **How to write sentences**: no status fragments like “stopped; not committed.” Subjects and connectives stay, and each sentence follows from the one before.
- **Tone and format**: a polite colleague explaining something in person — neither clipped nor put-on casual. Anything a few connected sentences can explain is not broken into bold labels and tables.

## Available styles

- [Explainer Guide](skills/explainer-guide/SKILL.md) (`explainer-guide`) helps agents write updates, answers and requests for decisions in Chinese, in the tone of a colleague explaining something to you.

Each style has its own directory under [`skills/`](skills/). The Explainer Guide is the first, and more styles will be added.

## How it works

- [`SKILL.md`](skills/explainer-guide/SKILL.md) gives the agent the main writing principles and a checklist to use after drafting a reply.
- [`references/`](skills/explainer-guide/references/) contains detailed guidance and examples. The agent reads the relevant file when it needs help with a specific issue, such as introducing an unfamiliar term or reporting an uncertain result.

## Installation

Clone the repository and run the steps for your agent from its root directory.

```sh
git clone https://github.com/MagicGeekSquad/agent-style-lab.git
cd agent-style-lab
```

### Claude Code

Copy the whole skill directory into your personal skills directory.

```sh
mkdir -p ~/.claude/skills
cp -R skills/explainer-guide ~/.claude/skills/
```

### Codex

Install `rsync` if it is missing, then run the installer.

```sh
sh scripts/install_codex.sh explainer-guide
```

The script copies the skill to `~/.codex/skills/explainer-guide/` by default, or to `$CODEX_HOME/skills/explainer-guide/` if you set `CODEX_HOME`. It adds the [Codex settings](scripts/codex/explainer-guide/agents/openai.yaml) for the display name and automatic use. After updating your checkout, run the same command to update the installed copy.

### Other agents

If your agent supports skills, copy the entire `skills/explainer-guide/` directory to the location where it looks for skills.

## Quick start

Once installed, the agent can use the guide automatically when it needs to explain progress, answer a question or ask you to make a decision in Chinese. You can also ask for the guide by name. In Codex, for example, use this prompt.

> 按 $explainer-guide 的要求，把这件事讲给我听。

## FAQ

<details>
<summary>What if I already have writing requirements?</summary>

Your instructions in the conversation take priority. If you ask the agent to write in a particular format or voice, such as academic prose, it should follow the requirements for that piece.

</details>

<details>
<summary>Is the guide meant for internal notes?</summary>

The guide is for text the user will read right away. For records kept mainly for later reference, follow your project's documentation conventions.

</details>

## Uninstall

Remove the installed `explainer-guide/` directory from your agent's skills directory. For Claude Code, that is `~/.claude/skills/explainer-guide/`. For Codex, use the path in the [installation steps](#codex) that matches your `CODEX_HOME` setting.

## Sources and copyright

Each reference file lists its sources at the end and links to those available online. The `sources/` directory mentioned in the references contains excerpts used to check quotations. It is kept out of the repository while permission to redistribute some of that material remains unconfirmed.

Quotations in the guide are brief and attributed. Their copyright remains with the original authors. Some examples come from real conversations with agents, with project names and details about how the agents were used removed.

## Feedback and contributions

If you find a passage that is hard to follow or have an idea for another writing style, you can [open an issue](https://github.com/MagicGeekSquad/agent-style-lab/issues).

## License

Original material in this repository is licensed under the [MIT License](LICENSE).
