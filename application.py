from flask import Flask, flash, render_template, request, jsonify, redirect, url_for, session, g, send_file, send_from_directory

# BEGIN : Imports for utility functions implemented by the buffett members
from stocky import * # Import all the functions
from models import * # Import all the models
from buffett_helper import * # Import all the helper functions
from newslib import *
from auth_phone import *
from forms import SignupForm, LoginForm, BuyForm, SellForm, SearchForm, SignupCodeForm, UpdatePasswordForm, UnregisterForm # Import for form functionality
# END : Imports for utility funtions
# import the desired hasher
from passlib.hash import pbkdf2_sha256

import csv
import os
import random
import re
import json
import plotly
import plotly.plotly as py
import plotly.graph_objs as go
import numpy as np

# importing tools for sessions
from flask_session import Session
from tempfile import mkdtemp
# end import for sessions

# Imports for database functionality
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
# End of imports for database functionality

########
import datetime as dt
import pandas as pd
import pandas_datareader.data as web
import pandas_datareader as pdr
from datetime import datetime
######

# The name of this application is app
app = Flask(__name__)

# Protecting the form against CSRF security exploit (this exploit is called Cross-Site Request Forgery)
app.secret_key = os.urandom(32)

# begin configuration of application for sessions
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)
# end configuration for sessions

# Relevant variables for database access, implementation and access
# The program shall make use of simple SQLLite for testing and development purposes
# PostgreSQL or MySQL shall be used for production
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///buffett.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)


#################### The rest of the application ####################
@app.route("/")
def home():
    """
    @author: EM

    Implementation of the homepage for the buffett stock market game application.
    """
    symbol = "MSFT"
    # obtaining graph information
    graphdata = plotter(symbol)
    news = get_general_headlines()
    latest = news['articles'][0]['title']

    return render_template("home.html", graphdata=graphdata, latest=latest)

@app.route("/index")
@login_required # This line can be commented out when you are testing out the application.
def index():
    """
    @author: SH
    The homepage of the application.
    """
    # Initialise a search form and relevant variables
    searchForm = SearchForm()
    current_user = None
    symbol = "MSFT"

    # Obtain data about current user using their session data
    username = session["username"]
    # Query the database with the given username
    current_user = User.query.filter_by(username=username).first()
    current_user_amount = usd(current_user.cash)
    # Attempt to overwrite the default value for symbol if the user has bought any stocks before
    if Portfolio.query.filter_by(userid=current_user.id).first() is not None:
        symbol = Portfolio.query.filter_by(userid=current_user.id).first().symbol


    current_price = usd(get_current_share_quote(symbol)['latestPrice'])

    # obtaining graph information
    graphdata = plotter(symbol)

    data = {}
    stock_info = []
    info = {}

    ptf = Portfolio.query.filter_by(userid=current_user.id).all()
    if ptf is not None:
        index = 0
        for stock in ptf:
            total_share_price = stock.quantity * get_current_share_quote(stock.symbol)['latestPrice']
            grand_total = current_user.cash + total_share_price
            info["grand_total"] = usd(grand_total)
            info["total_share_price"] = usd(total_share_price)
            stock_info.append(info)
            index = index + 1


    data["symbol"] = symbol.upper()
    data["amount"] = current_user_amount
    data["current_price"] = current_price
    data["stock_info"] = stock_info

    stocks = Portfolio.query.all()

    company_in = get_company_info(symbol)

    data['exchange'] = company_in['exchange']
    data['industry'] = company_in['industry']
    data['description'] = company_in['description']
    data['sector'] = company_in['sector']
    data['companyName'] = company_in['companyName']

    news = get_general_headlines()

    data['ns1'] = news['articles'][0]['title']
    data['ns1_url'] = news['articles'][0]['url']
    data['ns2'] = news['articles'][1]['title']
    data['ns2_url'] = news['articles'][1]['url']
    data['ns3'] = news['articles'][2]['title']
    data['ns3_url'] = news['articles'][2]['url']

    similar = get_similar_stocks(symbol)

    # calling the utility function for autocomplete
    quotes = search_autocomplete()

    #initialise leaderboard position
    counter = 1
    data['current_position'] = 1

    users = User.query.order_by(User.cash.desc()).all()
    for user in users:

        if username.lower() == user.username.title().lower():
            data['current_position'] = counter
        counter += 1

    return render_template('index.html', data=data, stocks=stocks, searchForm=searchForm, graphdata=graphdata, quotes=quotes, similar=similar)


