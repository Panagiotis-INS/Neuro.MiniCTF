"""
Initialise the Cat Cafe SQLite database with:
  * a users table (regular customers + one admin)
  * an orders table with a handful of pre-created orders
  * one of those orders carries the "orders" CTF flag in its note field

Idempotent: drops and recreates the DB on every run.
"""

import os
import sqlite3

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("CATCAFE_DB", os.path.join(APP_ROOT, "catcafe.db"))

# Flag hidden inside one of the seeded orders (leet speak)
ORDERS_FLAG = "CTF{1d0r_l3ts_y0u_r3ad_0th3r_c4ts_0rd3rs}"


SCHEMA = """
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS orders;

CREATE TABLE users (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    is_admin INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE orders (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    username  TEXT NOT NULL,
    item      TEXT NOT NULL,
    note      TEXT
);
"""

USERS = [
    # (username, password, is_admin)
    ("barista_bob",  "espresso123",   0),
    ("whiskers_fan", "meowmeow",      0),
    ("alice",        "alice1234",     0),
    ("mr_mittens",   "purrpurr",      0),
    ("admin",        "C4tC4f3Adm1n!", 1),
]

ORDERS = [
    # (username, item, note)
    ("barista_bob",  "Tabby Tuna Bowl",  "Extra tuna, hold the judgement."),
    ("whiskers_fan", "Siamese Salmon",   "Please let a cat sniff it first."),
    ("alice",        "Maine Coon Milk",  "Oat, warm, in the pink mug."),
    # <-- IDOR flag lives here, in mr_mittens's "private" order
    ("mr_mittens",   "Persian Pastry",   f"VIP note: {ORDERS_FLAG}"),
    ("barista_bob",  "Sphynx Sparkling", "No ice."),
    ("alice",        "Tabby Tuna Bowl",  "To go, in a paper bag shaped like a fish."),
    ("whiskers_fan", "Persian Pastry",   "Birthday treat for Mittens."),
]


def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    con = sqlite3.connect(DB_PATH)
    con.executescript(SCHEMA)
    con.executemany(
        "INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)",
        USERS,
    )
    con.executemany(
        "INSERT INTO orders (username, item, note) VALUES (?, ?, ?)",
        ORDERS,
    )
    con.commit()
    con.close()
    print(f"[+] Database initialised at {DB_PATH}")
    print(f"[+] {len(USERS)} users, {len(ORDERS)} orders inserted")


if __name__ == "__main__":
    main()
