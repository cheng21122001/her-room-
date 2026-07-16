import csv
import io
import json
import math
import os
import sqlite3

from flask import Flask, g, render_template, request, redirect, url_for, abort, Response

from seed_data import CASES, GLOSSARY

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "her_room.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")

GLOSSARY_BY_ID = {entry["id"]: entry for entry in GLOSSARY}

SYMBOL_CHOICES = [
    ("tower", "塔楼"), ("envelope", "信件"), ("gun", "手枪"), ("road", "公路"),
    ("flame", "火焰"), ("tape", "录音带"), ("house", "房屋"), ("camera", "摄像机"),
    ("shovel", "铁锹"), ("poison", "毒药瓶"),
]

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


def counts_by(db, column):
    rows = db.execute(
        f"SELECT {column} AS label, COUNT(*) AS n FROM cases "
        f"WHERE {column} != '' GROUP BY {column} ORDER BY n DESC, label"
    ).fetchall()
    peak = max((r["n"] for r in rows), default=1)
    return [(r["label"], r["n"], round(r["n"] / peak * 100)) for r in rows]


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/overview")
def overview():
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
    span = db.execute("SELECT MIN(year_start), MAX(year_start) FROM cases").fetchone()
    n_regions = db.execute("SELECT COUNT(DISTINCT region) FROM cases").fetchone()[0]
    n_types = db.execute("SELECT COUNT(DISTINCT case_type) FROM cases").fetchone()[0]
    latest = db.execute(
        "SELECT id, archive_no, name, era, region, case_type, symbol, summary "
        "FROM cases ORDER BY archive_no DESC LIMIT 3"
    ).fetchall()
    return render_template(
        "overview.html",
        total=total,
        span=span,
        n_regions=n_regions,
        n_types=n_types,
        n_terms=len(GLOSSARY),
        latest=latest,
        by_era=counts_by(db, "era"),
        by_type=counts_by(db, "case_type"),
    )


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


@app.route("/network")
def network():
    db = get_db()
    cases = db.execute(
        "SELECT id, archive_no, name, region, case_type, terms, year_start "
        "FROM cases ORDER BY year_start"
    ).fetchall()

    # Circular layout computed server-side; nodes link to case pages.
    width, height, radius = 900, 640, 250
    cx, cy = width / 2, height / 2
    nodes = []
    for i, case in enumerate(cases):
        angle = 2 * math.pi * i / max(len(cases), 1) - math.pi / 2
        nodes.append({
            "id": case["id"],
            "archive_no": case["archive_no"],
            "name": case["name"],
            "x": cx + radius * math.cos(angle),
            "y": cy + radius * math.sin(angle),
            "align": "start" if math.cos(angle) > 0.3 else ("end" if math.cos(angle) < -0.3 else "middle"),
            "terms": set(json.loads(case["terms"] or "[]")),
            "region": case["region"],
            "case_type": case["case_type"],
        })

    # One edge per pair, strongest relation wins: type > region > shared term.
    edges = []
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            a, b = nodes[i], nodes[j]
            if a["case_type"] == b["case_type"]:
                kind = "type"
            elif a["region"] == b["region"]:
                kind = "region"
            elif a["terms"] & b["terms"]:
                kind = "term"
            else:
                continue
            edges.append({"x1": a["x"], "y1": a["y"], "x2": b["x"], "y2": b["y"], "kind": kind})

    return render_template(
        "network.html", nodes=nodes, edges=edges, width=width, height=height
    )


@app.route("/stats")
def stats():
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
    span = db.execute("SELECT MIN(year_start), MAX(year_start) FROM cases").fetchone()
    return render_template(
        "stats.html",
        total=total,
        span=span,
        by_era=counts_by(db, "era"),
        by_type=counts_by(db, "case_type"),
        by_region=counts_by(db, "region"),
        by_credibility=counts_by(db, "credibility"),
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


@app.route("/capture")
def capture():
    db = get_db()
    last = db.execute("SELECT MAX(archive_no) FROM cases").fetchone()[0] or "HR-000"
    next_no = f"HR-{int(last.split('-')[1]) + 1:03d}"
    return render_template(
        "capture.html",
        next_no=next_no,
        symbol_choices=SYMBOL_CHOICES,
        glossary=GLOSSARY,
    )


def all_cases_export(db):
    rows = db.execute("SELECT * FROM cases ORDER BY archive_no").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d.pop("id", None)
        d.pop("created_at", None)
        d["timeline"] = json.loads(d["timeline"] or "[]")
        d["terms"] = json.loads(d["terms"] or "[]")
        out.append(d)
    return out


@app.route("/export.json")
def export_json():
    data = {"cases": all_cases_export(get_db()), "glossary": GLOSSARY}
    return Response(
        json.dumps(data, ensure_ascii=False, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=her-room-export.json"},
    )


@app.route("/export.csv")
def export_csv():
    cases = all_cases_export(get_db())
    buf = io.StringIO()
    if cases:
        writer = csv.DictWriter(buf, fieldnames=list(cases[0].keys()))
        writer.writeheader()
        for c in cases:
            row = dict(c)
            row["timeline"] = json.dumps(row["timeline"], ensure_ascii=False)
            row["terms"] = json.dumps(row["terms"], ensure_ascii=False)
            writer.writerow(row)
    return Response(
        "﻿" + buf.getvalue(),  # BOM so Excel opens UTF-8 correctly
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=her-room-export.csv"},
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
