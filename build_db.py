"""Build pessimism.duckdb from data/ (clippings, cards, timeline), raw/substack/posts, raw/cases/*.jsonl,
raw/research/fears_right.jsonl. Rebuilds from scratch; every input stays on disk."""
import glob, json, os
import duckdb, pandas as pd

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pessimism.duckdb")
if os.path.exists(DB):
    os.remove(DB)
con = duckdb.connect(DB)

def jl(path):
    rows = []
    for f in glob.glob(path, recursive=True):
        for line in open(f):
            line = line.strip()
            if line:
                try:
                    r = json.loads(line); r["_file"] = f; rows.append(r)
                except json.JSONDecodeError:
                    print("bad line in", f)
    return rows

# evidence
clip = pd.DataFrame(json.load(open("data/clippings.json")))
card = pd.DataFrame(json.load(open("data/cards.json")))
timeline = pd.DataFrame(json.load(open("data/timeline.json")))
posts = pd.DataFrame([json.load(open(f)) for f in glob.glob("raw/substack/posts/*.json")])
for name, df in [("clipping", clip), ("card", card), ("timeline", timeline), ("post", posts)]:
    con.register("_d", df); con.execute(f"CREATE TABLE {name} AS SELECT * FROM _d"); con.unregister("_d")

# cases: archive extraction + fears-right research
rows = []
for r in jl("raw/cases/*.jsonl") + jl("raw/research/**/*.jsonl"):
    r["origin"] = "research" if "/research/" in r["_file"] else "archive"
    rows.append(r)
seen, cases, quotes, evidence, analogs = set(), [], [], [], []
for r in rows:
    cid = r.get("case_id")
    if not cid or cid in seen:
        continue
    seen.add(cid)
    cases.append({k: r.get(k) for k in ["case_id", "thing", "domain", "year", "claim", "claim_type", "warner", "incumbent_stake",
                                        "verdict", "what_happened", "years_to_verdict", "adoption", "resisters_later_users",
                                        "dismissed_by", "cost_of_error", "lesson", "confidence", "origin"]})
    for q in r.get("quotes") or []:
        if isinstance(q, dict) and q.get("text"):
            quotes.append({"case_id": cid, "text": q.get("text"), "speaker": q.get("speaker"), "year": q.get("year"),
                           "publication": q.get("publication"), "url": q.get("url")})
    for e in (r.get("evidence") or []) + (r.get("sources") or []):
        evidence.append({"case_id": cid, "ref": str(e)})
    for a in r.get("modern_analog") or []:
        analogs.append({"case_id": cid, "analog": str(a).strip()})

case = pd.DataFrame(cases)
case["year"] = pd.to_numeric(case["year"], errors="coerce").astype("Int64")
case["years_to_verdict"] = pd.to_numeric(case["years_to_verdict"], errors="coerce").astype("Int64")
for c in ["incumbent_stake", "resisters_later_users"]:
    case[c] = case[c].map(lambda v: v if isinstance(v, bool) else None).astype("boolean")
for name, df in [("case_", case), ("quote", pd.DataFrame(quotes)), ("case_evidence", pd.DataFrame(evidence)),
                 ("case_analog", pd.DataFrame(analogs))]:
    con.register("_d", df); con.execute(f"CREATE TABLE {name} AS SELECT * FROM _d"); con.unregister("_d")
con.execute("ALTER TABLE case_ RENAME TO cases")

con.execute("""
CREATE VIEW verdict_by AS
SELECT claim_type, warner, incumbent_stake, count(*) n,
  round(avg((verdict='fear_wrong')::int),2) AS share_wrong,
  round(avg((verdict='mixed')::int),2) AS share_mixed,
  round(avg((verdict='fear_right')::int),2) AS share_right
FROM cases GROUP BY CUBE (claim_type, warner, incumbent_stake);
CREATE VIEW analog_cases AS
SELECT a.analog, c.* FROM case_analog a JOIN cases c USING (case_id);
""")
for t in ["clipping", "card", "timeline", "post", "cases", "quote", "case_evidence", "case_analog"]:
    print(f"{t:14s}", con.execute(f"select count(*) from {t}").fetchone()[0])
print(con.sql("select origin, verdict, count(*) n from cases group by all order by all"))
