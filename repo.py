import sqlite3 as sl


def create_symbols_table():
    db = sl.connect('./db/bot.db')
    with db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS pairs (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                pair TEXT
            );
        """)
    return

def create_orders_table():
    db = sl.connect('./db/bot.db')
    with db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                pair_id INTEGER NOT NULL,
                bot_name TEXT,
                ticket TEXT,
                open_price REAL NOT NULL,
                opened_at DATETIME NOT NULL,
                close_price REAL,
                closed_at DATETIME,
                profit REAL DEFAULT 0.0,
                FOREIGN KEY(pair_id) REFERENCES pairs(id)
            );
        """)
    return

def get_pair_id(pair):
    db = sl.connect('./db/bot.db')
    with db:
        cur = db.cursor()
        cur.execute('SELECT id FROM pairs WHERE pair=(?);', (pair,))
        rows = cur.fetchall()
        if len(rows) > 0: return rows[0][0]

        cur.execute('INSERT INTO pairs (pair) VALUES (?);', (pair,))
        cur.execute('SELECT last_insert_rowid() FROM pairs;')
        rows = cur.fetchall()
        return rows[0][0]

def insert_order(bot, order):
    db = sl.connect('./db/bot.db')
    with db:
        cur = db.cursor()
        cur.execute("""
            INSERT INTO orders
            (pair_id, bot_name, ticket, open_price, opened_at) VALUES
            (?, ?, ?, ?, CURRENT_TIMESTAMP);
        """, (bot.pair_id, bot.name, order.ticket, order.price))
        
        cur.execute('SELECT last_insert_rowid() FROM orders')
        rows = cur.fetchall()
        return rows[0][0]


def close_order(order):
    db = sl.connect('./db/bot.db')
    with db:
        cur = db.cursor()
        cur.execute("""
            UPDATE orders SET
            close_price = (?),
            closed_at = CURRENT_TIMESTAMP
            WHERE id = (?);
        """, (order.curr_price, order.db_id))
