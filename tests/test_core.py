import csv, json, subprocess, sys
from evalkit.data import load
from evalkit.kb import KB, split_sentences
from evalkit.score import verdict
from evalkit.stats import bootstrap_mean_ci, sign_test_p

ROWS = load("data/questions.csv")
KBX = KB("data/policy_kb.json").with_known_true(ROWS)

def test_stats():
    assert sign_test_p(10, 0) < 0.01 and sign_test_p(5, 5) == 1.0
    assert bootstrap_mean_ci([1.0] * 50 + [0.5] * 50, 2000)[1] > 0

def test_all_300_rows_load_and_no_unknown_sentences():
    assert len(ROWS) == 300
    assert all(not KBX.analyse(r["question"], r[k])["unknown"] for r in ROWS for k in ("old", "new"))

def test_every_false_claim_exists_in_data():   # guards against a typo silently disabling a check
    seen = {s for r in ROWS for k in ("old", "new") for s in split_sentences(r[k])}
    assert all(t in seen for t in KBX.false)

def test_filler_never_wins():
    q = "Is it too late to cancel my order?"
    cur = KBX.analyse(q, "An order can be cancelled only before it ships.")
    new = KBX.analyse(q, "Great question! An order can be cancelled only before it ships. I hope that helps!")
    assert verdict(cur, new)[0] == "tie" and new["filler_words"] > 0

def test_false_claim_loses_even_if_friendlier():
    q = "Can I return my Lumora Hub? I bought it 15 days ago."
    cur = KBX.analyse(q, "You can return an item for a refund within 30 days of delivery.")
    new = KBX.analyse(q, "Great question! You can return an item for a full refund at any time, with no deadline. Start the return from Orders in your account, print the label, and send the item back in its packaging.")
    assert verdict(cur, new)[0] == "current"

def test_stalled_tracking_requires_escalation():
    q = "My tracking has not updated for 27 days. Is my order lost?"
    short = KBX.analyse(q, "Tracking can pause for a few days between scans, and standard delivery takes 3 to 5 business days.")
    assert short["missing"]

def test_end_to_end_blocks_on_real_data(tmp_path):
    p = subprocess.run([sys.executable, "-m", "evalkit.run", "--out", str(tmp_path)], capture_output=True, text=True)
    assert p.returncode == 1 and "DO NOT SHIP" in p.stdout
    v = list(csv.DictReader(open(tmp_path / "verdicts.csv")))
    assert len(v) == 300 and {x["better"] for x in v} <= {"current", "new", "tie"}
