import datetime
import numerize.numerize as nz
import pandas as pd


def parse_datetime(datestr: str):
    return datetime.datetime.strptime(datestr, "%Y-%m-%d %H:%M:%S")


def transactions_to_total_per_month(transactions, year: int, game_format=True):
    total_per_month = dict()

    for transaction in transactions:
        t_date = parse_datetime(transaction['date'])
        if t_date.year == year:
            f_month = t_date.strftime("%B")
            if f_month not in total_per_month:
                total_per_month[f_month] = transaction['quantity']
            else:
                total_per_month[f_month] += transaction['quantity']

    if game_format:
        for key, avg in total_per_month.items():
            total_per_month[key] = nz.numerize(avg)

    return total_per_month


def calculate_total_per_month(transactions, game_format=False):
    """
    Calcula el total de cantidad por mes a partir de las transacciones proporcionadas.
    """
    transactions['date'] = pd.to_datetime(transactions['date'])
    transactions['month'] = transactions['date'].dt.strftime('%B')
    total_per_month = transactions.groupby('month')['quantity'].sum().to_dict()
    avg_year = 0
    if game_format:
        for key, avg in total_per_month.items():
            if game_format:
                total_per_month[key] = nz.numerize(avg)[:-1]
            avg_year += float(total_per_month[key])
        avg_year /= len(total_per_month)
        avg_year = round(avg_year, 1)

    months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    total_per_month = dict(sorted(total_per_month.items(), key=lambda x: months.index(x[0])))

    return total_per_month, avg_year
