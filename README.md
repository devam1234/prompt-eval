# Is the new prompt better?

**Answer: DO NOT SHIP as it stands.** The new prompt is friendlier and more helpful, and it wins more
head-to-heads (154 vs 51). But it contradicts company policy in **41** answers against **24** for the current
prompt, and the extra errors are almost all **refund promises**: 2 wrong answers before, 28 after, out of 60 refund
questions. Outside refunds the new prompt is actually *better* (13 errors vs 22), so the fix is targeted.
Full evidence: [`results/report.md`](results/report.md). Per-question labels: [`results/verdicts.csv`](results/verdicts.csv).

## Run the web app (backend + frontend)
```bash
python -m evalkit.server          # no installs needed; opens http://127.0.0.1:8000
```
- **Result** tab: verdict, headline numbers, errors by topic, the false claims the new prompt makes, recommendation.
- **Questions** tab: all 300 questions, filter by topic / winner / false claims, expand one to see both answers with each sentence marked (red = contradicts policy, grey = filler, amber = not in policy table). Download `verdicts.csv`.
- **Check an answer** tab: paste any question + answer and see which sentences break policy.
- **Use your own data** tab: upload a CSV (`id, topic, question, answer_current, answer_new`) and the whole evaluation re-runs.

Backend: `evalkit/server.py` (Python standard library only, JSON API: `/api/summary`, `/api/questions`, `/api/check`, `/api/evaluate`, `/api/verdicts.csv`). Frontend: `web/index.html` (one file, no build step, works offline).

## Command line (same engine, for CI)
```bash
pip install pytest
python -m evalkit.run --data data/questions.csv     # writes results/, exits 1 on DO NOT SHIP
pytest -q                                           # 8 tests
```
Outputs: `results/report.md` (short report ending in the recommendation), `verdicts.csv` (`id,better` with
current / new / tie, as the brief asks), `per_question.csv` (reason + the specific false claims per answer), `summary.json`.

## What I found in the data (and why the design looks the way it does)
- The new answers are the current answer **plus** a stock opener/closer (10 fixed phrases, ~39% of the new text)
  **plus** extra how-to detail. So "which one reads better" is a trap: the new one always looks warmer and fuller.
- No policy document was provided, so correctness has to be inferred. Each true policy statement appears 7-17x
  across the 600 answers; each contradicting claim appears 1-6x. I turned that into
  [`data/policy_kb.json`](data/policy_kb.json): 26 false claims, each tagged **critical** (security / privacy / legal),
  **high** (a money or service commitment) or **medium**, with the policy it violates. `scripts/derive_kb.py` regenerates the candidate list.
- The current version is not clean either (8% wrong, incl. critical ones such as denying data-export requests and
  accepting an email change without confirmation). The new version *fixes* many of those, but introduces a systematic
  over-generous refund pattern: no deadline, instant refunds, free return shipping, refunds on gift cards and licences.

## How it scores (criteria)
1. **Accuracy vs policy (primary).** Strip filler, split into sentences, classify each as true / false / unknown against the KB.
   Plus a condition-aware rule (a customer whose tracking is stalled 7+ days must be told how to escalate).
2. **Severity.** Critical > high > medium. A promise the company will have to honour matters more than a harmless slip.
3. **Completeness.** Among equally accurate answers, more verified, actionable detail wins.
4. **Style.** Filler alone never wins: if the substance is identical the question is a **tie**.

Verdict per question follows that order. Stats: paired by question, exact McNemar test for error rates, bootstrap 95% CI,
sign test for wins. Thresholds are in `config.json`, and the rule is written in `evalkit/decide.py` (blockers vs conditions)
so the bar is fixed *before* anyone sees a result.

Key numbers: error rate 8.0% -> 13.7% (paired +5.7 pts, CI +0.7 to +10.3, McNemar p = 0.033); high/critical false claims 12 -> 35;
refunds 3.3% -> 46.7%. Robustness (in the report): treating the closest-call claim (gift cards, 8 vs 6) as unknown makes the overall
test non-significant (p = 0.098) but the severity and refunds blockers still trigger, so the verdict does not depend on it.

## Design note: running this on every change to the assistant
- **Make it a merge gate.** `.github/workflows/eval.yml` runs the tests and the eval on any PR that touches the prompt, the KB, the data or the harness. Exit code 1 (DO NOT SHIP) fails the check; `report.md` is attached to the PR.
- **Make the policy a versioned, owned asset.** The KB is the real "test oracle". Keep it in the repo, require sign-off from the policy owner for changes, and fail the run on any *unknown* sentence so new claims are reviewed instead of silently passing. (Today the KB is inferred from the data and needs that sign-off.)
- **Generate answers in CI.** Replace the static CSV with a step that runs the baseline (main) and candidate prompts over a frozen question set and writes the same two columns, so a developer submits a prompt, not a spreadsheet. Pin model, temperature and prompt hash in `summary.json` for reproducibility.
- **Gate on guardrails, trend on quality.** Hard blockers: more false claims, more high/critical claims, or any topic regressing. Helpfulness and completeness are reported but cannot buy back an accuracy regression, because they did not here.
- **Keep the question set alive.** Add every real escalation and complaint as a permanent test, track per-topic sample sizes (60 refund questions is enough to see a 44-point jump, not a 3-point one), and re-label a small human sample each month to check the KB.
- **LLM judge as second opinion only.** `--llm-check` runs a policy-grounded LLM judge in both A/B orders and reports agreement with the rule-based verdict. It covers answers phrased in ways the sentence matcher has not seen. The primary verdict stays deterministic, free and reproducible.

## Limitations (honest)
- **Ground truth is inferred, not provided.** If the company's real policy differs (e.g. gift cards *are* refundable), edit `policy_kb.json` and re-run. I checked that the overall verdict survives dropping the least certain claim.
- The sentence matcher relies on this dataset's templated wording. For free-form production answers it will report many *unknown* sentences, which is when the LLM check (or human review) takes over. `--llm-check` was **not executed** here (no API key); the primary pipeline and all tests were.
- 300 questions, 93 distinct intents: many questions are near-duplicates, so statistical power is lower than 300 suggests. Treat p-values as indicative, and treat the topic-level result (refunds) as the strongest evidence.
- "Completeness" counts verified sentences; it does not judge whether extra detail was needed for that question.

## Layout
```
evalkit/  data.py kb.py score.py stats.py decide.py report.py pipeline.py run.py server.py judge.py(optional)
web/      index.html (frontend)
data/     questions.csv (provided)  policy_kb.json (derived ground truth)  DATA_README.txt
scripts/  derive_kb.py     tests/  test_core.py     config.json     .github/workflows/eval.yml     results/
```
