# Setup and operations

For whoever owns infrastructure. Sections 1-5 are the one-time build (already
done — kept as the record of how it was assembled and what to redo if it must be
rebuilt). Section 6 onward is what you actually do week to week.

---

## 1. GitHub Organization

`TUDQuant` org, repo `pipeline`, **public**.

Public is load-bearing, not a preference: the member bootstrap runs
`pip install git+https://github.com/TUDQuant/pipeline.git@main` with no token.
On a private repo every member needs a personal access token, which is exactly
the per-member manual step the design exists to eliminate. Public also gives
free branch protection and lets members link the work when they apply somewhere.

**Never a single shared account.** Every commit would be attributed to one
identity, destroying the attribution members join for.

### Teams and what permissions actually do

GitHub permissions are **repo-wide**. There is no per-directory write
permission — a team with Write can push a branch touching any path. Path-level
control exists only as *required review*, via `CODEOWNERS` plus branch
protection.

| Team | Who | Repo role |
|---|---|---|
| `infrastructure` | Noam + a backup | Admin |
| `curriculum` | Marven + content authors | Write |
| `members` | everyone | Write |

Write is safe here because `main` is protected: nobody can push to it, so the
worst anyone can do unilaterally is open a PR. What stops a member quietly
changing the data layer is `CODEOWNERS` — but only once **"Require review from
Code Owners"** is enabled in the ruleset, which needs a reviewer who is not the
author.

**While infrastructure is one person, leave Code Owners review off and required
approvals at 0.** Turning it on now means infrastructure changes cannot be
merged and nothing ships. Turn both on the day a second person joins
`infrastructure` — that is the actual unlock, not a calendar date.

If you would rather members not have Write at all, give `members` **Read** and
have them fork and open PRs from the fork. More friction per contribution,
stricter by default. For a club whose point is that students contribute
strategies, Write plus a protected `main` is the better trade.

`CODEOWNERS` team slugs must match the org exactly (`@TUDQuant/...`). GitHub
ignores unresolvable teams silently — no error, the file just does nothing.
Check the repo's CODEOWNERS settings page after editing it.

### Branch protection ruleset

Settings → Rules → Rulesets, targeting `main`:

- Block force pushes, restrict deletions
- Require a pull request before merging
- Require status checks: **`test`** — note the name. The check reports as
  `ci/test`; GitHub matches on the *job* name, `test`. Requiring `ci` (the
  workflow name) makes every PR wait forever on a check that never reports.
- **Required approvals: 0** while the infrastructure team is one person. You
  cannot approve your own PR, so 1 deadlocks you. Raise it when a backup joins.
- Leave "require branches to be up to date" **off**. It forces a rebase before
  every merge for little benefit here.

Do not attempt to give GitHub Actions a bypass — it is not an available bypass
actor. See `docs/notebooks.md` for why nothing in CI needs to push to `main`.

### On the repo name and what members can see

The repo is called `pipeline` but holds the library, the pipelines, the
curriculum and member strategies. The name is narrower than the contents.
Renaming it (e.g. to `quant`) is cheap — GitHub redirects the old URL — but the
bootstrap string appears in nine files including two generated notebooks, so it
is a small PR rather than a settings toggle. Worth doing before the cohort
arrives and starts bookmarking things; not worth doing mid-semester.

Splitting into separate repos is worse here: it breaks the one-line install, and
cross-repo coordination is real overhead for a club where the same two or three
people touch everything.

**Because the repo is public, members see all of it** — there is no clone link
to share and nothing is gated. `ARCHITECTURE.md`, `SETUP.md` and
`docs/working-with-claude.md` are as visible as the curriculum. That is fine and
mostly good: the decision record is the most useful thing a member can read to
understand why the environment looks the way it does.

Nothing in these docs is a credential. Secret *names* are public; values live in
GitHub secrets. The service account email is an identifier, useless without the
key.

`docs/working-with-claude.md` is internal operations guidance rather than
club-facing documentation. Harmless publicly; if that bothers you, move it to the
org wiki rather than deleting it — a successor will want it.

## 2. Google Cloud service account

The nightly job runs unattended, so it authenticates as a machine.

Current: `tud-quant-pipeline@tud-quant-pipeline-proj.iam.gserviceaccount.com`,
owned by the club, **not** by a personal Google account. If it ever needs
recreating and `iam.disableServiceAccountKeyCreation` is enforced on the
`boersen-team.de` org, either ask the Workspace admin for a project-level
exception or use Workload Identity Federation, which needs no downloaded key at
all and is the better answer.

