"""Load learnings/insights.json into pessimism.duckdb alongside the cases.

Each insight's numbers are stored with the SQL that produced them and recomputed on every load,
against demand.duckdb and outreach.duckdb attached read-only. A metric whose source DB is missing
is stored with value NULL and an error, never a stale number.
"""
import glob, json, os, datetime
import duckdb, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DBS = {"demand": os.path.expanduser("~/Desktop/workspace/demand-signals/demand.duckdb"),
       "outreach": os.path.expanduser("~/Desktop/workspace/outreach-ledger/outreach.duckdb")}

def run(con=None, learn_dir=None, dbs=None):
    own = con is None
    con = con or duckdb.connect(os.path.join(HERE, "pessimism.duckdb"))
    learn_dir = learn_dir or os.path.join(HERE, "learnings")
    dbs = DBS if dbs is None else dbs
    for alias, path in dbs.items():
        if os.path.exists(path):
            try:
                con.execute(f"ATTACH '{path}' AS {alias} (READ_ONLY)")
            except duckdb.Error as e:
                print("attach failed", alias, e)
    today = datetime.date.today()
    ins, met, link = [], [], []
    for f in sorted(glob.glob(os.path.join(learn_dir, "*.json"))):
        for i in json.load(open(f)):
            ins.append({k: i.get(k) for k in ["insight_id", "recorded_on", "kind", "status", "statement", "next_test"]})
            for m in i.get("metrics", []):
                val, err = None, None
                try:
                    row = con.execute(m["sql"]).fetchone()
                    if row is None:
                        err = "no rows"  # a filter that matches nothing (a renamed product, an empty sector) is not a number
                    else:
                        val = row[0]
                except duckdb.Error as e:
                    err = str(e).splitlines()[0]
                met.append({"insight_id": i["insight_id"], "name": m["name"], "db": m["db"], "sql": m["sql"],
                            "value": None if val is None else float(val), "computed_on": today, "error": err})
            for c in i.get("case_ids", []):
                link.append({"insight_id": i["insight_id"], "case_id": c})
    for t in ["insight", "insight_metric", "insight_case", "learning_doc"]:
        con.execute(f"DROP TABLE IF EXISTS {t}")
    for name, df in [("insight", pd.DataFrame(ins)), ("insight_metric", pd.DataFrame(met)), ("insight_case", pd.DataFrame(link))]:
        con.register("_d", df); con.execute(f"CREATE TABLE {name} AS SELECT * FROM _d"); con.unregister("_d")
    docs = [{"path": os.path.relpath(p, HERE), "text": open(p).read()} for p in glob.glob(os.path.join(HERE, "REFLECTION_*.md"))]
    con.register("_d", pd.DataFrame(docs)); con.execute("CREATE TABLE learning_doc AS SELECT * FROM _d"); con.unregister("_d")
    con.execute("""CREATE OR REPLACE VIEW insight_full AS
      SELECT i.insight_id, i.kind, i.status, i.statement, m.name AS metric, m.value, m.computed_on, m.error
      FROM insight i LEFT JOIN insight_metric m USING (insight_id)""")
    missing = con.execute("SELECT count(*) FROM insight_case WHERE case_id NOT IN (SELECT case_id FROM cases)").fetchone()[0]
    for alias in dbs:
        try: con.execute(f"DETACH {alias}")
        except duckdb.Error: pass
    print("insights", len(ins), "| metrics", len(met), "| errors", sum(1 for m in met if m["error"]), "| unlinked case ids", missing)
    if own:
        con.close()

if __name__ == "__main__":
    run()
