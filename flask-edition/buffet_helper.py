"""
@author: EM

This is a helper file for the application,
it consists of functional utilities needed by the application.
"""

from flask import redirect
from functools import wraps

import datetime as dt
import pandas as pd
import pandas_datareader.data as web
import pandas_datareader as pdr
from datetime import datetime

def usd(value):
    """
    @author: EM
    Format an amount in usd currency.
    """
    return f"${value:,.2f}"

def login_require(f):
    @wraps(f)
    def decorated_function(*args,**kwargs):
        """
        @author: SA
        Login is required to progress to next page.
        """
        return redirect("/login")
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
