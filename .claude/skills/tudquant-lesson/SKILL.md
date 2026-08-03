---
name: tudquant-lesson
description: Write or revise a curriculum notebook for the TUD Quant club. Use whenever the task is creating a lesson, exercise, tutorial notebook, or teaching material for club members, or converting an existing notebook into club format. Covers the required cell structure, the jupytext .py convention, data access rules, and the pedagogical standards a lesson must meet.
---

# Writing a TUD Quant lesson

Lessons are read by first- and second-semester students in a room, live, on
free-tier Colab. They are not demos and not documentation.

## Format

Write a `.py` file in jupytext percent format into `curriculum/`. Never write
`.ipynb` — CI rejects it and the render workflow generates notebooks into
`colab/` automatically.

Start every file with the jupytext header and the standard setup cell, copied
verbatim from `curriculum/00_welcome.py`. Do not modify the setup cell.

Name files `NN_topic.py` with a two-digit ordering prefix.

## Required structure

1. **Markdown title cell** — what this lesson teaches and what it assumes the
   reader already knows. One sentence each.
2. **Setup cell** — verbatim, unmodified.
3. **Content**, alternating markdown and code. Keep code cells under about 15
   lines; if a cell is longer, the logic belongs in `tudquant/`.
4. **Exercises** — at least three, ordered so the last one has no clean answer.
5. **A closing question** that the next lesson answers.

## Data access

Always `from tudquant import data` and read from the cache:

```python
px = data.equities("AAPL", start="2020-01-01")
```

Never call an API directly in a lesson. Never use `live=True`. Thirty members
running the same cell would exhaust the free tier mid-session. If a lesson
needs a symbol that is not cached, say so explicitly rather than working
around it — it needs adding to `data-pipelines/universe.yml` first.

Every lesson that backtests must show `data.quality(...)` before the backtest,
not after. Checking the data is part of the method being taught, not a
footnote.

## Pedagogical standards

**Show the failure first.** A lesson that only demonstrates the correct
approach teaches a ritual. Show the naive version, show what breaks, then fix
it. The moving-average lesson should show the strategy beating buy-and-hold,
then reveal the lookahead bias, then fix it.

**Never present a backtest result without its caveat in the same cell.** A
number with a caveat three cells later is a number without a caveat.

**No strategy is presented as working.** Every backtest in the curriculum is an
illustration of a method, never a recommendation. State this where it could be
misread.

**Prefer the question to the answer.** End sections with what the reader should
now be suspicious of.

## Constraints

- Free-tier Colab: roughly 12GB RAM, no persistence, sessions idle out. Nothing
  that runs longer than a few minutes.
- Daily data only. No intraday, no tick.
- Use `vectorbt` for vectorised sweeps, `backtrader` for event-driven order
  logic. Never build an engine.
- Plots: matplotlib defaults are fine. No custom styling.
- Language: English for code and comments. Prose may be German if the rest of
  `curriculum/` is — match what is already there.

## Before finishing

State which claims in the lesson you have not verified by running them, and
confirm the file has no `.ipynb` counterpart.
