import psycopg2

conn = psycopg2.connect(
    dbname="hotel_booking",
    user="admin",
    password="admin",
    host="localhost",
    port="5432"
)
cur = conn.cursor()

def show_menu():
    print("""
1 - Додати гостя
2 - Показати всіх гостей
3 - Додати бронювання
4 - Показати бронювання
5 - Вийти
""")

def add_guest():
    name = input("Ім'я: ")
    phone = input("Телефон: ")
    email = input("Email: ")
    cur.execute("INSERT INTO guests (full_name, phone, email) VALUES (%s, %s, %s)", (name, phone, email))
    conn.commit()

def show_guests():
    cur.execute("SELECT * FROM guests")
    for row in cur.fetchall():
        print(row)

def add_booking():
    guest_id = input("ID гостя: ")
    room_id = input("ID кімнати: ")
    check_in = input("Дата заїзду (YYYY-MM-DD): ")
    check_out = input("Дата виїзду (YYYY-MM-DD): ")
    cur.execute("""
        INSERT INTO bookings(guest_id, room_id, check_in, check_out, status)
        VALUES (%s,%s,%s,%s,'pending')
    """, (guest_id, room_id, check_in, check_out))
    conn.commit()

def show_bookings():
    cur.execute("SELECT * FROM bookings")
    for row in cur.fetchall():
        print(row)

while True:
    show_menu()
    choice = input("Ваш вибір: ")

    if choice == "1":
        add_guest()
    elif choice == "2":
        show_guests()
    elif choice == "3":
        add_booking()
    elif choice == "4":
        show_bookings()
    elif choice == "5":
        break

cur.close()
conn.close()