@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    """
    @author: SH
    Functionality for the search function.
    """
    # Initiliase the form and relevant local variables
    searchForm = SearchForm()
    symbol = None

    if searchForm.validate_on_submit():
        symbol = searchForm.search.data.upper()
        symbol = str(re.split(" ", symbol, 1)[0])

        users = User.query.all()
        user = User.query.first()
        amt = usd(user.cash)

        if symbol is None:
            flash('Please make sure you have provided the right symbol')
            return redirect(url_for("index"))

        # obtaining graph information
        graphdata = plotter(symbol)

        current_price = get_current_share_quote(symbol)['latestPrice'] # This line needs to be corrected

        data = {}
        data["symbol"] = symbol.upper()
        data["amount"] = amt
        data["current_price"] = current_price

        company_in = get_company_info(symbol)

        data['exchange'] = company_in['exchange']
        data['industry'] = company_in['industry']
        data['description'] = company_in['description']
        c_name = get_company_name(symbol)

        news = search_headlines(c_name)
        data['ns1'] = news['articles'][0]['title']
        data['ns1_url'] = news['articles'][0]['url']
        data['ns2'] = news['articles'][1]['title']
        data['ns2_url'] = news['articles'][1]['url']
        data['ns3'] = news['articles'][2]['title']
        data['ns3_url'] = news['articles'][2]['url']

        similar = get_similar_stocks(symbol)

        # calling the utility function for autocomplete
        quotes = search_autocomplete()
        to_csv(get_month_chart(symbol, 3))

        return render_template('index.html', searchForm=searchForm, data=data, users=users, user=user, graphdata=graphdata, quotes=quotes, similar=similar)
    return redirect(url_for("index"))


@app.route("/export")
@login_required
def export():
    """
    @author: EM & SH

    Implementation of the export feature.
    """
    fname = "iex.csv"
    try:
        return send_file(os.path.dirname(fname) + fname, attachment_filename=fname)
    except Exception as e:
        return str(e)

@app.route("/settings")
@login_required
def settings():
    """
    @author: EM

    Implementation of the settings feature.
    """
    searchForm = SearchForm()
    passwordForm = UpdatePasswordForm()
    # calling the utility function for autocomplete
    quotes = search_autocomplete()
    settings = {}
    return render_template("settings.html", searchForm=searchForm, quotes=quotes, settings=settings, form=passwordForm)

@app.route("/passwordupdate", methods=["GET", "POST"])
@login_required
def passwordupdate():
    """
    @author: EM

    Implementation of the password update feature.
    """
    passwordForm = UpdatePasswordForm()
    if passwordForm.validate_on_submit():
        flash(f"{session['username'].title()}, you have successfully changed your password.", "success")
        return redirect(url_for("index"))
    return redirect(url_for("settings"))

@app.route("/profile")
@login_required
def profile():
    """
    @author: EM
    Implementation of the profile feature.
    """
    return redirect(url_for("dashboard"))

