# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.


def print_hi(name):
    # Use a breakpoint in the code line below to debug your script.
    print(name)  # Press Ctrl+F8 to toggle the breakpoint.


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    print_hi('KatarzynaMK')

# See PyCharm help at https://www.jetbrains.com/help/pycharm/

from flask import Flask, render_template, request, flash
from flask_sqlalchemy import SQLAlchemy
import requests


app = Flask(__name__)
app.config["SECRET_KEY"] = 'uniquekeyKMKproject'
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///dataKMKproject.db"
db = SQLAlchemy(app)

url = 'https://coinranking1.p.rapidapi.com/coins'
querystring = {"referenceCurrencyUuid": "yhjMzLPhuIDl", "timePeriod": "24h", "tiers[0]": "1",
               "orderBy": "marketCap", "orderDirection": "desc", "limit": "50", "offset": "0"}
headers = {"X-RapidAPI-Key": "9635177855msh1e6eb00b352d41ap197cd4jsn30ff7100b002",
           "X-RapidAPI-Host": "coinranking1.p.rapidapi.com"}

response = requests.request("GET", url, headers=headers, params=querystring).json()

parameters = {}
for i in range(50):
    symbol = response['data']['coins'][i]['symbol']
    name = response['data']['coins'][i]['name']
    price_USD = float(response['data']['coins'][i]['price'])
    price_USD = round(price_USD, 5)
    price_zlPL = round(price_USD * 4.4, 5)                # --- przyjęto cene 1 USD  4.40 zł
    price_purchase_USD = float(price_USD) * 1.1           # --- założono cene zakupu  większą o 10 %
    price_purchase_USD = round(price_purchase_USD, 5)
    price_purchase_zlPL = round(price_purchase_USD * 4.4, 5)

    parameters[symbol] = [symbol, name, price_USD, price_zlPL, price_purchase_USD, price_purchase_zlPL]


class Balance(db.Model):
    id = db.Column(db.Integer, primary_key=1)
    balance = db.Column(db.Float)


class Wallet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String)
    name = db.Column(db.String)
    qty = db.Column(db.Integer)
    price = db.Column(db.Float)


