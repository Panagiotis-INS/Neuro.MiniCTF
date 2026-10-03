"""
Purr-fect Beans — Cat Cafe
A deliberately vulnerable web application for CTF training.

Vulnerabilities (by design, do NOT fix):
    * IDOR on /orders/<id>
    * Forgeable session cookie (base64 JSON, no signature) with isAdmin flag
    * Command injection on /admin (host ping diagnostics)

Author:  Neuro.MiniCTF — WEB01_CatCafe
"""

import base64
import json
import os
import sqlite3
import subprocess
from functools import wraps

from flask import (
    Flask,
    g,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("CATCAFE_DB", os.path.join(APP_ROOT, "catcafe.db"))

app = Flask(__name__)


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


# ---------------------------------------------------------------------------
# "Session" — intentionally broken (base64 JSON, no signature)
# ---------------------------------------------------------------------------
COOKIE_NAME = "session"


def make_session_cookie(username: str, is_admin: bool) -> str:
    payload = {"username": username, "isAdmin": bool(is_admin)}
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return base64.b64encode(raw).decode()


def read_session():
    raw = request.cookies.get(COOKIE_NAME)
    if not raw:
        return None
    try:
        data = json.loads(base64.b64decode(raw).decode())
        if "username" in data:
            return {
                "username": str(data["username"]),
                "isAdmin": bool(data.get("isAdmin", False)),
            }
    except Exception:
        return None
    return None


def login_required(view):
    @wraps(view)
    def wrapper(*a, **kw):
        if not read_session():
            return redirect(url_for("login"))
        return view(*a, **kw)
    return wrapper


def admin_required(view):
    @wraps(view)
    def wrapper(*a, **kw):
        sess = read_session()
        if not sess or not sess.get("isAdmin"):
            return render_template("forbidden.html"), 403
        return view(*a, **kw)
    return wrapper


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    sess = read_session()
    return render_template("index.html", session=sess)


@app.route("/menu")
def menu():
    sess = read_session()
    items = [
        {"name": "Tabby Tuna Bowl",   "price": "€6.00", "desc": "Fresh tuna, loved by Mr. Whiskers himself."},
        {"name": "Siamese Salmon",    "price": "€7.50", "desc": "Pink, flaky, served on a napkin shaped like a fish."},
        {"name": "Maine Coon Milk",   "price": "€3.00", "desc": "Warm oat milk. Humans only — the cats judge you."},
        {"name": "Persian Pastry",    "price": "€4.00", "desc": "A croissant that may or may not have been napped on."},
        {"name": "Sphynx Sparkling",  "price": "€3.50", "desc": "Fizzy water. No fur. Guaranteed."},
    ]
    return render_template("menu.html", session=sess, items=items)


@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        if not username or not password:
            error = "Username and password required."
        else:
            db = get_db()
            try:
                db.execute(
                    "INSERT INTO users (username, password, is_admin) VALUES (?, ?, 0)",
                    (username, password),
                )
                db.commit()
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                error = "That username is already curled up on the sofa."
    return render_template("register.html", error=error)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        db = get_db()
        row = db.execute(
            "SELECT username, password, is_admin FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if row and row["password"] == password:
            resp = make_response(redirect(url_for("orders_mine")))
            # NOTE: no signature, no HMAC, no server-side session.
            # The cookie is just base64(JSON({username, isAdmin})).
            resp.set_cookie(
                COOKIE_NAME,
                make_session_cookie(row["username"], bool(row["is_admin"])),
                httponly=False,
            )
            return resp
        error = "Hiss. Wrong credentials."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    resp = make_response(redirect(url_for("index")))
    resp.delete_cookie(COOKIE_NAME)
    return resp


@app.route("/order", methods=["GET", "POST"])
@login_required
def order_new():
    sess = read_session()
    if request.method == "POST":
        item = (request.form.get("item") or "").strip()
        note = (request.form.get("note") or "").strip()
        if item:
            db = get_db()
            cur = db.execute(
                "INSERT INTO orders (username, item, note) VALUES (?, ?, ?)",
                (sess["username"], item, note),
            )
            db.commit()
            return redirect(url_for("order_detail", order_id=cur.lastrowid))
    return render_template("order_new.html", session=sess)


@app.route("/orders")
@login_required
def orders_mine():
    sess = read_session()
    db = get_db()
    rows = db.execute(
        "SELECT id, item, note FROM orders WHERE username = ? ORDER BY id DESC",
        (sess["username"],),
    ).fetchall()
    return render_template("orders.html", session=sess, orders=rows)


@app.route("/orders/<int:order_id>")
@login_required
def order_detail(order_id):
    """IDOR: any authenticated user can read any order by id."""
    sess = read_session()
    db = get_db()
    row = db.execute(
        "SELECT id, username, item, note FROM orders WHERE id = ?",
        (order_id,),
    ).fetchone()
    if not row:
        return render_template("order_detail.html", session=sess, order=None), 404
    return render_template("order_detail.html", session=sess, order=row)


# ---------------------------------------------------------------------------
# Admin — guarded by the forgeable isAdmin cookie.
#
# The cafe runs a bunch of IoT devices on the back-of-house LAN: automatic
# treat dispensers in each lounge, cat-cams above the napping shelves, a
# smart water fountain, etc. When a cat parent complains that "the feeder
# hasn't gone off", the manager uses this panel to ping the device and
# confirm it's still on the network.
#
# Vulnerability: the device hostname is interpolated straight into a shell
# command — classic shell-metacharacter injection.
# ---------------------------------------------------------------------------
ADMIN_FLAG = "CTF{n0_s1gn4tur3_m34ns_n0_s3cur1ty}"

# Known devices on the cafe LAN — shown to the admin as a hint / autocomplete.
CAFE_DEVICES = [
    {"name": "feeder-lounge",  "kind": "Treat dispenser",   "where": "Main lounge"},
    {"name": "feeder-counter", "kind": "Treat dispenser",   "where": "Behind the counter"},
    {"name": "feeder-window",  "kind": "Treat dispenser",   "where": "Window shelf"},
    {"name": "cam-nap-shelf",  "kind": "Cat-cam",           "where": "Napping shelves"},
    {"name": "cam-litter",     "kind": "Cat-cam",           "where": "Litter corner"},
    {"name": "fountain-01",    "kind": "Smart water bowl",  "where": "Entrance"},
]


@app.route("/admin", methods=["GET", "POST"])
@admin_required
def admin():
    sess = read_session()
    output = None
    device = ""
    if request.method == "POST":
        # The form field is still called `host` on the wire — it's the
        # hostname of the IoT device on the cafe LAN.
        device = request.form.get("host", "")
        # Vulnerable: raw string interpolation into shell.
        # In production this just confirms the smart feeder is online.
        cmd = f"ping -c 1 -W 1 {device}"
        try:
            output = subprocess.check_output(
                cmd, shell=True, stderr=subprocess.STDOUT, timeout=10
            ).decode(errors="replace")
        except subprocess.CalledProcessError as e:
            output = e.output.decode(errors="replace")
        except subprocess.TimeoutExpired:
            output = "[!] device did not respond in time"
    return render_template(
        "admin.html",
        session=sess,
        output=output,
        host=device,
        devices=CAFE_DEVICES,
        admin_flag=ADMIN_FLAG,
    )


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=4000, debug=False)
