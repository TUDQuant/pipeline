# Why notebooks are committed as `.py`

## The rule

- **You edit `.py`.** Jupytext "percent" format — every `# %%` is a cell.
- **CI generates `colab/*.ipynb`.** Never edit those; your change will be overwritten on the next merge.
- CI fails any pull request containing an `.ipynb` outside `colab/`.

## Why

An `.ipynb` is JSON containing source, outputs, execution counts and base64 images. Two members editing the same lesson produce a merge conflict inside a JSON blob with embedded PNGs. It cannot be resolved by hand, and with 15–30 members it will happen in the first month.

Committing `.py` instead makes diffs readable, review possible, and merges ordinary.

## Why not just "keep logic in modules and notebooks thin"

That is good practice and we do it too — anything reusable belongs in `tudquant/`. But it does not solve the problem. A thin notebook is still `.ipynb`, still JSON, still conflicts. It reduces the size of the mess without changing its nature.

## Why not "commit only `.py` and drop `.ipynb` entirely"

Because Colab cannot open a `.py` from GitHub with one click, and one-click is the entire onboarding promise. So we keep generated notebooks in `colab/` purely as build output.

## Rendering

Render locally before you commit:

```bash
python scripts/render_notebooks.py
```

The script exists rather than a bare `jupytext` loop because nbformat 4.5 gives
every cell a random `id`, so plain jupytext renders the same source to a
different file each time. The script assigns deterministic ids instead, which is
what makes "is `colab/` up to date?" a question a diff can answer.

CI verifies that `colab/` matches the sources and fails the PR if it does not.
CI deliberately does not generate the notebooks itself: a bot commit would land
on the PR head without triggering a CI run, which leaves the required status
check missing and the pull request permanently unmergeable.

`.gitattributes` marks them `linguist-generated` (they stay collapsed in PR diffs) and `merge=ours` (they never produce a conflict).

## Working day to day

```bash
pip install jupytext

jupytext --to notebook curriculum/03_momentum.py   # edit locally as a notebook
jupytext --to py:percent 03_momentum.ipynb         # convert back before committing
```

In Colab: File → Download → `.py`, then commit that. Or `jupytext --set-formats ipynb,py:percent` once and let it sync both automatically.

## The part that actually matters

This convention is enforced by CI, not by discipline. Conventions that depend on thirty beginners remembering a rule do not survive the semester; conventions that fail the build do.
