# One-time setup

For whoever owns infrastructure. Roughly a weekend, most of it waiting on other people. Do steps 1 and 2 first — they involve other humans and have the longest lead time.

---

## 1. GitHub Organization

Create a free Organization (`tud-quant`). Individual member accounts, real attribution, real permissions.

Teams:

| Team | Members | Access |
|---|---|---|
| `infrastructure` | you + 1 backup | Admin |
| `curriculum` | Marven + content authors | Write on `curriculum/` |
| `members` | everyone | Write on `strategies/`, Read elsewhere |

**Never a single shared account.** Every commit would be attributed to one identity, which destroys the thing members join for — being able to point at their own work when they apply somewhere.

Repos are **public**. This makes `pip install` from GitHub a one-liner with no token per member, gives you branch protection on the free tier, and makes the work visible for recruiting.

Branch protection on `main`: require a pull request, require one approving review, require the `ci` check to pass, require `CODEOWNERS` review.

> Worth applying for [GitHub for Nonprofits](https://github.com/solutions/industry/nonprofits) (free Team plan), but read the eligibility first — it excludes organizations that are academic in nature, and a university student e.V. is exactly the ambiguous case. Apply, don't plan around it.

## 2. Google Cloud service account

The nightly job runs unattended, so it authenticates as a machine, not as you.

1. In the club's GCP project: **IAM → Service Accounts → Create**. Name it `tud-quant-pipeline`. No project roles needed.
2. **Keys → Add key → JSON.** Download it. This file is a credential — it goes into a GitHub secret and nowhere else, never into the repo.
3. Enable the **Google Drive API** for the project.

### The thing that will otherwise cost you an evening

A service account has **no Drive storage quota of its own.** It cannot write to "My Drive" — not yours, not anyone's. It can only write into a **Shared Drive**.

So:

1. Create a **Shared Drive** named `TUD Quant` (Drive → Shared drives → New). This needs Workspace, which is one more reason members get club accounts.
2. Add the service account's email (`tud-quant-pipeline@….iam.gserviceaccount.com`) as **Content manager**.
3. Create a `data` folder inside it. Its ID is the last path segment of the URL — that's `GDRIVE_FOLDER_ID`.
4. Give all club members **Viewer** on the Shared Drive. Read-only is correct: the pipeline writes, members read. Nobody deletes the cache by accident.

Every Drive API call in `data-pipelines/drive.py` passes `supportsAllDrives=True`, and every list call also passes `includeItemsFromAllDrives=True`. Omit either and the API returns an empty result rather than an error, which is a genuinely miserable hour of debugging.

## 3. Repository secrets

`Settings → Secrets and variables → Actions`:

| Secret | Where it comes from |
|---|---|
| `GDRIVE_SERVICE_ACCOUNT_JSON` | Contents of the JSON key from step 2 |
| `GDRIVE_FOLDER_ID` | Folder ID from step 2 |
| `ALPHAVANTAGE_API_KEY` | Club Alpha Vantage account |
| `FRED_API_KEY` | Club FRED account |

Register both API keys on a **club** address, not a personal one. Otherwise the pipeline breaks the day that person graduates — the same offboarding problem, one layer down.

## 4. Workspace

- Confirm **Colab is enabled** for your tenant. It is an admin-toggled additional service and is not on by default. If it's off, Phase 1 has no compute story.
- Each member gets an account on joining. Offboarding is disabling the user, which revokes Drive access in the same action.
- Add the `TUD Quant` Shared Drive to each member's Drive during onboarding, or the mount path won't resolve.

## 5. First run

```bash
gh workflow run update-data.yml -f group=all
```

Then open `colab/smoke_test.ipynb` in Colab with a club account. Every line should read PASS or SKIP. Hand it to one member who is not you before you hand it to twenty.

---

## Known failure modes

**Binance blocks datacenter IPs.** GitHub Actions runners sit in exactly those ranges, so `ccxt.binance` may fail in CI while working fine from your laptop. `sources/crypto.py` falls back to Kraken then Coinbase automatically. If crypto data goes stale, check which exchange actually served it before assuming the pipeline is broken.

**Colab upgrades its preinstalled packages without warning.** This is the single most likely thing to break a lecture. `requirements-pinned.txt` pins the stack and `bootstrap()` prints a loud warning when the runtime has drifted. `numpy` is held below 2.0 on purpose because vectorbt depends on numba. Before bumping anything mid-semester, test on a throwaway Colab runtime.

**Free-tier Colab sessions idle out and cap around 12 hours.** Nothing persists. This is fine because members read prepared data rather than computing it, but it does mean no long-running optimisations in a notebook. That limit is the concrete trigger for Phase 2.

**Alpha Vantage's free tier is very tight** (25 requests/day at time of writing). It exists as a fallback inside the nightly pipeline only. If it ever appears in a member notebook, that's a bug.
