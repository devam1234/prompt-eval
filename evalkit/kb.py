"""Policy knowledge base + sentence classifier.
Every answer is split into sentences; each is FILLER (stock politeness), FALSE (known to contradict policy),
TRUE (anything else seen in the KB's known-true list) or UNKNOWN (never seen: needs human/LLM review)."""
import json, re

SEV_RANK = {"none": 0, "medium": 1, "high": 2, "critical": 3}

def split_sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]

class KB:
    def __init__(self, path, known_true=()):
        d = json.load(open(path, encoding="utf-8"))
        self.filler = set(d["filler"])
        self.false = {c["text"]: c for c in d["false_claims"]}
        self.required = d.get("required_when", [])
        self.known_true = set(known_true)

    def with_known_true(self, rows):
        """Everything in the data that is neither filler nor a known-false claim is treated as true policy."""
        for r in rows:
            for k in ("old", "new"):
                for s in split_sentences(r[k]):
                    if s not in self.filler and s not in self.false:
                        self.known_true.add(s)
        return self

    def classify(self, s):
        if s in self.filler: return "filler"
        if s in self.false: return "false"
        if s in self.known_true: return "true"
        return "unknown"

    def analyse(self, question, answer, ignore_false=()):
        """Returns facts about one answer. ignore_false: claim texts to treat as unknown (sensitivity runs)."""
        out = {"true": 0, "false": [], "unknown": [], "filler_words": 0, "words": len(answer.split()), "missing": [], "sentences": []}
        for s in split_sentences(answer):
            c = self.classify(s)
            if c == "false" and s in ignore_false: c = "unknown_ignored"
            item = {"t": s, "k": c}
            if c == "false": item.update(sev=self.false[s]["severity"], why=self.false[s]["why"])
            out["sentences"].append(item)
            if c == "true": out["true"] += 1
            elif c == "false": out["false"].append(self.false[s])
            elif c == "unknown": out["unknown"].append(s)
            elif c == "filler": out["filler_words"] += len(s.split())
        for rule in self.required:
            m = re.search(rule["question_regex"], question)
            if m and int(m.group(1)) >= rule["min_value"] and rule["must_contain"] not in answer:
                out["missing"].append(rule["why"])
        out["sev"] = max([SEV_RANK[c["severity"]] for c in out["false"]] + ([1] if out["missing"] else []) + [0])
        out["wrong"] = int(bool(out["false"]) or bool(out["missing"]))
        return out
