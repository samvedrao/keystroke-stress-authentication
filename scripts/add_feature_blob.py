import sqlite3
p = r'C:\Documents\KeyboardPersonality\instance\keystroke_db.db'
conn = sqlite3.connect(p)
try:
    conn.execute("ALTER TABLE typing_sessions ADD COLUMN feature_blob TEXT")
    conn.commit()
    print('ALTER TABLE succeeded')
except Exception as e:
    print('ALTER TABLE failed:', e)
finally:
    conn.close()
