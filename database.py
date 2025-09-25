import datetime
import sqlite3
import os.path
import json
import pandas as pd
import aiosqlite


async def connect():
    """
        Establece una conexión con la base de datos o crea una nueva si no existe.
    """
    if os.path.isfile("./bots.db"):
        conn = await aiosqlite.connect("bots.db")
    else:
        conn = await create_tables()

    #  conn.execute('PRAGMA journal_mode = OFF;')  # Prevents to insert a row
    #  conn.execute('PRAGMA synchronous = 0;')
    #  conn.execute('PRAGMA cache_size = 1000000;')  # give it a GB
    #  conn.execute('PRAGMA locking_mode = EXCLUSIVE;')
    #  conn.execute('PRAGMA temp_store = MEMORY;')

    return conn


async def create_tables():
    """
        Crea las tablas "Bots" y "Transactions" en la base de datos.
    """
    conn = await aiosqlite.connect("bots.db")

    await conn.execute("""CREATE TABLE IF NOT EXISTS Bots (
        name TEXT,
        local_ip TEXT,
        temp INTEGER,
        gathering_map TEXT
    )""")

    await conn.execute("""CREATE TABLE IF NOT EXISTS Transactions (
            date TEXT,
            quantity INTEGER,
            bot_id INTEGER
    )""")

    await conn.commit()
    return conn


async def fetch_all_bots(in_json=True):
    """
        Devuelve todos las entradas de la tabla "Bots".
    """
    conn = await connect()
    if in_json:
        conn.row_factory = sqlite3.Row
    c = await conn.execute("""SELECT * FROM Bots""")
    rows = await c.fetchall()
    await conn.close()

    if in_json:
        rows = json.dumps([dict(ix) for ix in rows])
        rows = json.loads(rows)

    return rows


async def fetch_bots_name():
    conn = await connect()
    conn.row_factory = sqlite3.Row
    c = await conn.execute("""SELECT name FROM Bots""")
    rows = await c.fetchall()
    await conn.close()

    rows = json.dumps([dict(ix) for ix in rows])
    rows = json.loads(rows)

    return rows


async def fetch_bot_details(bot_name: str, in_json=True):
    conn = await connect()
    if in_json:
        conn.row_factory = sqlite3.Row
    c = await conn.execute("""SELECT * FROM Bots WHERE name = (?)""", [bot_name])
    rows = await c.fetchall()
    await conn.close()

    if in_json:
        rows = json.dumps([dict(ix) for ix in rows])
        rows = json.loads(rows)
    return rows[0]


async def insert_bot(name: str, local_ip: str, temp: int, gathering_map: str):
    """
        Inserta un nuevo bot en la tabla "Bots".
    """
    conn = await connect()

    await conn.execute("""INSERT INTO Bots VALUES (?,?,?,?)""", (name, local_ip, temp, gathering_map))
    await conn.commit()
    await conn.close()


async def delete_bot(name: str):
    """
        Borra un bot de la tabla "Bots".
    """
    conn = await connect()
    await conn.execute("""DELETE FROM Bots WHERE name = (?)""", [name])
    await conn.commit()
    await conn.close()


async def update_bot(name: str, local_ip: str, temp: int, gathering_map: str):
    conn = await connect()

    await conn.execute("""UPDATE Bots SET local_ip = (?), temp = (?), gathering_map = (?)
                    WHERE name = (?)""", (local_ip, temp, gathering_map, name))
    await conn.commit()
    await conn.close()


async def update_temp(bot_name: str, new_temp: int):
    """
        Actualiza la temperatura de un bot en la tabla "Bots".
    """
    conn = await connect()

    await conn.execute("""UPDATE Bots SET temp = (?)
                WHERE name = (?)""", (new_temp, bot_name))
    await conn.commit()
    await conn.close()


async def update_local_ip(bot_name: str, new_ip: str):
    """
        Actualiza la dirección IP local de un bot en la tabla "Bots".
    """
    conn = await connect()

    conn.execute("""UPDATE Bots SET local_ip = (?)
                    WHERE name = (?)""", (new_ip, bot_name))
    await conn.commit()
    await conn.close()


async def insert_transaction(quantity: int, bot_name: str, date=None):
    """
        Inserta una nueva transacción en la tabla "Transactions" asociada a un bot.
    """
    conn = await connect()
    if date is None:
        date = datetime.datetime.now()
    bot_id = await get_bot_id(bot_name)
    await conn.execute("""INSERT INTO Transactions VALUES (datetime(?),?,?)""", (date, quantity, bot_id))
    await conn.commit()
    await conn.close()


