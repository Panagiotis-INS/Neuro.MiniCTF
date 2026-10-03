# WEB01_CatCafe — *Purr-fect Beans*

> *"We have cats. No coffee yet. We are working on that."*

A deliberately vulnerable Flask web application themed around a cat cafe,
built for the **Neuro.MiniCTF** series. It chains three classic web
weaknesses into one short run — IDOR → cookie forgery → RCE — and ends
with three flags.

---

## 1. Setup

### 1.1 One-shot with Docker Compose (recommended)

```bash
cd WEB01_CatCafe
docker compose up -d --build
```

Then browse to **http://localhost:4000/**. Stop it with `docker compose down`.

### 1.2 With the Makefile

```bash
make up        # build + start in the background
make logs      # tail container logs
make shell     # drop into the running container
make solve     # smoke-test all three vulns end-to-end
make down      # stop and remove
make clean     # also drop the image + local dev artifacts
make help      # list every target
```

### 1.3 Plain `docker` (no compose)

```bash
docker build -t catcafe .
docker run --rm -p 4000:4000 --name catcafe catcafe
```

### 1.4 Run locally without Docker

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python init_db.py        # seed the sqlite DB
python app.py            # listens on :4000
```

### 1.5 Credentials seeded in the DB

| Username        | Password          | Role     |
|-----------------|-------------------|----------|
| `barista_bob`   | `espresso123`     | customer |
| `whiskers_fan`  | `meowmeow`        | customer |
| `alice`         | `alice1234`       | customer |
| `mr_mittens`    | `purrpurr`        | customer |
| `admin`         | `C4tC4f3Adm1n!`   | **admin** |

> The challenge is designed to be solved *without* the admin password —
> that's the whole point of the forgeable cookie.

---

## 2. Flags

Three flags live in the challenge. All are in the format `CTF{...}` and
leet-speak:

| # | Where                              | How to get it                                                                 |
|---|------------------------------------|-------------------------------------------------------------------------------|
| 1 | Inside an order's `note` field     | Register / log in, then abuse the IDOR on `/orders/<id>` to iterate ids.      |
| 2 | Rendered on `/admin`               | Forge the base64 session cookie with `isAdmin: true` and reload `/admin`.     |
| 3 | `/flag.txt` on the container FS    | Exploit the command injection in the admin ping tool.                         |

---

## 3. Intended solution

### Stage 1 — IDOR on `/orders/<id>`

1. Register a new user and log in.
2. Place one order; note that it's reachable at `/orders/<id>`.
3. Decrement/increment the `id` in the URL — the handler does **not**
   check that the current user owns the row. One of the seeded orders
   contains a `CTF{...}` flag in its note field.

### Stage 2 — Forge the session cookie

Inspect your `session` cookie. It is just base64-encoded JSON:

```
eyJ1c2VybmFtZSI6ImFsaWNlIiwiaXNBZG1pbiI6ZmFsc2V9
→ {"username":"alice","isAdmin":false}
```

There is no HMAC/signature. Change `isAdmin` to `true`, re-encode, drop
the cookie back into the browser, hit `/admin`. The page is rendered and
contains the second flag.

```bash
python3 -c 'import base64,json; print(base64.b64encode(json.dumps({"username":"alice","isAdmin":True},separators=(",",":")).encode()).decode())'
```

### Stage 3 — Command injection on `/admin`

The staff panel has a **smart-feeder / cat-cam health check**: the cafe
runs IoT treat dispensers (`feeder-lounge`, `feeder-counter`, …) and
cat-cams on its back-of-house LAN, and the admin can "ping" a device to
check it's online. The device hostname is interpolated straight into a
shell command:

```python
cmd = f"ping -c 1 -W 1 {device}"
subprocess.check_output(cmd, shell=True, ...)
```

Classic shell meta-character injection reads the final flag:

```
host=feeder-lounge; cat /flag.txt
```

---

## 4. OWASP Top 10 (2021) mapping

| Vulnerability in challenge             | OWASP category                                | CWE          |
|----------------------------------------|-----------------------------------------------|--------------|
| IDOR on `/orders/<id>`                 | **A01:2021 — Broken Access Control**          | CWE-639 / CWE-284 |
| `isAdmin` flag inside client cookie    | **A01:2021 — Broken Access Control** (privilege escalation via client-side trust) | CWE-602      |
| Unsigned base64-JSON session cookie    | **A02:2021 — Cryptographic Failures** (missing integrity / no HMAC) | CWE-345 / CWE-347 |
| Command injection in `/admin` IoT device health check | **A03:2021 — Injection** | CWE-77 / CWE-78 |
| Plaintext passwords in SQLite          | **A02:2021 — Cryptographic Failures**         | CWE-256 / CWE-257 |
| Weak / default admin password          | **A07:2021 — Identification and Authentication Failures** | CWE-521      |
| Vulnerable design (no auth-z checks on object references, trust in client-side flags) | **A04:2021 — Insecure Design**                | CWE-602 / CWE-840 |
| Debug-friendly, verbose shell errors returned to UI | **A09:2021 — Security Logging and Monitoring Failures** (indirect) | n/a         |

---

## 5. Layout

```
WEB01_CatCafe/
├── app.py              # Flask app (vulns live here)
├── init_db.py          # Seeds users + orders, embeds order flag
├── requirements.txt
├── Dockerfile
├── docker-compose.yml  # `docker compose up -d --build` to run
├── Makefile            # make up / down / logs / solve / clean / …
├── entrypoint.sh
├── flag.txt            # Copied to /flag.txt in the container
├── README.md
├── static/
│   └── style.css
└── templates/
    ├── base.html
    ├── index.html
    ├── menu.html
    ├── login.html
    ├── register.html
    ├── order_new.html
    ├── orders.html
    ├── order_detail.html
    ├── admin.html
    └── forbidden.html
```

---

## 6. Warning

This application is **intentionally insecure**. Do not expose it on the
public internet. Run it only inside an isolated lab / Docker network /
disposable VM.
