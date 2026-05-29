import sqlite3
import os
p1 = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'keystroke_db.db'))
p2 = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'keystroke_db.db'))
for p in (p1, p2):
	print('checking db path:', p)
	if not os.path.exists(p):
		print('  db not found')
		continue
	print('  db size bytes:', os.path.getsize(p))
	conn = sqlite3.connect(p)
	cur = conn.execute("PRAGMA table_info('typing_sessions')")
	cols = [r[1] for r in cur.fetchall()]
	print('  columns:', cols)
	conn.close()
