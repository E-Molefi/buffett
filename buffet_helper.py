"""
@author: EM
@author: SA

This is a helper file for the application,
it consists of functional utilities needed by the application.
"""

from flask import redirect, url_for, request, session
from functools import wraps

import datetime as dt
import pandas as pd
import pandas_datareader.data as web
import pandas_datareader as pdr
from datetime import datetime, timedelta
import time

def usd(value):
    """
    @author: EM
    Format an amount in usd currency.
    """
    return f"${value:,.2f}"

def login_required(f):
    """
    @author: EM
    @author: SA

    Login is required for any route that is visited by the user.
    """
    @wraps(f)
    def decorated_function(*args,**kwargs):
        # return redirect(url_for("login"))
        # if session["username"] is None:
        if "username" not in session:
            # return redirect(url_for('login', next=request.url))
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

def plotter(symbol):
    """
    @author: EM
    Prepare data to be used for plotting to the webpage depending on the symbol supplied.

    """
    # The start date of the data to be fetched from the API
    # The end date is defaulted to today's date
    start = dt.datetime(2016, 1, 1)

    # Currently the data manipulated goes back 3 months from the current date
    n_data = 60 # for 60 days / or 3 months
    # n_data = 30 # for 30 days / or 1 month

    df = web.DataReader(symbol, "iex", start)
    df.to_csv("iex.csv")
    df = pd.read_csv("iex.csv")

    df = df.set_index(df.date)

    data = {}
    ldate = []
    lhigh = []
    llow = []
    lopen = []
    lclose = []

    lt = df.tail(n_data).index.values

    for i in lt:
        d = datetime.strptime(i, "%Y-%m-%d")
        d = datetime.strftime(d, "%Y-%m-%d")
        ldate.append(d)

    for k in range(n_data):
        lhigh.append(df.tail(n_data)["high"][k])
        llow.append(df.tail(n_data)["low"][k])
        lopen.append(df.tail(n_data)["open"][k])
        lclose.append(df.tail(n_data)["close"][k])

    data["date"] = ldate
    data["high"] = lhigh
    data["low"] = llow
    data["open"] = lopen
    data["close"] = lclose

    return data

def search_autocomplete():
    """
    @author: EM
    Functionality to return all the symbols that are supported by IEX API.
    """
    symbols = web.get_iex_symbols().symbol.values
    names = web.get_iex_symbols().name.values

    data = {}
    data["symbols"] = symbols.tolist()
    data["names"] = names.tolist()

    values = []

    for q in range(len(symbols)):
        values.append(data["symbols"][q] + " " + data["names"][q])
    return values

def prepare_leaderboard(symbol=None):
    """
    @author: EM
    Functionality to do some arithmetic for the leaderboard display
    """
    data = {}
    if symbol is not None:
        df = web.DataReader(symbol, "iex", dt.date(2019, 3, 11)) # Edit this line for when the market is closed
        # df = web.DataReader(symbol, "iex", dt.date.today())
        # df = df.head(1)
        open_price = df["open"].values
        close_price = df["close"].values
        data["open_price"] = open_price
        data["close_price"] = close_price

        return data

def get_gainers_losers(symbols):
    """
    @author: EM
    """
    t3m = timedelta(days=60)
    today = datetime.today()
    t3m_ago = today - t3m

    data = {}
    symbol_cur_price = []

    # Retrieve current price
    for s in symbols:
        df = web.DataReader(s, "iex", today)
        # data[s] = df.loc[today.date().strftime('%Y-%m-%d')]

        # datetime.strptime(today, '%Y-%m-%d')


    return data

def quote_validate(symbol):
    """
    @author: EM
    Look up and confirm quote for symbol.

    This function is undergoing serious changes and should not be relied on at the moment.
    """

    # Reject symbol if it starts with caret
    if symbol.startswith("^"):
        return None

    # Reject symbol if it contains comma
    if "," in symbol:
        return None

    # Query IEX for quote
    symbols = web.get_iex_symbols().symbol.values.tolist()
    if symbol in symbols:
        return symbol.upper()
    else:
        return None