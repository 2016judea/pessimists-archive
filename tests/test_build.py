"""Build-step tests on fabricated inputs; pessimism.duckdb and the real raw/ files are never opened.
Run: .venv/bin/python -m pytest tests"""
import json, os, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import duckdb
import build_db, load_learnings


def write_jsonl(path, rows):
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def test_jl_reads_files_in_sorted_order_whatever_the_filesystem_says(tmp_path):
    # the same case_id sat in archive_0 (verdict mixed) and substack (fear_wrong); glob returned
    # archive_1, archive_3, archive_2, archive_0, substack on this Mac, so which verdict landed in the DB
    # depended on directory order
    for name in ["substack.jsonl", "archive_3.jsonl", "archive_0.jsonl", "archive_2.jsonl"]:
        write_jsonl(tmp_path / name, [{"case_id": "walkman", "verdict": name}])
    rows = build_db.jl(str(tmp_path / "*.jsonl"))
    assert [r["verdict"] for r in rows] == ["archive_0.jsonl", "archive_2.jsonl", "archive_3.jsonl", "substack.jsonl"]


def test_pick_cases_keeps_the_first_row_and_reports_a_disagreeing_duplicate():
    rows = [{"case_id": "walkman", "verdict": "mixed", "warner": "press", "_file": "a.jsonl", "quotes": [{"text": "q1"}]},
            {"case_id": "walkman", "verdict": "fear_wrong", "warner": "press", "_file": "b.jsonl", "quotes": [{"text": "q2"}]},
            {"case_id": "radio", "verdict": "fear_wrong", "_file": "a.jsonl"},
            {"case_id": "radio", "verdict": "fear_wrong", "_file": "b.jsonl"},
            {"thing": "no id", "verdict": "mixed"}]
    logged = []
    cases, quotes, evidence, analogs = build_db.pick_cases(rows, log=logged.append)
    assert [(c["case_id"], c["verdict"]) for c in cases] == [("walkman", "mixed"), ("radio", "fear_wrong")]
    assert [q["text"] for q in quotes] == ["q1"]            # the dropped duplicate's quotes do not leak in
    assert len(logged) == 1 and "walkman" in logged[0] and "fear_wrong" in logged[0]


def test_a_metric_whose_query_returns_no_row_is_stored_as_null_with_an_error(tmp_path):
    # before: fetchone()[0] on None raised TypeError and the whole build died on one empty filter
    (tmp_path / "learnings").mkdir()
    json.dump([{"insight_id": "i1", "recorded_on": "2026-10-17", "kind": "vein", "status": "testing", "statement": "s",
                "metrics": [{"name": "empty", "db": "pessimism", "sql": "select count(*) from cases where 1=0 group by verdict"},
                            {"name": "fine", "db": "pessimism", "sql": "select count(*) from cases"},
                            {"name": "broken", "db": "pessimism", "sql": "select nope from cases"}],
                "case_ids": ["c1", "ghost"]}], open(tmp_path / "learnings" / "x.json", "w"))
    con = duckdb.connect(":memory:")
    con.execute("CREATE TABLE cases (case_id TEXT, verdict TEXT)")
    con.execute("INSERT INTO cases VALUES ('c1', 'mixed')")
    load_learnings.run(con, learn_dir=str(tmp_path / "learnings"), dbs={})
    got = {r[0]: (r[1], r[2]) for r in con.execute("SELECT name, value, error FROM insight_metric").fetchall()}
    assert got["empty"] == (None, "no rows")
    assert got["fine"] == (1.0, None)
    assert got["broken"][0] is None and got["broken"][1]
    assert con.execute("SELECT count(*) FROM insight_case WHERE case_id NOT IN (SELECT case_id FROM cases)").fetchone()[0] == 1
