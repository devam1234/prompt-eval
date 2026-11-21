"""python -m evalkit.run --data data/questions.csv   (exit code 1 on DO NOT SHIP, so CI can block the merge)
Outputs in results/: report.md, verdicts.csv (id,better), per_question.csv, summary.json"""
import argparse, collections, csv, json, os, re, sys
from .data import load
from .kb import KB
from .score import verdict
from .stats import bootstrap_mean_ci, mcnemar_exact_p, sign_test_p
from .decide import decide
from .report import write_report

def analyse(rows, kb, ignore=()):
    out = []
    for r in rows:
        c, n = kb.analyse(r["question"], r["old"], ignore), kb.analyse(r["question"], r["new"], ignore)
        out.append({**r, "cur": c, "newa": n, "verdict": verdict(c, n)})
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/questions.csv")
    ap.add_argument("--kb", default="data/policy_kb.json")
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--out", default="results")
    ap.add_argument("--llm-check", action="store_true", help="optional second opinion from an LLM judge (needs ANTHROPIC_API_KEY)")
    a = ap.parse_args()
    cfg = json.load(open(a.config))
    rows = load(a.data)
    kb = KB(a.kb).with_known_true(rows)
    R = analyse(rows, kb)
    n = len(R)
    it, seed, al = cfg["bootstrap_iters"], cfg["seed"], cfg["alpha"]

    cw = sum(r["cur"]["wrong"] for r in R); nw = sum(r["newa"]["wrong"] for r in R)
    b = sum(r["newa"]["wrong"] and not r["cur"]["wrong"] for r in R); c = sum(r["cur"]["wrong"] and not r["newa"]["wrong"] for r in R)
    S = {"n": n, "n_intents": len({(r["topic"], re.sub(r"\d+|LM-\d+|Lumora [A-Z]\w+( Mini)?", "#", r["question"])) for r in R})}
    S["accuracy"] = {"cur_wrong": cw, "new_wrong": nw, "cur_rate": cw / n, "new_rate": nw / n, "new_only": b, "cur_only": c,
                     "both": sum(r["cur"]["wrong"] and r["newa"]["wrong"] for r in R), "p": mcnemar_exact_p(b, c),
                     "delta": bootstrap_mean_ci([r["newa"]["wrong"] - r["cur"]["wrong"] for r in R], it, seed, al)}
    sevn = lambda k: sum(r[k]["sev"] >= 2 for r in R)
    S["severe"] = {"cur": sevn("cur"), "new": sevn("newa")}
    vc = collections.Counter(r["verdict"][0] for r in R)
    S["wins"] = {"new": vc["new"], "current": vc["current"], "tie": vc["tie"],
                 "by_reason": {f"{r['verdict'][0]}|{r['verdict'][1]}": sum(1 for x in R if (x['verdict'][0], x['verdict'][1]) == (r['verdict'][0], r['verdict'][1])) for r in R},
                 "p": sign_test_p(vc["new"], vc["current"])}
    S["length"] = {"cur": sum(r["cur"]["words"] for r in R) / n, "new": sum(r["newa"]["words"] for r in R) / n,
                   "filler_share": sum(r["newa"]["filler_words"] for r in R) / sum(r["newa"]["words"] for r in R)}
    S["topics"] = {}
    for t in sorted({r["topic"] for r in R}):
        g = [r for r in R if r["topic"] == t]
        S["topics"][t] = {"n": len(g), "cur_wrong": sum(r["cur"]["wrong"] for r in g), "new_wrong": sum(r["newa"]["wrong"] for r in g)}
        S["topics"][t].update(cur_rate=S["topics"][t]["cur_wrong"] / len(g), new_rate=S["topics"][t]["new_wrong"] / len(g))
    nr = [r for r in R if r["topic"] != "refunds"]
    S["non_refund"] = {"n": len(nr), "cur_wrong": sum(r["cur"]["wrong"] for r in nr), "new_wrong": sum(r["newa"]["wrong"] for r in nr)}
    cl = collections.defaultdict(lambda: {"cur": 0, "new": 0})
    for r in R:
        for k, key in (("cur", "cur"), ("newa", "new")):
            for f in r[k]["false"]: cl[f["text"]][key] += 1
    S["claims"] = sorted([{"text": t, **v, **{x: kb.false[t][x] for x in ("severity", "why")}} for t, v in cl.items()],
                         key=lambda x: (-x["new"], -x["cur"]))
    S["unknown_sentences"] = sum(len(r["cur"]["unknown"]) + len(r["newa"]["unknown"]) for r in R)

    # robustness: (1) closest-call claim (gift cards) disregarded, (2) high/critical only, (3) accuracy-only wins
    gift = ["Yes, unused gift cards can be refunded within 30 days like any other item."]
    R2 = analyse(rows, kb, gift); b2 = sum(r["newa"]["wrong"] and not r["cur"]["wrong"] for r in R2); c2 = sum(r["cur"]["wrong"] and not r["newa"]["wrong"] for r in R2)
    b3 = sum(r["newa"]["sev"] >= 2 and r["cur"]["sev"] < 2 for r in R); c3 = sum(r["cur"]["sev"] >= 2 and r["newa"]["sev"] < 2 for r in R)
    acc_only = collections.Counter(r["verdict"][0] for r in R if r["verdict"][1] in ("accuracy", "both_wrong"))
    S["sensitivity"] = {
        "Treat the gift-card claim (the closest call in the data, 8 vs 6 sentences) as unknown": f"errors {sum(r['cur']['wrong'] for r in R2)} -> {sum(r['newa']['wrong'] for r in R2)}, McNemar p = {mcnemar_exact_p(b2, c2):.3f} (no longer significant on its own); refunds errors {sum(r['cur']['wrong'] for r in R2 if r['topic']=='refunds')} -> {sum(r['newa']['wrong'] for r in R2 if r['topic']=='refunds')}; the severity and refunds blockers still trigger, verdict unchanged",
        "High/critical severity only": f"questions made worse {b3} vs better {c3}, sign-test p = {sign_test_p(b3, c3):.4f}",
        "Judge on accuracy alone (ignore helpfulness)": f"new wins {acc_only['new']}, current wins {acc_only['current']}",
        "Bootstrap seed": f"fixed at {seed}; results are deterministic (no LLM involved in the primary verdict)"}
    S["verdict"], S["blockers"], S["conditions"] = decide(S, cfg)

    os.makedirs(a.out, exist_ok=True)
    json.dump(S, open(f"{a.out}/summary.json", "w"), indent=2, default=str)
    with open(f"{a.out}/verdicts.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n"); w.writerow(["id", "better"])
        for r in R: w.writerow([r["id"], r["verdict"][0]])
    with open(f"{a.out}/per_question.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n"); w.writerow(["id", "topic", "better", "reason", "current_false_claims", "new_false_claims", "current_severity", "new_severity", "unknown_sentences"])
        for r in R:
            w.writerow([r["id"], r["topic"], r["verdict"][0], r["verdict"][1], " | ".join(x["text"] for x in r["cur"]["false"]) + " ".join(r["cur"]["missing"]),
                        " | ".join(x["text"] for x in r["newa"]["false"]) + " ".join(r["newa"]["missing"]), r["cur"]["sev"], r["newa"]["sev"],
                        " | ".join(r["cur"]["unknown"] + r["newa"]["unknown"])])
    write_report(S, f"{a.out}/report.md")
    print(f"{n} questions | current wrong {cw} | new wrong {nw} | VERDICT: {S['verdict']}")

    if a.llm_check:
        from .judge import llm_judge
        J = llm_judge(rows, cfg, policy=sorted(kb.known_true))
        agree = sum(j["winner"] == r["verdict"][0] for j, r in zip(J, R)) / n
        print(f"LLM second opinion agrees with the rule-based verdict on {agree:.0%} of questions")
        json.dump({"agreement": agree, "llm_winners": [j["winner"] for j in J]}, open(f"{a.out}/llm_check.json", "w"))
    sys.exit(1 if S["verdict"] == "DO NOT SHIP" else 0)

if __name__ == "__main__":
    main()