@app.route("/dashboard")
@login_required
def dashboard():
    """
    @author: EM
    Functionality for the user dashboard/portfolio function.
    """
    # Initialise the form and relevant variables
    searchForm = SearchForm()

    data = {}
    info = {}
    portfolio = []
    stocks = Portfolio.query.all()

    for stock in stocks:
        temp = {}
        temp["symbol"] = stock.symbol
        temp["shares"] = stock.quantity
        temp["companyName"] = get_company_info(stock.symbol)["companyName"]
        portfolio.append(temp)

    user = User.query.first()
    amt = usd(user.cash)
    info["user_cash"] = amt
    grand_total = user.cash

    for item in stocks:
        company_info = get_company_info(item.symbol)
        current_price = get_current_share_quote(item.symbol)['latestPrice']

        # record the name and current price of this stock
        info[item.symbol+"price"] = usd(current_price)
        info[item.symbol+"total"] = current_price * item.quantity

        if len(stocks) == len(stocks):
            for k, value in info.items():
                if k == item.symbol+"total":
                    grand_total = float(grand_total) + float(value)
            info["g_total"] = usd(grand_total)
        info[item.symbol+"total"] = usd(current_price * item.quantity)

    # calling the utility function for autocomplete
    quotes = search_autocomplete()

    return render_template("portfolio.html", portfolio=portfolio, info=info, searchForm=searchForm, quotes=quotes)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """
    @author: EM
    Functionality for the user to buy some stocks.
    """
    # Initialise the relevant forms
    buyForm = BuyForm()
    searchForm = SearchForm()

    # calling the utility function for autocomplete
    quotes = search_autocomplete()

    if buyForm.validate_on_submit():
        # Get form information
        symbol = buyForm.symbol.data.upper()
        is_symbol = quote_validate(symbol)
        if is_symbol is None:
            flash("Please enter a valid quote to buy some shares.", "warning")
            return redirect(url_for("buy"))

        noOfShares = int(buyForm.shares.data)
        if noOfShares < 1:
            flash("Please enter a number greater than zero to buy some stocks.", "warning")
            return redirect(url_for("buy"))

        # contact API
        company_info = get_company_info(symbol)
        # confirm the symbol exists in the database
        if type(get_current_share_quote(symbol)) is not dict:
            flash(get_current_share_quote(symbol))
            return redirect(url_for("buy"))
        else:
            current_price = get_current_share_quote(symbol)['latestPrice']

        # Now it is certain the user has entered the correct data
        # obtaining graph information
        graphdata = plotter(symbol)

        # Query database
        # Based on the id of the currently logged in user , obtain this id from the session variable
        us = User.query.filter_by(username=session['username']).first()
        userid = us.id
        user = User.query.get(userid)

        total_cost = (float(noOfShares) * current_price)
        # Check if the user can afford the stocks they want to buy
        if total_cost > user.cash:
            # send the user to thier dashboard
            flash("Check that you have enough money to buy stocks.", "warning")
            return redirect(url_for("dashboard"))
        else:
            # update cash for user in the database
            user.cash -= total_cost
            # update portfolio table
            portf = Portfolio(userid=userid, symbol=symbol.upper(), quantity=noOfShares, transaction_type="buy")
            db.session.add(portf)
            # update history table
            hist = History(userid=userid, symbol=symbol.upper(), quantity=noOfShares, transaction_type="buy")
            db.session.add(hist)
            # commit the changes made to the database
            db.session.commit()

            # Notify the user about their recent trade
            send_buy_confirmation(symbol, noOfShares)

        # Putting together a summary of the users current transaction
        data = {}
        data["symbol"] = symbol.upper()
        data["noOfShares"] = noOfShares
        data["current_price"] = usd(current_price)
        data["amount"] = usd(user.cash)

        company_in = get_company_info(symbol)

        data['exchange'] = company_in['exchange']
        data['industry'] = company_in['industry']
        data['description'] = company_in['description']
        data['sector'] = company_in['sector']
        data['companyName'] = company_in['companyName']

        # Prepare some information to show the user thier portfolio
        stocks = Portfolio.query.all()
        ptf = Portfolio.query.filter_by(userid=int(1)).all()
        if ptf is not None:
            for stock in ptf:
                grand_total = user.cash + (stock.quantity * get_current_share_quote(stock.symbol)['latestPrice'])
                data["grand_total"] = usd(grand_total)

        flash(f"You have bought shares from {data['companyName']} worth {usd(current_price)}!", "success")

        return render_template('index.html',
                        data=data, searchForm=searchForm, stocks=stocks, graphdata=graphdata, quotes=quotes)

    # the code below is executed if the request method
    # was GET or there was some sort of error
    return render_template("buy.html", buyForm=buyForm, searchForm=searchForm, quotes=quotes)


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """
    @author: EM
    Functionality for the user sell function.
    """
    # Enable selling of shares
    # Remove stock from user's portfolio // or // add a new row with a negative value for the number of shares
    # You can use DELETE or log the sale as a negative quantity
    # Update cash/value of user [the stock is sold at its current price]
    # return success or failure message

    # Initialise the relevant forms and relevant variables
    sellForm = SellForm()
    searchForm = SearchForm()
    error = None

    # calling the utility function for autocomplete
    quotes = search_autocomplete()

    # Validate that the sell form was submitted via post and that the contents of the form were valid
    if sellForm.validate_on_submit():
        # Get form information
        symbol = sellForm.symbol.data.upper()
        is_symbol = quote_validate(symbol)
        if is_symbol is None:
            flash("Please enter a valid quote to sell some shares.", "warning")
            return redirect(url_for("sell"))
        noOfShares = int(sellForm.shares.data)

        # contact API
        company_info = get_company_info(symbol)
        current_price = get_current_share_quote(symbol)['latestPrice']

        # obtaining graph information
        graphdata = plotter(symbol)

        # Query database
        # Based on the id of the currently logged in user , obtain this id from the session variable
        current_user = User.query.filter_by(username=session['username']).first()
        userid = current_user.id
        user = User.query.get(userid)

        # Calculate the total cost of shares the user wants to sell based on the current price
        total_cost = (float(noOfShares) * current_price)
        # Query the database to confirm the user owns a particular share they wish to sell
        share = Portfolio.query.filter_by(symbol=symbol).first()
        if share is None:
            flash("You attempted to sell a share you do not currently own.", "warning")
            return redirect(url_for("sell"))

        # Query the database to confirm the user is selling the proper amount of shares
        # In other words, the user must not sell 3 shares if they only own 1 share for a particular stock
        if share.quantity < noOfShares:
            flash("You attempted to sell more shares than you currently own.", "warning")
            return redirect(url_for("sell"))

        # update portfolio table if the user is able to sell the shares
        # if number of shares is 2 or more then update row otherwise just delete the row
        portf = Portfolio.query.filter_by(userid=userid,symbol=symbol).first()
        if portf is not None:
            if portf.quantity > 1:
                # update the number of shares in the users portfolio
                portf.quantity = portf.quantity - noOfShares
                # update the users cash value
                user.cash = user.cash + total_cost
                # Commit the above changes to the database
                db.session.commit()
            else:
                # update the number of shares in the users portfolio
                db.session.delete(portf)
                # update the users cash value
                user.cash = user.cash + total_cost
                # Commit the above changes to the database
                db.session.commit()
            flash(f"You have sold some shares worth {usd(current_price)}.", "success")
        else:
            # no such stock exist
            flash("You attempted to sell a share you do not currently own.", "warning")
            return redirect(url_for("sell"))

        # update history table
        History().add_hist(userid, symbol.upper(), -noOfShares, "sell")

        data = {}
        data["symbol"] = symbol.upper()
        data["noOfShares"] = noOfShares
        data["current_price"] = usd(current_price)
        data["amount"] = usd(user.cash)

        company_in = get_company_info(symbol)

        data['exchange'] = company_in['exchange']
        data['industry'] = company_in['industry']
        data['description'] = company_in['description']
        data['sector'] = company_in['sector']
        data['companyName'] = company_in['companyName']

        stocks = Portfolio.query.all()
        ptf = Portfolio.query.filter_by(userid=int(1)).all()
        if ptf is not None:
            for stock in ptf:
                grand_total = user.cash + (stock.quantity * get_current_share_quote(stock.symbol)['latestPrice'])
                data["grand_total"] = usd(grand_total)

        return render_template('index.html',
                        data=data, sellForm=sellForm, searchForm=searchForm, stocks=stocks, graphdata=graphdata, quotes=quotes)

    return render_template("sell.html", sellForm=sellForm, searchForm=searchForm, error=error, quotes=quotes)

