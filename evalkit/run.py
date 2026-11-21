"""python -m evalkit.run --data data/questions.csv   (exit code 1 on DO NOT SHIP, so CI can block the merge)
Outputs in results/: report.md, verdicts.csv (id,better), per_question.csv, summary.json"""
import argparse, csv, json, os, sys
from .data import load
from .pipeline import evaluate
from .report import write_report

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/questions.csv")
    ap.add_argument("--kb", default="data/policy_kb.json")
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--out", default="results")
    ap.add_argument("--llm-check", action="store_true", help="optional LLM second opinion (needs ANTHROPIC_API_KEY)")
    a = ap.parse_args()
    cfg = json.load(open(a.config))
    rows = load(a.data)
    S, R, kb = evaluate(rows, a.kb, cfg)
    n, cw, nw = S["n"], S["accuracy"]["cur_wrong"], S["accuracy"]["new_wrong"]
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
