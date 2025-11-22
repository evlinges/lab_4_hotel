from flask import Flask, render_template, request, redirect, session, send_file, jsonify
import psycopg2
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import tempfile
import subprocess
import datetime
import openpyxl

app = Flask(__name__)
app.secret_key = "supersecretkey"


# ======================
#  DB CONNECTION
# ======================
def get_conn():
    return psycopg2.connect(
        dbname="hotel_booking",
        user="admin",
        password="admin",
        host="localhost",
        port=5432
    )


# ======================
#  AUTH HELPERS
# ======================
def require_login():
    return "user_id" in session


def require_role(role):
    return session.get("role") == role


# ======================
#  ROUTES (WEB PAGES)
# ======================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/guests")
def guests():
    if not require_login():
        return redirect("/login")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM guests ORDER BY id")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("guests.html", guests=rows)


@app.route("/rooms")
def rooms():
    if not require_login():
        return redirect("/login")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM available_rooms ORDER BY id")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("rooms.html", rooms=rows)


@app.route("/bookings")
def bookings():
    if not require_login():
        return redirect("/login")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM booking_details ORDER BY booking_id")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("bookings.html", bookings=rows)


# ======================
#        LOGIN
# ======================

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, role 
            FROM users 
            WHERE username=%s AND password=%s
        """, (username, password))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            session["user_id"] = user[0]
            session["role"] = user[1]
            return redirect("/")
        else:
            error = "Невірний логін або пароль"

    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ======================
#        LOGS
# ======================

@app.route("/logs")
def logs():
    if not require_login():
        return redirect("/login")

    if not require_role("admin"):
        return "Доступ заборонено", 403

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM logs ORDER BY created_at DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("logs.html", logs=rows)


# ======================
#         PDF REPORT
# ======================

@app.route("/report/pdf")
def report_pdf():
    if not require_login():
        return redirect("/login")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT booking_id, guest, hotel, room_number,
               check_in, check_out, total_price, status
        FROM booking_details
        ORDER BY booking_id
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")

    c = canvas.Canvas(temp.name, pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(30, 750, "Звіт про бронювання")

    c.setFont("Helvetica", 12)
    y = 720

    for row in rows:
        text = f"ID:{row[0]} | {row[1]} | {row[2]} | Кімн:{row[3]} | {row[4]} → {row[5]} | {row[6]} грн | {row[7]}"
        c.drawString(30, y, text)
        y -= 20

        if y < 50:
            c.showPage()
            c.setFont("Helvetica", 12)
            y = 750

    c.save()

    return send_file(temp.name, as_attachment=True, download_name="bookings_report.pdf")


# ======================
#         EXCEL REPORT
# ======================

@app.route("/report/excel")
def report_excel():
    if not require_login():
        return redirect("/login")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT booking_id, guest, hotel, room_number,
               check_in, check_out, total_price, status
        FROM booking_details
        ORDER BY booking_id
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Bookings"

    ws.append(["ID", "Guest", "Hotel", "Room", "Check-in", "Check-out", "Total", "Status"])

    for row in rows:
        ws.append(row)

    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    wb.save(temp.name)

    return send_file(temp.name, as_attachment=True, download_name="bookings_report.xlsx")


# ======================
#         BACKUP
# ======================

@app.route("/backup")
def backup():
    if not require_login():
        return redirect("/login")

    if not require_role("admin"):
        return "Доступ заборонено", 403

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"backup_{timestamp}.sql"

    cmd = [
        "pg_dump",
        "-U", "admin",
        "-d", "hotel_booking",
        "-h", "localhost",
        "-p", "5432",
        "-f", filename
    ]

    subprocess.run(cmd, check=True)

    return send_file(filename, as_attachment=True)


# ======================
#       STATISTICS
# ======================

@app.route("/stats")
def stats():
    if not require_login():
        return redirect("/login")

    conn = get_conn()
    cur = conn.cursor()

    # Доходи по місяцях
    cur.execute("""
        SELECT 
            TO_CHAR(check_in, 'YYYY-MM') AS month,
            SUM(total_price)
        FROM booking_details
        GROUP BY month
        ORDER BY month
    """)
    income_rows = cur.fetchall()

    income_data = {
        "labels": [row[0] for row in income_rows],
        "values": [float(row[1]) for row in income_rows]
    }

    # Бронювання по готелях
    cur.execute("""
        SELECT hotel, COUNT(*)
        FROM booking_details
        GROUP BY hotel
        ORDER BY hotel
    """)
    hotel_rows = cur.fetchall()

    hotel_data = {
        "labels": [row[0] for row in hotel_rows],
        "values": [row[1] for row in hotel_rows]
    }

    cur.close()
    conn.close()

    return render_template("stats.html",
                           income_data=income_data,
                           hotel_data=hotel_data)


# ======================
#           API
# ======================

@app.route("/api/bookings", methods=["GET"])
def api_get_bookings():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT booking_id, guest, hotel, room_number,
               check_in, check_out, total_price, status
        FROM booking_details
        ORDER BY booking_id
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    result = []
    for r in rows:
        result.append({
            "booking_id": r[0],
            "guest": r[1],
            "hotel": r[2],
            "room_number": r[3],
            "check_in": str(r[4]),
            "check_out": str(r[5]),
            "total_price": float(r[6]),
            "status": r[7]
        })

    return jsonify(result)


@app.route("/api/bookings", methods=["POST"])
def api_create_booking():
    data = request.get_json()

    required = ["guest_id", "room_id", "check_in", "check_out"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO bookings (guest_id, room_id, check_in, check_out, status)
        VALUES (%s, %s, %s, %s, 'confirmed')
        RETURNING id
    """, (data["guest_id"], data["room_id"], data["check_in"], data["check_out"]))

    new_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"message": "Booking created", "booking_id": new_id}), 201


@app.route("/api/bookings/<int:booking_id>", methods=["DELETE"])
def api_delete_booking(booking_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("DELETE FROM bookings WHERE id = %s", (booking_id,))
    deleted = cur.rowcount

    conn.commit()
    cur.close()
    conn.close()

    if deleted == 0:
        return jsonify({"error": "Booking not found"}), 404

    return jsonify({"message": "Booking deleted"})


# ======================
#       START APP
# ======================

if __name__ == "__main__":
    app.run(debug=True)
