import psycopg2
from psycopg2 import sql
import os

DB_NAME = 'odd'
DB_USER = 'openpg'
DB_PASS = 'openpgpwd'
DB_HOST = 'localhost'
DB_PORT = 5432

icon_path = os.path.join(r'C:\Program Files\odoo\server\odoo\addons\tapis_erp', 'static', 'description', 'icon.png')

conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)
cur = conn.cursor()
with open(icon_path, 'rb') as f:
    data = f.read()
# Update any menu that references tapis_erp in web_icon or name 'Tapis ERP'
cur.execute("SELECT id, name FROM ir_ui_menu WHERE web_icon LIKE %s OR name = %s", ("%tapis_erp%", 'Tapis ERP'))
rows = cur.fetchall()
if not rows:
    print('No matching menu rows found; aborting')
else:
    for r in rows:
        menu_id = r[0]
        cur.execute(sql.SQL("UPDATE ir_ui_menu SET web_icon_data = %s WHERE id = %s"), (psycopg2.Binary(data), menu_id))
        print(f'Updated menu id {menu_id} ({r[1]})')
    conn.commit()
cur.close()
conn.close()
print('Done')
