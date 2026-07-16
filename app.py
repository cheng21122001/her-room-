import os
import sqlite3

from flask import Flask, g, render_template, request, abort

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "her_room.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")

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
    from seed_data import CASES

    conn = sqlite3.connect(DB_PATH)
    conn.execute("DROP TABLE IF EXISTS cases")
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.executemany(
        """
        INSERT INTO cases
            (name, aliases, period, era, location, case_type, silhouette,
             summary, case_details, psychological_profile, sources)
        VALUES
            (:name, :aliases, :period, :era, :location, :case_type, :silhouette,
             :summary, :case_details, :psychological_profile, :sources)
        """,
        CASES,
    )
    conn.commit()
    conn.close()


@app.route("/")
def index():
    db = get_db()
    q = request.args.get("q", "").strip()
    era = request.args.get("era", "").strip()
    case_type = request.args.get("case_type", "").strip()

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
    sql += " ORDER BY name COLLATE NOCASE"

    cases = db.execute(sql, params).fetchall()
    eras = [r["era"] for r in db.execute(
        "SELECT DISTINCT era FROM cases WHERE era != '' ORDER BY era"
    ).fetchall()]
    case_types = [r["case_type"] for r in db.execute(
        "SELECT DISTINCT case_type FROM cases WHERE case_type != '' ORDER BY case_type"
    ).fetchall()]

    return render_template(
        "index.html",
        cases=cases,
        q=q,
        era=era,
        case_type=case_type,
        eras=eras,
        case_types=case_types,
        total=len(cases),
    )


@app.route("/case/<int:case_id>")
def case_detail(case_id):
    db = get_db()
    case = db.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    if case is None:
        abort(404)
    return render_template("case_detail.html", case=case)


init_db()

if __name__ == "__main__":
    app.run(debug=True, port=5001)