@app.route("/history")
@login_required
def history():
    """
    @author: EM
    Functionality for the history function.

    This will show all the transactions that the user has made over time
    """
    # Initialise the search form and relevant variables
    searchForm = SearchForm()
    hist = []

    history = History.query.all()
    if history is None:
        # Just show the index page for now.
        flash("You currently have no record on any transactions.", "info")
        return redirect(url_for("index"))

    # It appears that the user has records in their history table therefore prepare this data and present it to the user
    for stock in history:
        temp = {}
        temp["symbol"] = stock.symbol
        temp["shares"] = stock.quantity
        temp["companyName"] = get_company_info(stock.symbol)["companyName"]
        temp["current_price"] = usd(get_current_share_quote(stock.symbol)['latestPrice'])
        temp["transaction_date"] = stock.transaction_date
        temp["transaction_type"] = stock.transaction_type
        hist.append(temp)

    # calling the utility function for autocomplete
    quotes = search_autocomplete()

    return render_template("history.html", searchForm=searchForm, hist=hist, quotes=quotes)

@app.route("/summary")
@login_required
def summary():
    """
    @author: EM
    Functionality for the summary function.
    """
    # Initialise the search form for this route
    searchForm = SearchForm()
    # graph stuff
    symbol = "MSFT"
    graphdata = plotter(symbol)
    # Showing open positions for the loggedin user
    stocks = Portfolio.query.all()
    data = {}
    for stock in stocks:
        current_stock = get_company_info(stock.symbol)

    company_in = get_company_info(symbol)
    data["companyName"] = get_company_info(symbol)["companyName"]
    data["symbol"] = symbol.upper()
    data['exchange'] = company_in['exchange']
    data['industry'] = company_in['industry']
    data['description'] = company_in['description']
    data['sector'] = company_in['sector']
    data["current_price"] = usd(get_current_share_quote(symbol)["latestPrice"])

    # calling the utility function for autocomplete
    quotes = search_autocomplete()

    return render_template("index.html", graphdata=graphdata, searchForm=searchForm, data=data, quotes=quotes)

