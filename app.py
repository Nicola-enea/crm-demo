
from flask import Flask, render_template, request, redirect, session, jsonify, flash, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime, timedelta
import random
import calendar

app = Flask(__name__)
app.secret_key = "supersecretkey"

DB_PATH = "database.db"

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            phone TEXT,
            status TEXT,
            priority TEXT,
            source TEXT,
            value REAL,
            notes TEXT,
            created_at TEXT,
            last_contact TEXT,
            next_followup TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            date TEXT,
            time TEXT,
            service TEXT,
            amount REAL,
            status TEXT,
            notes TEXT,
            created_at TEXT,
            FOREIGN KEY(client_id) REFERENCES clients(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            due_date TEXT,
            priority TEXT,
            done INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()

def seed():
    conn = db()
    c = conn.cursor()

    # demo user
    c.execute("SELECT 1 FROM users WHERE username=?", ("demo1",))
    if not c.fetchone():
        c.execute("INSERT INTO users (username,password) VALUES (?,?)",
                  ("demo1", generate_password_hash("demo123")))

    # clients demo
    c.execute("SELECT COUNT(*) AS n FROM clients")
    if c.fetchone()["n"] == 0:
        statuses = ["Lead", "Attivo", "Perso"]
        priorities = ["Alta", "Media", "Bassa"]
        sources = ["Sito", "Referral", "Ads", "Email"]
        now = datetime.now()
        for i in range(1, 21):
            st = random.choice(statuses)
            pr = random.choice(priorities)
            src = random.choice(sources)
            created = (now - timedelta(days=random.randint(0, 120))).strftime("%Y-%m-%d %H:%M:%S")
            lastc = (now - timedelta(days=random.randint(0, 40))).strftime("%Y-%m-%d")
            nextf = (now + timedelta(days=random.randint(1, 40))).strftime("%Y-%m-%d")
            val = float(random.randint(300, 6000))
            c.execute("""
                INSERT INTO clients (name,email,phone,status,priority,source,value,notes,created_at,last_contact,next_followup)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            (f"Cliente {i}", f"cliente{i}@mail.com", f"333000{i:03d}", st, pr, src, val,
             "Nota demo: cliente di esempio.", created, lastc, nextf))

    # bookings demo
    c.execute("SELECT COUNT(*) AS n FROM bookings")
    if c.fetchone()["n"] == 0:
        c.execute("SELECT id FROM clients ORDER BY id LIMIT 20")
        client_ids = [r["id"] for r in c.fetchall()]
        now = datetime.now()
        services = ["Consulenza Strategica", "Onboarding", "Revisione Report", "Meeting", "Supporto"]
        bstatuses = ["Confermata", "In attesa", "Annullata"]
        for i in range(1, 21):
            cid = random.choice(client_ids)
            dt = (now + timedelta(days=random.randint(-10, 30))).strftime("%Y-%m-%d")
            tm = f"{random.randint(9, 18):02d}:{random.choice([0, 15, 30, 45]):02d}"
            srv = random.choice(services)
            amt = float(random.randint(50, 900))
            st = random.choice(bstatuses)
            c.execute("""
                INSERT INTO bookings (client_id,date,time,service,amount,status,notes,created_at)
                VALUES (?,?,?,?,?,?,?,?)
            """,
            (cid, dt, tm, srv, amt, st, "Nota demo prenotazione.", now.strftime("%Y-%m-%d %H:%M:%S")))

    # tasks demo
    c.execute("SELECT COUNT(*) AS n FROM tasks")
    if c.fetchone()["n"] == 0:
        now = datetime.now()
        tprio = ["Alta", "Media", "Bassa"]
        for i in range(1, 11):
            due = (now + timedelta(days=i)).strftime("%Y-%m-%d")
            c.execute("INSERT INTO tasks (title,due_date,priority,done,created_at) VALUES (?,?,?,?,?)",
                      (f"Task demo {i}", due, random.choice(tprio), 0, now.strftime("%Y-%m-%d %H:%M:%S")))

    conn.commit()
    conn.close()

init_db()
seed()

def require_login():
    return "user" in session

@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username","").strip()
        password = request.form.get("password","")
        conn = db()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=?", (username,))
        u = c.fetchone()
        conn.close()
        if u and check_password_hash(u["password"], password):
            session["user"] = username
            session.setdefault("theme", "light")
            return redirect(url_for("dashboard"))
        flash("Credenziali non valide.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/theme/toggle", methods=["POST"])
def theme_toggle():
    if not require_login():
        return redirect(url_for("login"))
    session["theme"] = "dark" if session.get("theme","light") == "light" else "light"
    return redirect(request.referrer or url_for("dashboard"))

# ---------------- DASHBOARD ----------------

@app.route("/dashboard")
def dashboard():
    if not require_login():
        return redirect(url_for("login"))

    conn = db()
    c = conn.cursor()

    c.execute("SELECT COUNT(*) AS n FROM clients")
    totale = c.fetchone()["n"]

    c.execute("SELECT COUNT(*) AS n FROM clients WHERE status='Attivo'")
    attivi = c.fetchone()["n"]

    c.execute("SELECT SUM(value) AS s FROM clients")
    revenue = float(c.fetchone()["s"] or 0)

    c.execute("SELECT * FROM bookings ORDER BY date, time LIMIT 6")
    prenotazioni = c.fetchall()

    c.execute("SELECT * FROM tasks ORDER BY done ASC, due_date ASC LIMIT 6")
    tasks = c.fetchall()

    conn.close()

    return render_template("dashboard.html",
                           totale=totale,
                           attivi=attivi,
                           revenue=revenue,
                           prenotazioni=prenotazioni,
                           tasks=tasks)

@app.route("/api/charts/overview")
def api_overview():
    if not require_login():
        return jsonify({"error":"unauthorized"}), 401

    conn = db()
    c = conn.cursor()

    c.execute("SELECT status, COUNT(*) AS n FROM clients GROUP BY status")
    by_status = {r["status"]: r["n"] for r in c.fetchall()}

    c.execute("SELECT strftime('%Y-%m', created_at) AS ym, SUM(value) AS s FROM clients GROUP BY ym ORDER BY ym LIMIT 12")
    rev_month = [{"m": r["ym"], "v": float(r["s"] or 0)} for r in c.fetchall()]

    c.execute("SELECT date, COUNT(*) AS n FROM bookings GROUP BY date ORDER BY date DESC LIMIT 14")
    b = c.fetchall()
    b = list(reversed(b))
    bookings_daily = [{"d": r["date"], "n": r["n"]} for r in b]

    conn.close()
    return jsonify({"status": by_status, "rev_month": rev_month, "bookings_daily": bookings_daily})

# ---------------- CLIENTI ----------------

@app.route("/clients")
def clients():
    if not require_login():
        return redirect(url_for("login"))

    q = request.args.get("q","").strip()
    status = request.args.get("status","").strip()
    priority = request.args.get("priority","").strip()

    conn = db()
    c = conn.cursor()

    where = []
    params = []

    if q:
        where.append("(name LIKE ? OR email LIKE ? OR phone LIKE ?)")
        params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])
    if status:
        where.append("status=?")
        params.append(status)
    if priority:
        where.append("priority=?")
        params.append(priority)

    sql = "SELECT * FROM clients"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY created_at DESC LIMIT 200"

    c.execute(sql, params)
    rows = c.fetchall()

    conn.close()
    return render_template("clients.html", clients=rows, q=q, status=status, priority=priority)

@app.route("/clients/new", methods=["GET","POST"])
def clients_new():
    if not require_login():
        return redirect(url_for("login"))
    if request.method == "POST":
        data = (
            request.form.get("name","").strip(),
            request.form.get("email","").strip(),
            request.form.get("phone","").strip(),
            request.form.get("status","Lead"),
            request.form.get("priority","Media"),
            request.form.get("source","Sito"),
            float(request.form.get("value") or 0),
            request.form.get("notes","").strip(),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            request.form.get("last_contact","").strip(),
            request.form.get("next_followup","").strip(),
        )
        conn = db()
        c = conn.cursor()
        c.execute("""
            INSERT INTO clients (name,email,phone,status,priority,source,value,notes,created_at,last_contact,next_followup)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, data)
        conn.commit()
        conn.close()
        flash("Cliente creato con successo.", "success")
        return redirect(url_for("clients"))
    return render_template("client_form.html", mode="new", client=None)

@app.route("/clients/<int:client_id>")
def client_detail(client_id):
    if not require_login():
        return redirect(url_for("login"))
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM clients WHERE id=?", (client_id,))
    client = c.fetchone()
    c.execute("""
        SELECT b.*, c.name AS client_name
        FROM bookings b
        JOIN clients c ON c.id=b.client_id
        WHERE b.client_id=?
        ORDER BY date DESC, time DESC
        LIMIT 50
    """, (client_id,))
    bookings = c.fetchall()
    conn.close()
    if not client:
        flash("Cliente non trovato.", "danger")
        return redirect(url_for("clients"))
    return render_template("client_detail.html", client=client, bookings=bookings)

@app.route("/clients/<int:client_id>/edit", methods=["GET","POST"])
def clients_edit(client_id):
    if not require_login():
        return redirect(url_for("login"))
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM clients WHERE id=?", (client_id,))
    client = c.fetchone()
    if not client:
        conn.close()
        flash("Cliente non trovato.", "danger")
        return redirect(url_for("clients"))

    if request.method == "POST":
        data = (
            request.form.get("name","").strip(),
            request.form.get("email","").strip(),
            request.form.get("phone","").strip(),
            request.form.get("status","Lead"),
            request.form.get("priority","Media"),
            request.form.get("source","Sito"),
            float(request.form.get("value") or 0),
            request.form.get("notes","").strip(),
            request.form.get("last_contact","").strip(),
            request.form.get("next_followup","").strip(),
            client_id
        )
        c.execute("""
            UPDATE clients SET
                name=?, email=?, phone=?, status=?, priority=?, source=?, value=?, notes=?, last_contact=?, next_followup=?
            WHERE id=?
        """, data)
        conn.commit()
        conn.close()
        flash("Cliente aggiornato.", "success")
        return redirect(url_for("client_detail", client_id=client_id))

    conn.close()
    return render_template("client_form.html", mode="edit", client=client)

@app.route("/clients/<int:client_id>/delete", methods=["POST"])
def clients_delete(client_id):
    if not require_login():
        return redirect(url_for("login"))
    conn = db()
    c = conn.cursor()
    c.execute("DELETE FROM bookings WHERE client_id=?", (client_id,))
    c.execute("DELETE FROM clients WHERE id=?", (client_id,))
    conn.commit()
    conn.close()
    flash("Cliente eliminato.", "warning")
    return redirect(url_for("clients"))

# ---------------- PRENOTAZIONI ----------------

@app.route("/bookings")
def bookings():
    if not require_login():
        return redirect(url_for("login"))

    q = request.args.get("q","").strip()
    status = request.args.get("status","").strip()

    conn = db()
    c = conn.cursor()

    sql = """
        SELECT b.*, c.name AS client_name
        FROM bookings b
        LEFT JOIN clients c ON c.id=b.client_id
    """
    where = []
    params = []
    if q:
        where.append("(c.name LIKE ? OR b.service LIKE ?)")
        params.extend([f"%{q}%", f"%{q}%"])
    if status:
        where.append("b.status=?")
        params.append(status)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY b.date DESC, b.time DESC LIMIT 200"

    c.execute(sql, params)
    rows = c.fetchall()

    c.execute("SELECT id, name FROM clients ORDER BY name LIMIT 500")
    clients_list = c.fetchall()

    conn.close()
    return render_template("bookings.html", bookings=rows, clients_list=clients_list, q=q, status=status)

@app.route("/bookings/new", methods=["POST"])
def bookings_new():
    if not require_login():
        return redirect(url_for("login"))

    client_id = int(request.form.get("client_id") or 0)
    date = request.form.get("date","")
    time = request.form.get("time","")
    service = request.form.get("service","").strip()
    amount = float(request.form.get("amount") or 0)
    status = request.form.get("status","Confermata")
    notes = request.form.get("notes","").strip()

    conn = db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO bookings (client_id,date,time,service,amount,status,notes,created_at)
        VALUES (?,?,?,?,?,?,?,?)
    """, (client_id, date, time, service, amount, status, notes, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()
    flash("Prenotazione creata.", "success")
    return redirect(url_for("bookings"))

@app.route("/bookings/<int:booking_id>/delete", methods=["POST"])
def bookings_delete(booking_id):
    if not require_login():
        return redirect(url_for("login"))
    conn = db()
    c = conn.cursor()
    c.execute("DELETE FROM bookings WHERE id=?", (booking_id,))
    conn.commit()
    conn.close()
    flash("Prenotazione eliminata.", "warning")
    return redirect(url_for("bookings"))

@app.route("/bookings/<int:booking_id>/status", methods=["POST"])
def bookings_status(booking_id):
    if not require_login():
        return redirect(url_for("login"))
    new_status = request.form.get("status","Confermata")
    conn = db()
    c = conn.cursor()
    c.execute("UPDATE bookings SET status=? WHERE id=?", (new_status, booking_id))
    conn.commit()
    conn.close()
    flash("Stato prenotazione aggiornato.", "success")
    return redirect(url_for("bookings"))

# ---------------- TASKS ----------------

@app.route("/tasks", methods=["GET","POST"])
def tasks():
    if not require_login():
        return redirect(url_for("login"))
    conn = db()
    c = conn.cursor()

    if request.method == "POST":
        title = request.form.get("title","").strip()
        due = request.form.get("due_date","").strip()
        priority = request.form.get("priority","Media")
        if title:
            c.execute("INSERT INTO tasks (title,due_date,priority,done,created_at) VALUES (?,?,?,?,?)",
                      (title, due, priority, 0, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            flash("Task creato.", "success")

    c.execute("SELECT * FROM tasks ORDER BY done ASC, due_date ASC LIMIT 200")
    rows = c.fetchall()
    conn.close()
    return render_template("tasks.html", tasks=rows)

@app.route("/tasks/<int:task_id>/toggle", methods=["POST"])
def task_toggle(task_id):
    if not require_login():
        return redirect(url_for("login"))
    conn = db()
    c = conn.cursor()
    c.execute("UPDATE tasks SET done = CASE WHEN done=1 THEN 0 ELSE 1 END WHERE id=?", (task_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("tasks"))

@app.route("/tasks/<int:task_id>/delete", methods=["POST"])
def task_delete(task_id):
    if not require_login():
        return redirect(url_for("login"))
    conn = db()
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("tasks"))

# ---------------- CALENDAR (Simple) ----------------

@app.route("/calendar")
def calendar_view():
    if not require_login():
        return redirect(url_for("login"))
    year = int(request.args.get("y") or datetime.now().year)
    month = int(request.args.get("m") or datetime.now().month)

    conn = db()
    c = conn.cursor()
    c.execute("""
        SELECT b.id, b.date, b.time, b.service, b.status, c.name AS client_name
        FROM bookings b
        LEFT JOIN clients c ON c.id=b.client_id
        WHERE strftime('%Y', b.date)=? AND strftime('%m', b.date)=?
        ORDER BY b.date, b.time
    """, (str(year), f"{month:02d}"))
    bookings = c.fetchall()
    conn.close()

    # group bookings by day
    by_day = {}
    for b in bookings:
        by_day.setdefault(b["date"], []).append(b)

    cal = calendar.Calendar(firstweekday=0).monthdayscalendar(year, month)
    month_name = calendar.month_name[month]

    return render_template("calendar.html",
                           year=year, month=month, month_name=month_name,
                           cal=cal, by_day=by_day)

if __name__ == "__main__":
    app.run(debug=True)