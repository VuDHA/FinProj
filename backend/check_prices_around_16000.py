import sqlite3

conn = sqlite3.connect("e:/FinProj/backend/data/wealth.db")
c = conn.cursor()

print("Snapshots with price between 15000 and 17000:")
c.execute("""
    SELECT a.symbol, a.name, p.date, p.price, p.change, p.change_percent
    FROM pricesnapshot p
    JOIN asset a ON p.asset_id = a.id
    WHERE p.price BETWEEN 15000 AND 17000
    ORDER BY p.price DESC
""")
rows = c.fetchall()
if rows:
    for row in rows:
        print(row)
else:
    print("None")

conn.close()
