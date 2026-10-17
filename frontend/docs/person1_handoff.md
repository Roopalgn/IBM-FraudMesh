# Person 1 integration handoff

Frontend branch: `feat/dashboard` in `Roopalgn/IBM-FraudMesh`, based on reviewed `71f5866`. Only frontend files are owned here. No main push, force push, revert or backend/ML/graph modification was performed.

The team's main branch was reviewed as README-only; dashboard restoration is yours to coordinate. Fetch current refs, inspect `git diff origin/main...origin/feat/dashboard -- frontend`, and open a normal PR from feat/dashboard to main (or your integration branch). Review existing revert history before choosing a merge. Do not blindly revert the revert or replay the old dashboard commit; this branch already contains its original implementation plus the adaptation work. Merge only after repository checks and contract approval.

From a teammate checkout: `cd frontend` then `node server.mjs`. Tests: `node --test tests/*.test.mjs` and `node --check src/app.js`. No install/build is needed for runtime.

Approve or adjust the minimal scenario-reference envelope in `docs/data_contract.md` at the dedicated API/adapter boundary. The response mapping follows corrected graph commit `34822ed09e167a810abc29cdde5104b569e84b72`, not the earlier frontend schema. Keep raw bank ledgers, labels and linkage secrets outside browser requests. Configure your actual CORS origin and test real endpoint reachability.

Confirm LinuxONE/security deployment evidence independently before changing unverified status. The frontend does not accept a bare verified boolean as proof. Obtain ML flag counts separately if needed; do not infer flags from graph structures or turn missing values into zero.

Generated fixtures and the HTTP harness unblock frontend review but do not establish live integration. The corrected local-control fixture yields one local cycle; the split-bank fixture yields zero local structures and one combined cycle. These are controlled examples, not performance benchmarks.