@app.route("/unregister", methods=["GET", "POST"])
def unregister():
    """
     @author: SA

    Implementation of the unregister function.
    """
    unregisterForm = UnregisterForm()

    if unregisterForm.validate_on_submit():
        user = User.query.filter_by(username=session["username"]).first()
        password = unregisterForm.password.data
        hash = user.password

        if pbkdf2_sha256.verify(password, hash) == True:
            db.session.delete(user)
            db.session.commit()


            flash(f"You have successfully unregistered! :(", "success")

            return redirect(url_for("signup"))
        return redirect(url_for("unregister"))

    return render_template("unregister.html", form=unregisterForm)

@app.route("/initdb")
def main():
    # Create a database with tables
    # This method will only be called at the beginning of the program
    # to initiate the database and never again.
    db.create_all()
    # Register some stub users
    f = open("users.csv")
    reader = csv.reader(f)
    users = User.query.all()

    if len(users) == 0:
        for name, passcode, number in reader:
            user = User(username=name, password=pbkdf2_sha256.hash(passcode), phone_number=number)
            db.session.add(user)
            print("A stub user has been added.")
        db.session.commit()

    return "db initialized"


@app.route("/signupcode", methods=["GET", "POST"])
def signupcode():
    """
    @author: EM

    This is an implementation of user authentication.
    """
    form = SignupCodeForm()
    if form.validate_on_submit():
        acode = form.signup_code.data
        if acode == session["a_code"]:
            flash(f"Welcome {session['username'].title()}, you were successfully registered!", "success")
            return redirect(url_for("index"))
        flash(f"Authentication code entered is incorrect.", "danger")
        return render_template("authcode.html", form=form)
    return render_template("authcode.html", form=form)

@app.route("/signup", methods=["GET", "POST"])
def signup():
    """
    @author: EM

    This is an implementation of user registration for the buffett application.
    """
    signupForm = SignupForm()
    error = None
    authcode = ""

    if signupForm.validate_on_submit():
        # The user has supplied credentials that meet the expected input
        # Obtain form data
        username = signupForm.username.data
        password = signupForm.password.data
        passhash = pbkdf2_sha256.hash(password)
        phone_number = signupForm.phone_number.data
        phone_number = prepare_phone_number(phone_number)

        # Adding a new user to the database
        db.session.add(User(username=username, password=passhash, phone_number=phone_number))
        db.session.commit()

        session["username"] = username

        # Prompt the user for an authentication code to be confirmed
        # Generate a six digit random number
        for i in range(6):
            authcode += str(random.randint(0, 9))
        session["a_code"] = authcode
        # Authentication code can be sent to the user here or using sessions
        flash(f"Authentication code is {authcode}", "success")
        return redirect(url_for("signupcode"))
    # Else the form was submitted via get
    return render_template("signup.html", form=signupForm, error=error)

@app.route("/login", methods=["GET", "POST"])
def login():
    """
    @author: EM
    @author: SA
    """
    loginForm = LoginForm()
    error = None

    if loginForm.validate_on_submit():
        username = loginForm.username.data
        password = loginForm.password.data

        usr = User.query.all()
        user = None
        for u in usr:
            un = u.username
            ph = u.password
            if pbkdf2_sha256.verify(password, ph) == True:
                user = u
                break

        if user is not None:
            session["logged_in"] = True
            session["username"] = username
            flash(f"{session['username'].title()}, you are successfully logged in!", "success")
            return redirect(url_for("index"))
        else:
            flash("You have entered an incorrect username or password.", "danger")
            return redirect(url_for("login"))

    # rendering login page
    return render_template("login.html", form=loginForm)

