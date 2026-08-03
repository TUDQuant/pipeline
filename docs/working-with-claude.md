# Working with Claude on this project

Which surface to use for what, which account to use where, and what not to
delegate. Written for whoever owns infrastructure.

---

## 1. The routing rule

One question decides the surface: **where does the work live?**

| Work lives in… | Use | Why |
|---|---|---|
| The repo — code, tests, CI, pipelines | **Claude Code** | It runs `pytest`, reads the failure, fixes it, re-runs. Chat cannot. |
| Files and apps — docs, decks, research across sources | **Cowork** | Multi-step work over many files without a codebase. |
| Your head — a decision, a design, a message | **Chat (claude.ai)** | Fastest loop. No setup, no repo. |

Most people over-use chat for repo work and end up copy-pasting code and error
messages back and forth. That loop is where the time goes.

### Applied to what's left here

| Task | Surface |
|---|---|
| Push the repo, wire branch protections | Claude Code |
| First pipeline run fails — diagnose and fix | **Claude Code.** The whole loop is read log → edit → re-run. |
| numpy/numba/vectorbt version conflict | Claude Code. It has to actually install and import to know. |
| Write curriculum lessons | Claude Code (uses the `tudquant-lesson` skill) or Cowork |
| Draft the message to Marven or the board | Chat |
| Decide Phase 2 timing, argue a tradeoff | Chat |
| Research paid intraday data providers | Cowork, or chat with search |
| Create GCP service account, paste secrets | **You. Not an agent.** See §4. |

---

## 2. Claude Code

The bulk of the remaining work. Requires a Pro, Max, Team, Enterprise or
Console account — the free plan does not include it
([docs](https://code.claude.com/docs/en/setup)). Available in the terminal, in
VS Code, and in the desktop app if you'd rather not use a terminal.

**`CLAUDE.md` is the thing that makes it good rather than mediocre.** It sits in
the repo root and loads automatically every session. Ours already contains the
hard rules — never touch credentials, never commit `.ipynb` outside `colab/`,
never unpin numpy, never widen the data universe unasked. Without it you
re-explain the project every session and it will still guess wrong.

Keep `CLAUDE.md` current. When you correct Claude on the same thing twice, that
correction belongs in the file. This is the single highest-leverage habit in
the whole setup.

**Use plan mode for anything structural.** It researches and proposes without
editing. Reserve direct execution for changes you could review in a diff.

**Work in branches.** `main` is protected and CI must pass. Let it open a PR;
read the diff. An agent that can push to `main` unreviewed is a bad idea in a
repo twenty students depend on.

### Prompts that work here

> The nightly pipeline failed. Read the latest `update-data` Actions run, find
> the failing symbol, and fix it. If it's a source outage rather than a bug,
> say so and don't change code.

> Add a validation check for *[fault]* in `tudquant/validation.py`, plus a test
> in `tests/test_validation.py` that injects the fault and asserts it's caught.
> Run the suite.

> Members report the setup cell fails on a fresh Colab runtime with *[error]*.
> Reproduce against `requirements-pinned.txt`, find the minimum version change
> that fixes it, and tell me the risk of that change mid-semester.

---

## 3. Skills

A skill is a folder with a `SKILL.md` — YAML frontmatter (`name`,
`description`) plus instructions. Claude loads the description at startup and
reads the body only when the task matches, so a skill costs nothing until it's
relevant ([docs](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)).

Skills are for **procedural knowledge you'd otherwise repeat in every prompt.**

This repo ships `.claude/skills/tudquant-lesson/`. It encodes the lesson
format, the data-access rules, and the pedagogical standards — show the failure
first, never present a backtest without its caveat in the same cell, no strategy
is presented as working. Anyone writing curriculum gets those constraints
automatically instead of you reviewing for them.

Worth adding later, once the pattern is clear:

- `tudquant-datasource` — the checklist for adding a source: adapter shape,
  calendar choice, universe entry, validation, smoke test line
- `tudquant-review` — what a strategy PR from a member must contain before merge

Write a skill when you've explained the same procedure three times. Not before —
a skill written from a guess encodes the guess.

The built-in document skills (docx, pptx, xlsx, pdf) are already available on
paid plans and need no setup. Useful when the board wants a slide deck.

---

## 4. Accounts — which one, for what

Getting this wrong is the most common way student club infrastructure dies:
everything is tied to one person, that person graduates, and nobody can log in.

| Account | Used for | Rule |
|---|---|---|
| **Your personal GitHub** | Your commits, as a member of the Org | Attribution is yours. The Org owns the repos. Never host club repos here. |
| **GitHub Organization** (`tud-quant`) | All repos, teams, Actions secrets | Owned by ≥2 people. One owner is a single point of failure. |
| **Your club Workspace account** | Colab, Drive, admin | Personal Gmail can't see the Shared Drive. |
| **Service account** (`tud-quant-pipeline@…`) | Nightly Drive writes only | Never a human login. Key lives in a GitHub secret and nowhere else. |
| **Club Alpha Vantage / FRED keys** | Pipeline only | Registered to a club address. A personal key breaks on graduation. |
| **Your Claude account** | Claude Code, Cowork, chat | Personal, individual. See below. |

### On the Claude account specifically

Claude Code needs a paid plan. Two honest points:

- Pay for it yourself for now. A club subscription is a board decision with a
  recurring cost, and you shouldn't commit the club to one to unblock your own
  workflow.
- If it becomes something several people need, that's a proper proposal with a
  cost line — not something that quietly appears on the club card.

### The rule that matters most

**Never let an agent hold a credential.**

`.gitignore` already excludes `*service-account*.json` and `.env`. `CLAUDE.md`
forbids reading them. Keep both. The service account has write access to the
club's entire data layer; the correct number of tools that can read that key is
one, and it's GitHub Actions.

If a task seems to require pasting a secret into a chat, the task is wrong. Do
it yourself in the console.

---

## 5. What not to delegate

Four things are yours, permanently:

1. **Creating accounts and accepting terms.** The Org, the Workspace accounts,
   the GCP project. Your name is on them.
2. **Anything touching a secret.** Generating the service account key, pasting
   the four GitHub secrets.
3. **Deciding what the club builds.** Whether Phase 2 happens in October or
   March, whether to pay for intraday data. An agent will produce a confident
   recommendation for either; the judgement is the job.
4. **The final read of anything members depend on.** Especially the smoke test.
   If it passes and the environment is still broken, twenty people find out
   during a lesson.

---

## 6. A working rhythm

**Weekly:** open Claude Code, ask it to check the last week of `update-data`
runs and the data quality summary, and report what degraded. Ten minutes.

**Before each session:** run `colab/smoke_test.ipynb` with a club account —
not yours, a real member's. Environments break silently between lessons.

**After each session:** whatever confused members goes into `CLAUDE.md` or a
skill, not into your memory. You are building something that outlives your
involvement, which is the actual difference between a club project and a
personal one.

---

## Reference

- Claude Code setup — https://code.claude.com/docs/en/setup
- Agent Skills — https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
- Connectors — https://support.claude.com/en/articles/11176164-use-connectors-to-extend-claude-s-capabilities
