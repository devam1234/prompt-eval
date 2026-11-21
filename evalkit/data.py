"""Load the question set (.csv / .jsonl / .json). Columns: id, topic (optional), question, answer_current, answer_new."""
import csv, json

ALIASES = {
    "id": ["id", "qid", "question_id"],
    "topic": ["topic", "category", "segment"],
    "question": ["question", "customer_question", "query"],
    "old": ["answer_current", "current", "old", "answer_old", "baseline"],
    "new": ["answer_new", "new", "candidate"],
}

def _pick(row, key, required=True):
    for a in ALIASES[key]:
        if a in row and row[a] is not None:
            return str(row[a])
    if required:
        raise KeyError(f"Missing column for '{key}'. Tried {ALIASES[key]}; found {list(row)}")
    return "unknown"

def load(path):
    if path.endswith(".jsonl"):
        raw = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    elif path.endswith(".json"):
        raw = json.load(open(path, encoding="utf-8"))
    else:
        raw = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    return [{"id": _pick(r, "id") if any(a in r for a in ALIASES["id"]) else str(i),
             "topic": _pick(r, "topic", False), "question": _pick(r, "question").strip(),
             "old": _pick(r, "old").strip(), "new": _pick(r, "new").strip()} for i, r in enumerate(raw)]
