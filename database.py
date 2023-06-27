import datetime
import sqlite3
import os.path
import json
import pandas as pd


def connect():
    """
        Establece una conexión con la base de datos o crea una nueva si no existe.
    """
    if os.path.isfile("./bots.db"):
        conn = sqlite3.connect("bots.db")
    else:
        conn = create_tables()

    #  conn.execute('PRAGMA journal_mode = OFF;')  # Prevents to insert a row
    #  conn.execute('PRAGMA synchronous = 0;')
    #  conn.execute('PRAGMA cache_size = 1000000;')  # give it a GB
    #  conn.execute('PRAGMA locking_mode = EXCLUSIVE;')
    #  conn.execute('PRAGMA temp_store = MEMORY;')

    return conn


def create_tables():
    """
        Crea las tablas "Bots" y "Transactions" en la base de datos.
    """
    conn = sqlite3.connect("bots.db")
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS Bots (
        name TEXT,
        local_ip TEXT,
        temp INTEGER,
        gathering_map TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS Transactions (
            date TEXT,
            quantity INTEGER,
            bot_id INTEGER
    )""")

    conn.commit()
    return conn


def fetch_all_bots(in_json=True):
    """
        Devuelve todos las entradas de la tabla "Bots".
    """
    conn = connect()
    if in_json:
        conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""SELECT * FROM Bots""")
    rows = c.fetchall()
    conn.close()

    if in_json:
        rows = json.dumps([dict(ix) for ix in rows])
        rows = json.loads(rows)

    return rows


def fetch_bots_name():
    conn = connect()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""SELECT name FROM Bots""")
    rows = c.fetchall()
    conn.close()

    rows = json.dumps([dict(ix) for ix in rows])
    rows = json.loads(rows)

    return rows


def fetch_bot_details(bot_name: str, in_json=True):
    conn = connect()
    if in_json:
        conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""SELECT * FROM Bots WHERE name = (?)""", [bot_name])
    rows = c.fetchall()
    conn.close()

    if in_json:
        rows = json.dumps([dict(ix) for ix in rows])
        rows = json.loads(rows)
    return rows[0]


def insert_bot(name: str, local_ip: str, temp: int, gathering_map: str):
    """
        Inserta un nuevo bot en la tabla "Bots".
    """
    conn = connect()
    c = conn.cursor()

    c.execute("""INSERT INTO Bots VALUES (?,?,?,?)""", (name, local_ip, temp, gathering_map))
    conn.commit()
    conn.close()


def delete_bot(name: str):
    """
        Borra un bot de la tabla "Bots".
    """
    conn = connect()
    c = conn.cursor()
    c.execute("""DELETE FROM Bots WHERE name = (?)""", [name])
    conn.commit()
    conn.close()


def update_bot(name: str, local_ip: str, temp: int, gathering_map: str):
    conn = connect()
    c = conn.cursor()

    c.execute("""UPDATE Bots SET local_ip = (?), temp = (?), gathering_map = (?)
                    WHERE name = (?)""", (local_ip, temp, gathering_map, name))
    conn.commit()
    conn.close()


def update_temp(bot_name: str, new_temp: int):
    """
        Actualiza la temperatura de un bot en la tabla "Bots".
    """
    conn = connect()
    c = conn.cursor()

    c.execute("""UPDATE Bots SET temp = (?)
                WHERE name = (?)""", (new_temp, bot_name))
    conn.commit()
    conn.close()


def update_local_ip(bot_name: str, new_ip: str):
    """
        Actualiza la dirección IP local de un bot en la tabla "Bots".
    """
    conn = connect()
    c = conn.cursor()

    c.execute("""UPDATE Bots SET local_ip = (?)
                    WHERE name = (?)""", (new_ip, bot_name))
    conn.commit()
    conn.close()


def insert_transaction(quantity: int, bot_name: str, date=None):
    """
        Inserta una nueva transacción en la tabla "Transactions" asociada a un bot.
    """
    conn = connect()
    c = conn.cursor()
    if date is None:
        date = datetime.datetime.now()
    bot_id = get_bot_id(bot_name)
    c.execute("""INSERT INTO Transactions VALUES (datetime(?),?,?)""", (date, quantity, bot_id))
    conn.commit()
    conn.close()


def insert_batch_transactions(transactions_list):
    """
        Inserta una lista de transacciones en la tabla "Transactions" asociada a un bot.

        El formato esperado es:
        transaction_list = [(bot_name, quantity)]

        Esta funcíon se usa cuando una serie de transacciones no han sido ingresadas en la base de datos
        y el cliente manda una lista de las transacciones que no ha podido guardar ya sea por que el servidor
        no esta disponible o hay algun problema con la red.
    """
    conn = connect()
    bot_name = transactions_list[0][0]
    bot_id = get_bot_id(bot_name)
    date = datetime.datetime.now()
    t_ready = list()
    for transaction in transactions_list:
        t_ready.append((date, transaction[1], bot_id))

    conn.execute("BEGIN")
    conn.executemany("INSERT INTO Transactions VALUES (datetime(?),?,?)", t_ready)
    conn.commit()
    conn.close()


def fetch_all_transactions_from_bot(bot_name: str, in_json=True):
    """
        Obtiene todas las transacciones asociadas a un bot de la tabla "Transactions".
    """
    conn = connect()
    if in_json:
        conn.row_factory = sqlite3.Row
    c = conn.cursor()
    bot_id = get_bot_id(bot_name)
    if bot_id:
        c.execute("""SELECT * FROM Transactions WHERE bot_id = (?)""", [bot_id])
        rows = c.fetchall()
        if in_json:
            rows = json.dumps([dict(ix) for ix in rows])
            rows = json.loads(rows)
    else:
        rows = list()
    conn.close()
    return rows


def fetch_transactions_by_year(bot_name: str, year: int):
    """
    Obtiene las transacciones de un año específico y un bot_id dado directamente de la base de datos.
    """
    conn = connect()
    bot_id = get_bot_id(bot_name)
    query = """
        SELECT date, quantity
        FROM Transactions
        WHERE strftime('%Y', date) = ? AND bot_id = ?
    """
    transactions = pd.read_sql_query(query, conn, params=(str(year), int(bot_id)))
    return transactions


def fetch_transactions_by_month(bot_name: str, year: int, month: int):
    if month < 10:
        month = "0"+str(month)
    conn = connect()
    bot_id = get_bot_id(bot_name)
    query = """
            SELECT date, quantity
            FROM Transactions
            WHERE strftime('%Y', date) = ? AND strftime('%m', date) = ? AND bot_id = ?
        """
    transactions = pd.read_sql_query(query, conn, params=(str(year), month, int(bot_id)))
    return transactions


def get_bot_id(bot_name: str):
    """
        Obtiene el ID de un bot según su nombre en la tabla "Bots".
    """
    conn = connect()
    c = conn.cursor()
    c.execute("""SELECT rowid FROM Bots WHERE name = (?)""", [bot_name])
    try:
        bot_id = c.fetchone()[0]
    except TypeError:
        bot_id = None
    conn.close()
    return bot_id


def create_date_transactions_index():
    """
    Crea un índice en la columna 'date' de la tabla 'Transactions'.
    """
    conn = connect()
    c = conn.cursor()
    c.execute("CREATE INDEX idx_transactions_date ON Transactions(date)")
    conn.commit()
    conn.close()
