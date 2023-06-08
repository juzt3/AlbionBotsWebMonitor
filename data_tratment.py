import datetime
import numerize.numerize as nz


def parse_datetime(datestr: str):
    return datetime.datetime.strptime(datestr, "%Y-%m-%d %H:%M:%S")


def transactions_to_average_per_month(transactions, year: int, game_format=True):
    avg_per_month = dict()

    for transaction in transactions:
        t_date = parse_datetime(transaction['date'])
        if t_date.year == year:
            f_month = t_date.strftime("%B")
            if f_month not in avg_per_month:
                avg_per_month[f_month] = transaction['quantity']
            else:
                avg_per_month[f_month] += transaction['quantity']

    if game_format:
        for key, avg in avg_per_month.items():
            avg_per_month[key] = nz.numerize(avg)

    return avg_per_month
