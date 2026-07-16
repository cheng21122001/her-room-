import hmac
import os
import sqlite3

from flask import Flask, g, render_template, request, redirect, url_for, abort, Response

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "her_room.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")

SITE_USER = os.environ.get("SITE_USER")
SITE_PASSWORD = os.environ.get("SITE_PASSWORD")

# Anyone can browse and submit new cases; only editing/deleting existing
# entries requires the site password, so public contributions can't be
# vandalized or wiped by other visitors.
AUTH_REQUIRED_ENDPOINTS = {"case_edit", "case_delete"}

app = Flask(__name__)


@app.before_request
def require_auth():
    # Auth is only enforced when SITE_USER/SITE_PASSWORD are set (e.g. in production).
    # Local development without those env vars stays open.
    if not SITE_USER or not SITE_PASSWORD:
        return
    if request.endpoint not in AUTH_REQUIRED_ENDPOINTS:
        return
    auth = request.authorization
    valid = (
        auth
        and hmac.compare_digest(auth.username, SITE_USER)
        and hmac.compare_digest(auth.password, SITE_PASSWORD)
    )
    if not valid:
        return Response(
            "Authentication required.",
            401,
            {"WWW-Authenticate": 'Basic realm="Her Room"'},
        )


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    is_new = not os.path.exists(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    if is_new:
        seed(conn)
    conn.close()


def seed(conn):
    from seed_data import CASES

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


CASE_FIELDS = [
    "name", "aliases", "period", "era", "location", "case_type", "silhouette",
    "summary", "case_details", "psychological_profile", "sources",
]


def form_to_case(form):
    return {
        "name": form.get("name", "").strip(),
        "aliases": form.get("aliases", "").strip(),
        "period": form.get("period", "").strip(),
        "era": form.get("era", "").strip(),
        "location": form.get("location", "").strip(),
        "case_type": form.get("case_type", "").strip(),
        "silhouette": int(form.get("silhouette") or 0) % 4,
        "summary": form.get("summary", "").strip(),
        "case_details": form.get("case_details", "").strip(),
        "psychological_profile": form.get("psychological_profile", "").strip(),
        "sources": form.get("sources", "").strip(),
    }


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


@app.route("/case/new", methods=["GET", "POST"])
def case_new():
    if request.method == "POST":
        data = form_to_case(request.form)
        db = get_db()
        cur = db.execute(
            """
            INSERT INTO cases
                (name, aliases, period, era, location, case_type, silhouette,
                 summary, case_details, psychological_profile, sources)
            VALUES
                (:name, :aliases, :period, :era, :location, :case_type, :silhouette,
                 :summary, :case_details, :psychological_profile, :sources)
            """,
            data,
        )
        db.commit()
        return redirect(url_for("case_detail", case_id=cur.lastrowid))
    return render_template("case_form.html", case=None, action=url_for("case_new"))


@app.route("/case/<int:case_id>/edit", methods=["GET", "POST"])
def case_edit(case_id):
    db = get_db()
    case = db.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    if case is None:
        abort(404)
    if request.method == "POST":
        data = form_to_case(request.form)
        data["id"] = case_id
        db.execute(
            """
            UPDATE cases SET
                name=:name, aliases=:aliases, period=:period, era=:era,
                location=:location, case_type=:case_type, silhouette=:silhouette,
                summary=:summary, case_details=:case_details,
                psychological_profile=:psychological_profile, sources=:sources
            WHERE id=:id
            """,
            data,
        )
        db.commit()
        return redirect(url_for("case_detail", case_id=case_id))
    return render_template("case_form.html", case=case, action=url_for("case_edit", case_id=case_id))


@app.route("/case/<int:case_id>/delete", methods=["POST"])
def case_delete(case_id):
    db = get_db()
    db.execute("DELETE FROM cases WHERE id = ?", (case_id,))
    db.commit()
    return redirect(url_for("index"))


init_db()

if __name__ == "__main__":
    app.run(debug=True, port=5001)
