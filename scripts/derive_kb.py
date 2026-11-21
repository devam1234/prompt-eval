"""Lists candidate policy statements from the data so a human can confirm data/policy_kb.json.
 - filler : sentences that appear only in the new version, >=30 times (stock openers/closers)
 - suspects: sentences that appear <=6 times (minority claims) -> candidates for false_claims
 Usage: python scripts/derive_kb.py data/questions.csv"""
import collections, csv, re, sys
rows = list(csv.DictReader(open(sys.argv[1], encoding="utf-8")))
split = lambda t: [s.strip() for s in re.split(r"(?<=[.!?])\s+", t) if s.strip()]
cur = collections.Counter(s for r in rows for s in split(r["answer_current"]))
new = collections.Counter(s for r in rows for s in split(r["answer_new"]))
print("== FILLER candidates")
for s, n in new.most_common():
    if n >= 30 and cur[s] == 0: print(f"{n:3d}  {s}")
print("\n== SUSPECT minority claims (count<=6) -- confirm or reject each")
tot = cur + new
for s, n in sorted(tot.items(), key=lambda x: x[1]):
    if n <= 6 and new[s] + cur[s] == n: print(f"{n:3d} cur={cur[s]} new={new[s]}  {s}")
