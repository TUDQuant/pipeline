# TUD Quant — project rules

Student quant finance club at Börsen-Team TU Darmstadt. Read `ARCHITECTURE.md`
before proposing structural changes; the design decisions there were argued
for and are not up for casual revision.

## Audience

The users are 15–30 first- and second-semester students, most of whom have
never used a terminal. Every choice optimises for "works on the first try in a
Colab session" over elegance. If a change makes the code nicer but the
onboarding harder, it is the wrong change.

## Stack

- Python 3.10+, pandas 2.x, numpy pinned `<2.0` (vectorbt depends on numba)
- Backtesting: `vectorbt` and `backtrader`. **Never write a custom engine.**
- Data: yfinance / Alpha Vantage (equities), ccxt (crypto), FRED (macro)
- Storage: parquet in a Google Shared Drive, written nightly by GitHub Actions
- Members run Colab free tier. Assume ~12GB RAM and no persistence.

## Commands

```bash
pytest -q                                   # must pass before any commit
ruff check tudquant data-pipelines tests    # must be clean
python data-pipelines/update_data.py --group equities --dry-run
```

## Hard rules

1. **Never touch credentials.** Do not read, print, echo, or open
   `*service-account*.json`, `.env`, or anything under `_data/`. Do not add
   secrets to any file. If a task appears to need a secret, stop and say so.
2. **Never commit `.ipynb` outside `colab/`.** Notebooks are `.py` in jupytext
   percent format. See `docs/notebooks.md`. CI enforces this.
3. **Never unpin a dependency** in `requirements-pinned.txt` without being asked
   explicitly. A silent numpy bump breaks vectorbt during a lecture.
4. **Never widen the data universe** in `data-pipelines/universe.yml` without
   being asked. Every symbol is a nightly API call and a file every member syncs.
5. **No new runtime dependencies** without flagging it first. Every dependency is
   something that can fail in a Colab cell in front of a room of people.

## Conventions

- Config lives only in `tudquant/config.py`. No path is hardcoded anywhere else —
  this is what keeps the Phase 2 move to JupyterHub a migration and not a rewrite.
- Every data source adapter returns a `DatetimeIndex` named `date` and lowercase
  columns: `open, high, low, close, volume` (+ `adj_close` where available).
- New validation checks go in `tudquant/validation.py` and get a test in
  `tests/test_validation.py` that injects the fault and asserts it is caught.
  A quality check without a test that proves it fires is decoration.
- Member-facing errors must say what to do next, not just what went wrong.
  Compare: "Drive not mounted" versus "run tudquant.bootstrap() again and
  approve the Drive prompt".

## When writing curriculum

Use the `tudquant-lesson` skill in `.claude/skills/`. Lessons are pedagogical
artefacts, not demos — the guidance there is not optional formatting advice.
