import sqlite3, os
p = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'keystroke_db.db'))
print('checking root db path:', p)
if not os.path.exists(p):
    print('db not found')
else:
    print('db size bytes:', os.path.getsize(p))
    conn = sqlite3.connect(p)
    cur = conn.execute("PRAGMA table_info('typing_sessions')")
    cols = [r[1] for r in cur.fetchall()]
    print('columns:', cols)
    conn.close()
