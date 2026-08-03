# Deploy checklist — from "it works on my Mac" to "it works for the club"

Written against the actual state of `TUDQuant/pipeline` after the first manual
pipeline run. Do these in order; the numbering matters because later items
depend on earlier ones.

---

## 0. Rotate both API keys — first, today

The FRED key and the Alpha Vantage key were both pasted in plaintext into a
chat transcript, and that transcript is now a file that has been moved around.
Treat both as public.

- FRED: https://fredaccount.stlouisfed.org/apikeys → revoke, request a new one
- Alpha Vantage: request a new key from a club address

Then update the two GitHub secrets. Neither key is expensive to lose, but the
habit is the point: a key that has appeared in a document is a key you rotate,
every time, without debating whether it matters.

While you're there: register both on a club address if they aren't already. A
key tied to a personal email breaks the day that person graduates.

---

## 1. Get git working locally

Right now the local folder was drag-and-dropped into GitHub through the web UI,
which means your machine and the repo can drift apart with nothing to reconcile
them. Every fix you made locally — the numpy/numba resolution, the plotly
downgrade, the yfinance upgrade — currently exists only on your laptop.

GitHub disabled password auth for git operations, which is why the clone
failed. Pick one:

- **GitHub Desktop** — sign in with the browser, clone, commit and push with
  buttons. For a club where the next infra lead may not be a terminal person,
  this is the defensible choice.
- **`gh auth login`** — the GitHub CLI handles the token for you, and you need
  `gh` anyway for `gh workflow run`.

Then clone fresh into a sane location (not `~/Downloads`) and copy your working
changes in. Do not keep editing the Downloads copy.

---

## 2. Make the repository public

Symptom that gave this away: organization secrets scoped to "Public
repositories" were invisible to `pipeline`, so you had to re-add them as
repository secrets.

That's fine as a workaround, but a private repo breaks the thing the whole
Phase 1 design rests on: members installing the club package with one line and
no token. `pip install git+https://github.com/TUDQuant/pipeline.git` only works
without credentials on a public repo.

Settings → General → Danger Zone → Change visibility → Public. Then delete the
duplicated repository secrets and let the organization ones do their job.

Before flipping: confirm nothing sensitive was ever committed. Check that
`.gitignore` excludes `*service-account*.json` and `.env`, and search the repo
for the two API keys. If a key was ever committed, rotating it (step 0) is what
actually fixes it — deleting the file does not remove it from history.

---

## 3. Deploy the real workflows

The repo currently has one hand-written `pipeline.yml` with `workflow_dispatch`
only. That means **there is no nightly refresh** — data updates exactly as
often as someone remembers to click a button. It also means `colab/` is never
generated, which is why `colab/smoke_test.ipynb` doesn't exist for members to
open.

Replace it with the three workflows in `.github/workflows/`:

| File | What it does | Why it matters |
|---|---|---|
| `update-data.yml` | Cron: equities+macro 23:15 UTC weekdays, crypto 00:30 daily | The actual automation |
| `render-notebooks.yml` | Renders `curriculum/*.py` → `colab/*.ipynb` on merge | Without it members have nothing to click |
| `ci.yml` | Tests, lint, rejects stray `.ipynb` | Keeps the convention alive past week two |

Delete `pipeline.yml` once `update-data.yml` runs green — two workflows doing
the same job will double your API calls and race each other writing to Drive.

---

## 4. Take the corrected pins

`requirements-pinned.txt` in the repo did not match what actually works — that
mismatch is what cost you an evening. It now pins the set your own passing run
demonstrated, with `numba` and `llvmlite` named explicitly so pip cannot
resolve its way back into a numpy 2.x install, and `plotly<6` because vectorbt
0.26.2 references a trace type plotly 6 removed.

Workflows now use Python 3.10. numba 0.56.4 has no wheels for 3.12+, so the
`3.11` they had before was wrong too.

**Do not run `pip freeze > requirements-pinned.txt`.** It dumps sixty
transitive packages, bakes in macOS-only resolutions, and destroys the comments
that explain why each awkward pin exists. Edit it by hand.

---

## 5. Fix the macro data quality failures

Your catalogue shows all six FRED series failing with one error each. That was
a bug in the validator, not bad data: the "none" calendar fell through to a
daily comparison, so monthly CPI looked 97% missing. Fixed in
`tudquant/validation.py`, with regression tests.

After redeploying and re-running, all six should read `ok: True`.

---

## 6. Fix the missing equities

Your catalogue has 9 datasets: 3 crypto, 6 macro, **0 equities**. The equity
leg is silently failing — yfinance gets rate-limited from GitHub Actions IPs,
and the Alpha Vantage fallback needs a working key (see step 0).

The yfinance bump in step 4 should fix it. Verify by reading the `update-data`
log for the `== equities ==` block rather than assuming.

A curriculum built on crypto and macro only is not the program Marven
described. This one is worth confirming before you tell anyone the pipeline is
done.

---

## 7. Then, and only then: Workspace and first real run

**Enable Colab** for the tenant (admin console → Additional Google services).
It is not on by default. If it's off, nothing above reaches a member.

**Onboarding, per member:** club Workspace account → add the `TUD Quant` Shared
Drive to their Drive → Viewer permission on the Shared Drive. Viewer, not
Editor: the pipeline writes, members read, nobody deletes the cache by
accident.

**First run:**

```bash
gh workflow run update-data.yml -f group=all
```

Then read the log — specifically that all three groups appear and the equities
block is not empty.

**Then the smoke test, in Colab, on a club account, not yours.** Open
`colab/smoke_test.ipynb` (which now exists, because of step 3). Every line
should read PASS or SKIP.

Hand it to one member who is not you before you hand it to twenty. Your machine
has a symlink, a `.zshrc` export and a hand-repaired virtualenv that no member
will have. You are the least representative tester available.

---

## Carry-forward: the service account

The service account currently lives in a GCP project under a personal Google
account, because `iam.disableServiceAccountKeyCreation` is enforced on the
`boersen-team.de` organization and you don't have the org policy admin role.

It works. It is also the exact failure mode this design was meant to avoid: the
club's entire data layer depends on one person's private Google account, and
nobody else can regenerate that key.

Two ways out, in order of preference:

1. **Workload Identity Federation.** GitHub Actions authenticates to GCP via
   OIDC with no downloaded key at all. The org policy blocks *key creation*,
   not service accounts — so this sidesteps it entirely and is genuinely more
   secure than a JSON key sitting in a secret. Needs IAM permissions on a
   club-org project; ask whoever administers it.
2. **Ask the Workspace admin** for a project-level exception, or to create the
   service account and hand you the key.

Either way, write it down as known debt with your name on it, and don't let it
quietly become permanent. The policy you disabled your way around exists
because downloadable service account keys leak.
