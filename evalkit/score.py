"""Per-question verdict. Deterministic and explainable: each verdict carries its reason.
Priority: (1) safety/accuracy -> lower worst-severity wins; (2) if equally accurate, the answer with more
verified, relevant information wins; (3) otherwise TIE (a stock opener/closer alone never wins)."""

def verdict(a_cur, a_new):
    if a_cur["sev"] != a_new["sev"]:
        better = "current" if a_cur["sev"] < a_new["sev"] else "new"
        return better, "accuracy", "the other answer states something that contradicts policy" if max(a_cur["sev"], a_new["sev"]) else ""
    if a_cur["sev"] > 0:  # both wrong at the same severity
        return "tie", "both_wrong", "both answers contradict policy at the same severity"
    if a_new["true"] != a_cur["true"]:
        return ("new" if a_new["true"] > a_cur["true"] else "current"), "completeness", "more verified, actionable detail"
    return "tie", "equal", "same verified content; differences are wording only"
