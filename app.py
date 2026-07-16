import json
import os
import random
import sqlite3

from flask import Flask, g, render_template, request, redirect, url_for, abort

from seed_data import CASES, GLOSSARY

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "her_room.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")

GLOSSARY_BY_ID = {entry["id"]: entry for entry in GLOSSARY}

app = Flask(__name__)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    # The repo (seed_data.py) is the single source of truth: the site is
    # read-only and the database is rebuilt from seed data on every start,
    # so content updates ship as git commits.
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DROP TABLE IF EXISTS cases")
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    rows = [
        {**case,
         "timeline": json.dumps(case["timeline"], ensure_ascii=False),
         "terms": json.dumps(case["terms"], ensure_ascii=False)}
        for case in CASES
    ]
    conn.executemany(
        """
        INSERT INTO cases
            (archive_no, name, aliases, period, era, region, year_start,
             location, case_type, credibility, symbol, summary, case_details,
             timeline, psychological_profile, terms, sources)
        VALUES
            (:archive_no, :name, :aliases, :period, :era, :region, :year_start,
             :location, :case_type, :credibility, :symbol, :summary, :case_details,
             :timeline, :psychological_profile, :terms, :sources)
        """,
        rows,
    )
    conn.commit()
    conn.close()


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/archive")
def index():
    db = get_db()
    q = request.args.get("q", "").strip()
    era = request.args.get("era", "").strip()
    case_type = request.args.get("case_type", "").strip()
    region = request.args.get("region", "").strip()

    sql = "SELECT * FROM cases WHERE 1=1"
    params = []
    if q:
        sql += " AND (name LIKE ? OR aliases LIKE ? OR summary LIKE ? OR case_details LIKE ?)"
        like = f"%{q}%"
        params += [like, like, like, like]
    if era:
        sql += " AND era = ?"
        params.append(era)
    if case_type:
        sql += " AND case_type = ?"
        params.append(case_type)
    if region:
        sql += " AND region = ?"
        params.append(region)
    sql += " ORDER BY archive_no"

    cases = db.execute(sql, params).fetchall()

    def distinct(column):
        return [r[column] for r in db.execute(
            f"SELECT DISTINCT {column} FROM cases WHERE {column} != '' ORDER BY {column}"
        ).fetchall()]

    return render_template(
        "index.html",
        cases=cases,
        q=q,
        era=era,
        case_type=case_type,
        region=region,
        eras=distinct("era"),
        case_types=distinct("case_type"),
        regions=distinct("region"),
        total=len(cases),
    )


@app.route("/case/<int:case_id>")
def case_detail(case_id):
    db = get_db()
    case = db.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    if case is None:
        abort(404)

    timeline = json.loads(case["timeline"] or "[]")
    terms = [GLOSSARY_BY_ID[t] for t in json.loads(case["terms"] or "[]")
             if t in GLOSSARY_BY_ID]

    # Closest cases by year among those sharing a type or region.
    related = db.execute(
        """
        SELECT id, archive_no, name, era, case_type, symbol FROM cases
        WHERE id != ? AND (case_type = ? OR region = ?)
        ORDER BY ABS(year_start - ?) LIMIT 4
        """,
        (case_id, case["case_type"], case["region"], case["year_start"]),
    ).fetchall()

    return render_template(
        "case_detail.html",
        case=case,
        timeline=timeline,
        terms=terms,
        related=related,
    )


@app.route("/timeline")
def timeline():
    db = get_db()
    cases = db.execute(
        "SELECT id, archive_no, name, period, era, region, case_type, symbol, "
        "year_start, summary FROM cases ORDER BY year_start"
    ).fetchall()
    return render_template("timeline.html", cases=cases)


@app.route("/stats")
def stats():
    db = get_db()

    def counts(column):
        rows = db.execute(
            f"SELECT {column} AS label, COUNT(*) AS n FROM cases "
            f"WHERE {column} != '' GROUP BY {column} ORDER BY n DESC, label"
        ).fetchall()
        peak = max((r["n"] for r in rows), default=1)
        return [(r["label"], r["n"], round(r["n"] / peak * 100)) for r in rows]

    total = db.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
    span = db.execute("SELECT MIN(year_start), MAX(year_start) FROM cases").fetchone()

    return render_template(
        "stats.html",
        total=total,
        span=span,
        by_era=counts("era"),
        by_type=counts("case_type"),
        by_region=counts("region"),
        by_credibility=counts("credibility"),
    )


@app.route("/glossary")
def glossary():
    db = get_db()
    cases = db.execute(
        "SELECT id, archive_no, name, terms FROM cases ORDER BY archive_no"
    ).fetchall()
    related_cases = {}
    for case in cases:
        for term_id in json.loads(case["terms"] or "[]"):
            related_cases.setdefault(term_id, []).append(case)
    return render_template(
        "glossary.html", glossary=GLOSSARY, related_cases=related_cases
    )


@app.route("/random")
def random_case():
    db = get_db()
    row = db.execute("SELECT id FROM cases ORDER BY RANDOM() LIMIT 1").fetchone()
    if row is None:
        return redirect(url_for("index"))
    return redirect(url_for("case_detail", case_id=row["id"]))


init_db()

if __name__ == "__main__":
    app.run(debug=True, port=5001)