@app.route("/logout")
@login_required
def logout():
    """
    @author: EM
    Implementation of the logout function.
    """
    session.clear()
    session.pop("username", None)
    session.pop("logged_in", False)
    flash("You have successfully logged out.", "info")
    return redirect(url_for("login"))

@app.route("/gainers")
@login_required
def gainers():
    """
    @author: EM

    Functionality to generate information regarding the most declined stocks
    based on the stocks owned by users of the buffett stock market game.
    """
    # Initiliase the form and relevant local variables
    searchForm = SearchForm()
    stocks_symbols = []
    ptf = Portfolio.query.all()

    for stock in ptf:
        stocks_symbols.append(stock.symbol)

    # Remove duplicates
    stocks_symbols_d = list(dict.fromkeys(stocks_symbols))

    gainers = get_gainers_losers(stocks_symbols_d, tag="g")

    # calling the utility function for autocomplete
    quotes = search_autocomplete()

    return render_template("gainers.html", searchForm=searchForm, data=gainers, quotes=quotes)

@app.route("/losers")
@login_required
def losers():
    """
    @author: EM

    Functionality to generate information regarding the most advanced stocks
    based on the stocks owned by users of the buffett stock market game
    """
    # Initiliase the form and relevant local variables
    searchForm = SearchForm()
    stocks_symbols = []
    ptf = Portfolio.query.all()

    for stock in ptf:
        stocks_symbols.append(stock.symbol)

    # Remove duplicates
    stocks_symbols_d = list(dict.fromkeys(stocks_symbols))

    losers = get_gainers_losers(stocks_symbols_d, tag="l")

    # calling the utility function for autocomplete
    quotes = search_autocomplete()

    return render_template("losers.html", searchForm=searchForm, data=losers, quotes=quotes)

@app.route("/leaderboard")
@login_required
def leaderboard():
    """
    @author: EM + SH

    Functionality to generate information to rank users of the buffett stock market game
    based on their net value of stocks.
    """
    # Initiliase the form and relevant local variables
    searchForm = SearchForm()
    data = []
    vals = []

    # Prepare info for leaderboard display
    users = User.query.order_by(User.cash.desc()).all()
    # Day Change = (open price - close price) * number of shares owned
    # It is assumed that all the users reinvest their paid dividends by buying more shares and/or increasing thier capital
    # Therefore, Total Change = (total gains / initial investment value) * 100 expressed as a %
    for user in users:
        temp = {}
        portfolio = Portfolio.query.filter_by(userid=user.id).all()
        temp["userName"] = user.username.title()
        temp["netValue"] = usd(user.cash)
        temp["numberOfTrades"] = len(History.query.filter_by(userid=user.id).all())
        i = 0
        total_gain = 0
        total_by_price = 0
        for stock in portfolio:
            open_price = prepare_leaderboard(stock.symbol)["open_price"][-1]
            close_price = prepare_leaderboard(stock.symbol)["close_price"][-1]
            shares_owned = Portfolio.query.filter_by(userid=user.id, symbol=stock.symbol).first().quantity
            day_change = (close_price - open_price) * shares_owned

            vals.append(day_change)

            temp["dayChange"] = f"{sum(vals):.2f}"

            # Multiply the number of shares you own of each stock by its dividends per share only if it pays a dividend
            # access the amount key
            dividend = requests.get(f"https://api.iextrading.com/1.0/stock/{stock.symbol.lower()}/dividends/1m").json()
            if len(dividend) != 0:
                for v in dividend:
                    total_gain += stock.quantity * v["amount"]

            # Multiply the number of shares you own of each stock by its price regardless of whether or not it pays a dividend.
            total_by_price += stock.quantity * get_current_share_quote(stock.symbol)['latestPrice']

            if i == len(portfolio) - 1:
                total_change = (total_gain / total_by_price) * 100
                temp["totalChange"] = f"{total_change:.2f}"
            i = i + 1

        data.append(temp)

    # calling the utility function for autocomplete
    quotes = search_autocomplete()

    return render_template("leaderboard.html", searchForm=searchForm, data=data, quotes=quotes)


if __name__ == "__main__":
    """
    @author: EM
    This is the main entry of the program.

    Debug has been set to true for development purposes.
    This program can now be executed by typing "python application.py" or "python3 application.py"
    provided you are in the current directory of application.py
    """
    with app.app_context():
        main()  # Calling the main function to initialise the database
    app.run(debug=True)
