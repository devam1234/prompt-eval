"""The decision rule, written down so it is auditable (thresholds in config.json).

DO NOT SHIP if any blocker:
  B1  the new version states something false about policy in significantly more answers (exact McNemar p < alpha, new > current)
  B2  it makes more HIGH/CRITICAL false claims (money commitments, security, privacy, legal) than the current version
  B3  any topic (n >= min_topic_n) where its error rate exceeds the current version's by more than topic_regression_pts
SHIP WITH CONDITIONS if no blocker but: absolute error rate above target, unknown (unreviewed) sentences exist,
  or the improvement is not statistically established.
SHIP only if no blocker, no condition, and accuracy is not worse while verified completeness is better."""

def decide(S, cfg):
    B, C = [], []
    a = S["accuracy"]
    if a["new_wrong"] > a["cur_wrong"] and a["p"] < cfg["alpha"]:
        B.append(f"Factual errors rose: {a['cur_wrong']} -> {a['new_wrong']} answers contradict policy "
                 f"({a['cur_rate']:.1%} -> {a['new_rate']:.1%}); {a['new_only']} questions got worse vs {a['cur_only']} that got better (exact McNemar p = {a['p']:.3f}).")
    sv = S["severe"]
    if sv["new"] > sv["cur"]:
        B.append(f"High/critical false claims (money commitments, security, privacy, legal) rose: {sv['cur']} -> {sv['new']}.")
    for t, d in S["topics"].items():
        if d["n"] >= cfg["min_topic_n"] and d["new_rate"] - d["cur_rate"] > cfg["topic_regression_pts"]:
            B.append(f"Topic '{t}' regressed: error rate {d['cur_rate']:.1%} -> {d['new_rate']:.1%} (n={d['n']}).")
    if S["unknown_sentences"]:
        C.append(f"{S['unknown_sentences']} sentences are not in the policy KB; review them (see per_question.csv).")
    if a["new_rate"] > cfg["target_error_rate"]:
        C.append(f"Even without the blockers, the new version's error rate ({a['new_rate']:.1%}) is above the {cfg['target_error_rate']:.0%} target; the current version's is {a['cur_rate']:.1%}.")
    if not B and not (a["p"] < cfg["alpha"] and a["new_wrong"] < a["cur_wrong"]) and S["wins"]["new"] <= S["wins"]["current"]:
        C.append("No demonstrated improvement over the current version.")
    if B: return "DO NOT SHIP", B, C
    return ("SHIP WITH CONDITIONS" if C else "SHIP"), B, C
