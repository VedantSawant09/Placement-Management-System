import sqlite3

conn = sqlite3.connect('placement.db')
c = conn.cursor()
c.execute('SELECT id, name, email, role FROM users WHERE role="admin"')
admins = c.fetchall()
print('Admin users:', admins)
conn.close()