### The thing that will otherwise cost you an evening

A service account has **no Drive storage quota of its own.** It cannot write to
"My Drive" — not yours, not anyone's. Only into a **Shared Drive**.

1. Shared Drive named `TUD Quant`, containing a folder named **`Data`**
   (capital D — see §5).
2. Service account added as **Content manager** on the Shared Drive.
3. `Data`'s folder ID is `GDRIVE_FOLDER_ID`.

Every Drive API call in `data-pipelines/drive.py` passes `supportsAllDrives=True`,
and every list call also `includeItemsFromAllDrives=True`. Omit either and the
API returns an empty result rather than an error.

## 3. Repository secrets

`Settings → Secrets and variables → Actions`:

| Secret | Source |
|---|---|
| `GDRIVE_SERVICE_ACCOUNT_JSON` | Full contents of the service account key |
| `GDRIVE_FOLDER_ID` | ID of the `Data` folder in the Shared Drive |
| `ALPHAVANTAGE_API_KEY` | Club Alpha Vantage account |
| `FRED_API_KEY` | Club FRED account |

Both API keys must be registered to a **club** address. A key on a personal
email breaks the day that person graduates.

The service account JSON goes into the secret and nowhere else. Delete the
downloaded file from disk afterwards — a key sitting in `~/Downloads` is the
same exposure as a committed one.

## 4. Workspace

- Confirm **Colab is enabled** for the tenant (admin console → Additional Google
  services). It is not on by default.
- Each member gets a club account on joining. Offboarding is disabling the user,
  which revokes Drive access in the same action.

---

## 5. Onboarding a member

Three steps. The third is the one that goes wrong.

1. Create their club Workspace account.
2. Send them `colab/00_welcome.ipynb` (open via Colab → GitHub → `TUDQuant/pipeline`).
3. **Add them as a MEMBER of the `TUD Quant` Shared Drive** — open the Shared
   Drive → *Manage members* → add their address → role **Viewer**.

### Why step 3 is not "share the Data folder with them"

Sharing the folder looks equivalent and is not. Colab's Drive mount exposes
`/content/drive/Shareddrives/<name>` **only for Shared Drives the user is a
member of.** A folder shared *from* a Shared Drive appears under "Shared with
me" instead, at a path Colab does not surface. The mount succeeds, the path
does not exist, and the member sees "data directory not found" — which reads
like a broken environment rather than a missing permission.

Viewer, not Editor: the pipeline writes, members read, nobody deletes the cache
by accident.

Personal Gmail accounts cannot be members unless Workspace admin allows external
members on Shared Drives. Real members have club accounts, so this only affects
testing.

---

## 6. Weekly operations

**Check the nightly pipeline.** It runs on cron (23:15 UTC weekdays for equities
and macro, 00:30 daily for crypto) and needs no intervention, but degradation is
silent:

```bash
gh run list --workflow=update-data --limit=5
```

Then in a notebook, `data.catalogue()` — every row should read `ok: True`.

**Before each session**, run `colab/smoke_test.ipynb` on a club account that is
not yours. Everything should PASS except FRED, which correctly SKIPs because
club API keys never live in a member session. Your own machine has a symlink and
a hand-built venv no member has, which makes you the least representative tester
available.

**After changing a notebook source**, confirm `colab/` actually updated on
`main`. `python scripts/render_notebooks.py`, commit, merge the PR — a pushed
branch has not reached anyone.

---

## Known failure modes

**Colab upgrades its preinstalled packages without warning.** The single most
likely thing to break a lecture. `requirements-pinned.txt` pins the stack and
`bootstrap()` warns loudly when the runtime has drifted. Test any bump on a
throwaway Colab runtime before merging.

**Binance blocks datacenter IPs.** GitHub Actions runners sit in those ranges, so
`ccxt.binance` may fail in CI while working from a laptop. `sources/crypto.py`
falls back to Kraken then Coinbase automatically.

**Free-tier Colab sessions idle out and cap around 12 hours.** Fine because
members read prepared data rather than computing it, but no long-running
optimisations in a notebook. That limit is the concrete trigger for Phase 2.

**Alpha Vantage's free tier is very tight.** It exists as a fallback inside the
nightly pipeline only. If it ever appears in a member notebook, that is a bug.