async def insert_batch_transactions(transactions_list):
    """
        Inserta una lista de transacciones en la tabla "Transactions" asociada a un bot.

        El formato esperado es:
        transaction_list = [(bot_name, quantity)]

        Esta funcíon se usa cuando una serie de transacciones no han sido ingresadas en la base de datos
        y el cliente manda una lista de las transacciones que no ha podido guardar ya sea por que el servidor
        no esta disponible o hay algun problema con la red.
    """
    conn = await connect()
    bot_name = transactions_list[0][0]
    bot_id = await get_bot_id(bot_name)
    date = datetime.datetime.now()
    t_ready = list()
    for transaction in transactions_list:
        t_ready.append((date, transaction[1], bot_id))

    await conn.execute("BEGIN")
    await conn.executemany("INSERT INTO Transactions VALUES (datetime(?),?,?)", t_ready)
    await conn.commit()
    await conn.close()


async def fetch_all_transactions_from_bot(bot_name: str, in_json=True):
    """
        Obtiene todas las transacciones asociadas a un bot de la tabla "Transactions".
    """
    conn = await connect()
    if in_json:
        conn.row_factory = sqlite3.Row
    bot_id = get_bot_id(bot_name)
    if bot_id:
        c = await conn.execute("""SELECT * FROM Transactions WHERE bot_id = (?)""", [bot_id])
        rows = await c.fetchall()
        if in_json:
            rows = json.dumps([dict(ix) for ix in rows])
            rows = json.loads(rows)
    else:
        rows = list()
    await conn.close()
    return rows


async def fetch_transactions_by_year(year: int, bot_name: str = None):
    """
    Obtiene las transacciones de un año específico y un bot_id dado directamente de la base de datos.
    """
    conn = await connect()
    if bot_name:
        bot_id = await get_bot_id(bot_name)
        query = """
            SELECT date, quantity
            FROM Transactions
            WHERE strftime('%Y', date) = ? AND bot_id = ?
        """
        async with conn.execute(query, (str(year), str(bot_id))) as cursor:
            rows = await cursor.fetchall()
            # Crear un DataFrame de pandas a partir de los resultados
            df = pd.DataFrame(rows, columns=['date', 'quantity'])
    else:
        query = """
            SELECT date, quantity
            FROM Transactions
            WHERE strftime('%Y', date) = ?
        """
        async with conn.execute(query, (str(year), )) as cursor:
            rows = await cursor.fetchall()
            # Crear un DataFrame de pandas a partir de los resultados
            df = pd.DataFrame(rows, columns=['date', 'quantity'])
    return df


async def fetch_transactions_by_month(year: int, month: int, bot_name: str = None, group_by_day=False):
    month = f"{month:02}"
    conn = await connect()
    if bot_name:
        bot_id = await get_bot_id(bot_name)
        query = """
                SELECT date, quantity
                FROM Transactions
                WHERE strftime('%Y', date) = ? AND strftime('%m', date) = ? AND bot_id = ?
            """
        async with conn.execute(query, (str(year), str(month), str(bot_id))) as cursor:
            rows = await cursor.fetchall()
            # Creamos un DataFrame de pandas a partir de los resultados
            transactions = pd.DataFrame(rows, columns=['date', 'quantity'])
    else:
        query = """
            SELECT date, quantity
            FROM Transactions
            WHERE strftime('%Y', date) = ? AND strftime('%m', date) = ?
        """
        async with conn.execute(query, (str(year), str(month))) as cursor:
            rows = await cursor.fetchall()
            # Creamos un DataFrame de pandas a partir de los resultados
            transactions = pd.DataFrame(rows, columns=['date', 'quantity'])

    if not group_by_day:
        return transactions
    else:
        # Convertimos la columna 'date' al tipo datetime para poder manipularla mejor
        transactions.__setitem__('date', pd.to_datetime(transactions.__getitem__('date')))

        # Agrupamos las transacciones por día y sumamos las cantidades para obtener el total por día
        daily_transactions = transactions.groupby(transactions['date'].dt.date)['quantity'].sum().reset_index()
        return daily_transactions


async def get_bot_id(bot_name: str):
    """
        Obtiene el ID de un bot según su nombre en la tabla "Bots".
    """
    conn = await connect()
    c = await conn.execute("""SELECT rowid FROM Bots WHERE name = (?)""", [bot_name])
    try:
        result = await c.fetchone()
        if result is None:
            bot_id = None
        else:
            bot_id = result[0]
    except TypeError:
        bot_id = None
    await conn.close()
    return bot_id


async def create_date_transactions_index():
    """
    Crea un índice en la columna 'date' de la tabla 'Transactions'.
    """
    conn = await connect()
    await conn.execute("CREATE INDEX idx_transactions_date ON Transactions(date)")
    await conn.commit()
    await conn.close()
