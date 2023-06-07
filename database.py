import datetime
import sqlite3
import os.path


def connect():
    """
        Establece una conexión con la base de datos o crea una nueva si no existe.
    """
    if os.path.isfile("./bots.db"):
        conn = sqlite3.connect("bots.db")
        return conn
    else:
        return create_tables()


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


def fetch_all_bots():
    """
        Devuelve todos las entradas de la tabla "Bots".
    """
    conn = connect()
    c = conn.cursor()
    c.execute("""SELECT * FROM Bots""")
    data = c.fetchall()
    conn.close()
    return data

def insert_bot(name: str, local_ip: str, temp: int, gathering_map: str):
    """
        Inserta un nuevo bot en la tabla "Bots".
    """
    conn = connect()
    c = conn.cursor()

    c.execute("""INSERT INTO Bots VALUES (?,?,?,?)""", (name, local_ip, temp, gathering_map))
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


def insert_transaction(quantity: int, bot_name: str):
    """
        Inserta una nueva transacción en la tabla "Transactions" asociada a un bot.
    """
    conn = connect()
    c = conn.cursor()
    date = datetime.datetime.now()
    bot_id = get_bot_id(bot_name)
    c.execute("""INSERT INTO Transactions VALUES (datetime(?),?,?)""", (date, quantity, bot_id))
    conn.commit()
    conn.close()


def fetch_all_transactions_from_bot(bot_name: str):
    """
        Obtiene todas las transacciones asociadas a un bot de la tabla "Transactions".
    """
    conn = connect()
    c = conn.cursor()
    bot_id = get_bot_id(bot_name)
    if bot_id:
        c.execute("""SELECT * FROM Transactions WHERE bot_id = (?)""", [bot_id])
        data = c.fetchall()
    else:
        data = list()
    conn.close()
    return data


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
