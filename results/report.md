# Is the new prompt better? Evaluation report

**Bottom line: DO NOT SHIP.** The new version is more helpful and wins more head-to-heads (154 vs 51), but it contradicts company policy in 41 answers against 24 for the current version, and the damage is concentrated in refunds.

## How the 300 questions were scored

1. **Ground truth.** No policy document was supplied, so `data/policy_kb.json` was derived from the data: every correct policy statement appears 7-17 times across the 600 answers, while each contradicting claim appears 1-6 times. **A policy owner should confirm this file.**
2. **Sentence-level checking.** Each answer is split into sentences; stock openers/closers (10 phrases such as "Great question!") are removed, every remaining sentence is checked against the KB: *true*, *false* (contradicts policy, tagged critical / high / medium), or *unknown*. A rule also checks condition-dependent answers (e.g. tracking stalled 7+ days must mention how to escalate).
3. **Verdict per question** (`verdicts.csv`): the answer with the less severe policy error wins; if equally accurate, the one with more verified detail wins; otherwise tie. Wording alone never wins.
4. **Statistics.** Paired by question; exact McNemar test for error rates, bootstrap 95% CI, sign test for wins. 300 questions, 93 distinct intents.

## Headline

| | Current | New |
|---|---|---|
| Answers contradicting policy | 24 (8.0%) | **41 (13.7%)** |
| High/critical false claims | 12 | **35** |
| Average length (words) | 17 | 40 (39.2% of new text is stock filler) |
| Head-to-head wins | 51 | 154 (ties 95) |

Paired change in error rate (new - current): **+5.7%** (95% CI +0.7% to +10.3%). 37 questions got worse, 20 got better, 4 wrong in both; exact McNemar p = 0.033.

**Why a quick read says "ship":** the new version wins 134 questions on extra helpful detail (next steps and where to click). If answers were judged for helpfulness and tone, the new prompt wins 75% of decided comparisons. The accuracy check is what changes the answer.

## Where it goes wrong

| Topic | n | Errors current | Errors new | Change |
|---|---|---|---|---|
| refunds | 60 | 2 (3.3%) | 28 (46.7%) | +43.3% |
| account | 60 | 4 (6.7%) | 4 (6.7%) | +0.0% |
| product | 50 | 1 (2.0%) | 1 (2.0%) | +0.0% |
| orders | 70 | 10 (14.3%) | 7 (10.0%) | -4.3% |
| shipping | 60 | 7 (11.7%) | 1 (1.7%) | -10.0% |

Outside refunds the new prompt is **better**: 13 errors vs 22 for the current version across 240 questions.

### False claims by frequency (what the prompt change actually did)

| Claim | Severity | New | Current | Actual policy |
|---|---|---|---|---|
| Yes, unused gift cards can be refunded within 30 days like any other item. | high | 5 | 1 | Majority policy: gift cards cannot be refunded (8 vs 6 sentences). Closest call in the data; see sensitivity run. |
| Yes, since the device is faulty you are entitled to a full refund, however long ago you bought it. | high | 5 | 0 | Policy: no refund after 30 days; warranty repair/replacement instead. |
| Yes, we always refund the original shipping fee along with the item price. | high | 5 | 0 | Policy: not refunded unless faulty/wrong item. |
| Return shipping is always free. | high | 4 | 0 | Policy: customer pays unless faulty/wrong item. |
| We send a prepaid label for every return. | high | 4 | 0 | Policy: prepaid label only for faulty/wrong item. |
| No problem, activated licences can be refunded within 30 days. | high | 3 | 1 | Policy: licences cannot be refunded once opened or activated. |
| You can return an item for a full refund at any time, with no deadline. | high | 3 | 0 | Policy: 30 days from delivery. |
| Your refund will be in your account instantly, as soon as you request the return. | high | 3 | 0 | Policy: 5-7 business days after we receive the item. |
| All orders ship the same day they are placed. | medium | 2 | 1 | Policy: within 2 business days. |
| Confirmation emails can take up to 3 days to arrive. | medium | 1 | 4 | Policy: normally within 15 minutes. |
| We do not provide copies of customer data. | critical | 1 | 2 | Customers can request an export from the Privacy page; denying it is a data-rights/compliance problem. |
| Just type the new address in your profile and it changes immediately. | critical | 1 | 1 | Policy requires confirmation from both old and new address; skipping it enables account takeover. |
| You can cancel an order at any point, even after it has shipped, and we will recall the parcel. | high | 1 | 1 | Policy: cancel only before it ships. |
| Shipping is free on every order, with no minimum. | high | 1 | 1 | Policy: free over $50. |

The new refund answers are consistently *more generous than policy* (no deadline, instant refunds, free return shipping, refunds on gift cards and licences). Each of these is a promise a customer can hold the company to. The current version's errors are mostly isolated and spread across topics; the new version's are systematic and one-directional, which points at a specific instruction in the new prompt (likely something encouraging generosity or reassurance).

## Robustness checks

| Check | Result |
|---|---|
| Treat the gift-card claim (the closest call in the data, 8 vs 6 sentences) as unknown | errors 23 -> 36, McNemar p = 0.098 (no longer significant on its own); refunds errors 1 -> 23; the severity and refunds blockers still trigger, verdict unchanged |
| High/critical severity only | questions made worse 32 vs better 9, sign-test p = 0.0004 |
| Judge on accuracy alone (ignore helpfulness) | new wins 20, current wins 37 |
| Bootstrap seed | fixed at 7; results are deterministic (no LLM involved in the primary verdict) |

## Recommendation

### DO NOT SHIP

**Why:**
- Factual errors rose: 24 -> 41 answers contradict policy (8.0% -> 13.7%); 37 questions got worse vs 20 that got better (exact McNemar p = 0.033).
- High/critical false claims (money commitments, security, privacy, legal) rose: 12 -> 35.
- Topic 'refunds' regressed: error rate 3.3% -> 46.7% (n=60).

**Also:**
- Even without the blockers, the new version's error rate (13.7%) is above the 5% target; the current version's is 8.0%.

**Fastest path to a ship decision:**
1. Fix the refund-related instructions in the new prompt (the over-generous claims in the table above), keeping the rest.
2. Re-generate answers for the 300 questions (or just the 60 refund questions plus a sample of the rest) and re-run `python -m evalkit.run`.
3. Ship when: no topic regresses, high/critical false claims are no higher than current, and error rate is statistically no worse. On the current data the new prompt would already meet this outside refunds.
4. Separately: the *current* prompt also contradicts policy in 8% of answers, including critical ones (e.g. denying data-export requests). Worth fixing regardless of this decision.