class History(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    line = db.Column(db.String)


with app.app_context():
    db.create_all()


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/account", methods=['GET', 'POST'])
def account():
    b = Balance.query.get(1)
    rf = request.form
    if rf.get('modified') and float(rf.get('modified')) > 0:
        b.balance += round(float(rf['modified']), 2)
        h = History(line=f"{rf['datetime']}{' __ wpłata : '}{rf['modified']}{' zł / stan konta : '}{b.balance:.2f}{' zł'}")
        db.session.add(h)
        db.session.commit()
    if rf.get('modified') and float(rf.get('modified')) <= 0:
        flash(f"Nieprawidłowa wartość")
    return render_template('account.html', balance=round(b.balance, 2))


@app.route("/operation", methods=['GET', 'POST'])
def operation():
    if not Balance.query.get(1):
        balance = Balance(balance=0)
        with app.app_context():
            db.session.add(balance)
            db.session.commit()
    b = Balance.query.get(1)
    if b.balance == 0:
        flash(f"Zasil konto.")
    return render_template('operation.html', balance=b.balance, parameters=parameters)


@app.route("/coin_purchase", methods=['GET', 'POST'])
def coin_purchase():
    wallet = []
    b = Balance.query.get(1)
    if b.balance == 0:
        flash(f"Zasil konto.")
    rf = request.form
    if rf.get('crypto_symbol') and rf.get('crypto_qty'):
        if int(rf.get('crypto_qty')) < 1:
            flash('Nieprawidłowa wartość.')
        else:
            crypto_price_purchase = parameters[rf.get('crypto_symbol')][5]
            crypto_total_value = float(crypto_price_purchase) * int(rf['crypto_qty'])
            b.balance -= round(crypto_total_value, 2)
            symbol = parameters[rf.get('crypto_symbol')][0]
            name = parameters[rf.get('crypto_symbol')][1]
            price = float(parameters[rf.get('crypto_symbol')][5])
            qty = int(rf['crypto_qty'])
            wallet = Wallet.query.all()
            w = Wallet(symbol=symbol, name=name, qty=qty, price=price)
            if crypto_total_value < 0.01:
                flash('Wartość transakcji jest za niska. Kup większą ilość tej kryptowaluty.')
            else:
                if b.balance > 0:
                    if Wallet.query.filter(Wallet.symbol == rf['crypto_symbol']).first():
                        Wallet.query.filter(Wallet.symbol == rf['crypto_symbol']).first().qty += int(rf['crypto_qty'])
                        h = History(
                            line=f"{rf['datetime']}{' __ zakup : '}{name}{' / ilość : '}{rf['crypto_qty']}{' __ cena/j.: '}{crypto_price_purchase:.5f}{' zł / koszt całkowity : '}{crypto_total_value:.2f}{' zł'}")
                    else:
                        h = History(
                            line=f"{rf['datetime']}{' __ zakup : '}{name}{' / ilość : '}{rf['crypto_qty']}{' __ cena/j.: '}{crypto_price_purchase:.5f}{' zł / koszt całkowity : '}{crypto_total_value:.2f}{' zł'}")
                        db.session.add(w)
                    db.session.add(h)
                    db.session.commit()
                else:
                    b.balance += round(crypto_total_value, 2)
                    flash(f"Koszt jest za wysoki. Jest za mało środków na koncie - zasil konto.")
                db.session.commit()
    return render_template('coin_purchase.html', balance=round(b.balance, 2), wallet=wallet, parameters=parameters)


@app.route("/purse_sell", methods=['GET', 'POST'])
def purse_sell():
    profit = 0
    b = Balance.query.get(1)
    wallet = Wallet.query.all()
    rf = request.form
    if rf.get('crypto_symbol') and rf.get('crypto_qty'):
        if int(rf.get('crypto_qty')) < 1:
            flash('Nieprawidłowa wartość.')
        else:
            name = parameters[rf.get('crypto_symbol')][1]
            crypto_price_sell = parameters[rf.get('crypto_symbol')][3]
            if int(rf['crypto_qty']) > Wallet.query.filter(Wallet.symbol == rf['crypto_symbol']).first().qty:
                flash('Brak takiej ilości kryptowaluty w portfelu.')
            else:
                crypto_total_value = float(crypto_price_sell) * int(rf['crypto_qty'])
                if crypto_total_value < 0.01:
                    flash('Wartość transakcji jest za niska. Sprzedaj większą ilość tej kryptowaluty.')
                else:
                    if wallet:
                        profit = (float(parameters[rf.get('crypto_symbol')][3]) - Wallet.query.filter(
                            Wallet.symbol == rf['crypto_symbol']).first().price) * int(rf['crypto_qty'])
                        profit = round(profit, 2)
                    else:
                        profit = (float(parameters[rf.get('crypto_symbol')][3]) - float(
                            parameters[rf.get('crypto_symbol')][5])) * int(rf['crypto_qty'])
                        profit = round(profit, 2)
                    b.balance += round(crypto_total_value, 2)
                    Wallet.query.filter(Wallet.symbol == rf['crypto_symbol']).first().qty -= int(rf['crypto_qty'])
                    h = History(
                        line=f"{rf['datetime']}{' __ sprzedaż : '}{name}{' / ilość : '}{rf['crypto_qty']}{' __ cena/j.: '}{crypto_price_sell:.5f}{' zł / wartość całkowita : '}{crypto_total_value:.2f}{' zł / zysk : '}{profit:.2f}{' zł'}")
                    if Wallet.query.filter(Wallet.symbol == rf['crypto_symbol']).first().qty == 0:
                        db.session.delete(Wallet.query.filter(Wallet.symbol == rf['crypto_symbol']).first())
                    db.session.add(h)
                    db.session.commit()
    return render_template('purse_sell.html', balance=round(b.balance, 2), wallet=wallet, profit=profit)


@app.route('/history', methods=['GET', 'POST'])
def history():
    part_history = []
    history = History.query.all()
    x = len(history)
    rf = request.form
    if rf.get('line7') and not rf.get('line14') and not rf.get('line30') and not rf.get('line0'):
        if x < 7:
            for i in range(x - 1, -1, -1):
                part_history.append(history[i])
        else:
            for i in range(x - 1, x - 8, -1):
                part_history.append(history[i])
    if rf.get('line14') and not rf.get('line7') and not rf.get('line30') and not rf.get('line0'):
        if x < 14:
            for i in range(x - 1, -1, -1):
                part_history.append(history[i])
        else:
            for i in range(x - 1, x - 15, -1):
                part_history.append(history[i])
    if rf.get('line30') and not rf.get('line7') and not rf.get('line14') and not rf.get('line0'):
        if x < 30:
            for i in range(x - 1, -1, -1):
                part_history.append(history[i])
        else:
            for i in range(x - 1, x - 31, -1):
                part_history.append(history[i])
    if rf.get('line0') and not rf.get('line7') and not rf.get('line14') and not rf.get('line30'):
        for i in range(x - 1, -1, -1):
            part_history.append(history[i])
    return render_template('history.html', part_history=part_history)



