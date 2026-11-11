import sqlite3
db = r"c:\project\BaseBallAttendanceSimulator\baseball_attendance.db"
conn = sqlite3.connect(db)
cur = conn.cursor()
tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
for (t,) in tables:
    (n,) = cur.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()
    print(f"{t:>25}: {n:>8,} rows")
conn.close()

