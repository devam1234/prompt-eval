def _p(x): return f"{x:.1%}"

def write_report(S, path):
    a, sv, w, L = S["accuracy"], S["severe"], S["wins"], []
    L += ["# Is the new prompt better? Evaluation report", "",
          f"**Bottom line: {S['verdict']}.** The new version is more helpful and wins more head-to-heads ({w['new']} vs {w['current']}), "
          f"but it contradicts company policy in {a['new_wrong']} answers against {a['cur_wrong']} for the current version, and the damage is concentrated in refunds.", "",
          "## How the 300 questions were scored", "",
          "1. **Ground truth.** No policy document was supplied, so `data/policy_kb.json` was derived from the data: every correct policy statement appears 7-17 times across the 600 answers, while each contradicting claim appears 1-6 times. **A policy owner should confirm this file.**",
          "2. **Sentence-level checking.** Each answer is split into sentences; stock openers/closers (10 phrases such as \"Great question!\") are removed, every remaining sentence is checked against the KB: *true*, *false* (contradicts policy, tagged critical / high / medium), or *unknown*. A rule also checks condition-dependent answers (e.g. tracking stalled 7+ days must mention how to escalate).",
          "3. **Verdict per question** (`verdicts.csv`): the answer with the less severe policy error wins; if equally accurate, the one with more verified detail wins; otherwise tie. Wording alone never wins.",
          f"4. **Statistics.** Paired by question; exact McNemar test for error rates, bootstrap 95% CI, sign test for wins. {S['n']} questions, {S['n_intents']} distinct intents.", "",
          "## Headline", "", "| | Current | New |", "|---|---|---|",
          f"| Answers contradicting policy | {a['cur_wrong']} ({_p(a['cur_rate'])}) | **{a['new_wrong']} ({_p(a['new_rate'])})** |",
          f"| High/critical false claims | {sv['cur']} | **{sv['new']}** |",
          f"| Average length (words) | {S['length']['cur']:.0f} | {S['length']['new']:.0f} ({_p(S['length']['filler_share'])} of new text is stock filler) |",
          f"| Head-to-head wins | {w['current']} | {w['new']} (ties {w['tie']}) |", "",
          f"Paired change in error rate (new - current): **{a['delta'][0]:+.1%}** (95% CI {a['delta'][1]:+.1%} to {a['delta'][2]:+.1%}). "
          f"{a['new_only']} questions got worse, {a['cur_only']} got better, {a['both']} wrong in both; exact McNemar p = {a['p']:.3f}.", "",
          "**Why a quick read says \"ship\":** the new version wins "
          f"{w['by_reason'].get('new|completeness', 0)} questions on extra helpful detail (next steps and where to click). If answers were judged for helpfulness and tone, the new prompt wins "
          f"{w['new'] / max(1, w['new'] + w['current']):.0%} of decided comparisons. The accuracy check is what changes the answer.", "",
          "## Where it goes wrong", "", "| Topic | n | Errors current | Errors new | Change |", "|---|---|---|---|---|"]
    for t, d in sorted(S["topics"].items(), key=lambda x: x[1]["new_rate"] - x[1]["cur_rate"], reverse=True):
        L.append(f"| {t} | {d['n']} | {d['cur_wrong']} ({_p(d['cur_rate'])}) | {d['new_wrong']} ({_p(d['new_rate'])}) | {d['new_rate'] - d['cur_rate']:+.1%} |")
    L += ["", "Outside refunds the new prompt is **better**: "
          f"{S['non_refund']['new_wrong']} errors vs {S['non_refund']['cur_wrong']} for the current version across {S['non_refund']['n']} questions.", "",
          "### False claims by frequency (what the prompt change actually did)", "",
          "| Claim | Severity | New | Current | Actual policy |", "|---|---|---|---|---|"]
    for c in S["claims"][:14]:
        L.append(f"| {c['text']} | {c['severity']} | {c['new']} | {c['cur']} | {c['why']} |")
    L += ["", "The new refund answers are consistently *more generous than policy* (no deadline, instant refunds, free return shipping, refunds on gift cards and licences). "
          "Each of these is a promise a customer can hold the company to. The current version's errors are mostly isolated and spread across topics; the new version's are systematic and one-directional, which points at a specific instruction in the new prompt (likely something encouraging generosity or reassurance).", "",
          "## Robustness checks", "", "| Check | Result |", "|---|---|"]
    for k, v in S["sensitivity"].items():
        L.append(f"| {k} | {v} |")
    L += ["", "## Recommendation", "", f"### {S['verdict']}", ""]
    if S["blockers"]: L += ["**Why:**"] + [f"- {b}" for b in S["blockers"]] + [""]
    if S["conditions"]: L += ["**Also:**"] + [f"- {c}" for c in S["conditions"]] + [""]
    L += ["**Fastest path to a ship decision:**",
          "1. Fix the refund-related instructions in the new prompt (the over-generous claims in the table above), keeping the rest.",
          "2. Re-generate answers for the 300 questions (or just the 60 refund questions plus a sample of the rest) and re-run `python -m evalkit.run`.",
          "3. Ship when: no topic regresses, high/critical false claims are no higher than current, and error rate is statistically no worse. On the current data the new prompt would already meet this outside refunds.",
          "4. Separately: the *current* prompt also contradicts policy in 8% of answers, including critical ones (e.g. denying data-export requests). Worth fixing regardless of this decision.", ""]
    open(path, "w", encoding="utf-8").write("\n".join(L) + "\n")
