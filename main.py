from flask import Flask, render_template, request
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import sqlite3
import plotly
import plotly.graph_objs as go
import json

app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        return render_template('index.html')

    ticker = request.form.get('ticker')
    start = request.form.get('start')
    end = request.form.get('end')
    data, user_ticker_company_name = get_info(ticker, start, end)

    if data is False:
        return render_template('index.html', user_ticker_company_name="Invalid Ticker")

    write_to_db(data)
    user_ticker = read_from_db()

    start, end = read_dates_from_db()
    end = increase_date_by_1(end)
    spy_ticker, spy_ticker_company_name = get_info('SPY', start, end)

    plot1 = create_line_plot(user_ticker, user_ticker_company_name)
    plot2 = create_candlestick_plot(user_ticker, user_ticker_company_name)
    plot3 = create_macd_plot(user_ticker, user_ticker_company_name)
    average, plot4 = create_moving_average_plot(user_ticker, user_ticker_company_name)
    rsi, plot5 = create_rsi_plot(user_ticker, user_ticker_company_name)
    plot6 = create_comparison_plot(user_ticker, spy_ticker, user_ticker_company_name, spy_ticker_company_name)
    volume = round(user_ticker['Volume'].iloc[-1], 2)
    price = round(user_ticker['Close'].iloc[-1], 2)
    buy_sell = buy_or_sell(rsi)
    return render_template('index.html', plot1=plot1, plot2=plot2, plot3=plot3, plot4=plot4, plot5=plot5,
                           plot6=plot6, user_ticker_company_name=user_ticker_company_name, price=price,
                           volume=volume, rsi=rsi, average=average, buy_sell=buy_sell,ticker=ticker,start=start,end=end)


def create_line_plot(user_ticker, user_ticker_company_name):
    x = user_ticker['Date']
    y = user_ticker['Close']
    df = pd.DataFrame({'x': x, 'y': y})  # creating a sample dataframe

    trace = go.Scatter(
        x=df['x'],
        y=df['y'],
        mode='lines',
        name=user_ticker_company_name
    )

    data = [trace]

    graphJSON = json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder)
    return graphJSON


def create_candlestick_plot(user_ticker, user_ticker_company_name):
    df = user_ticker

    trace = go.Candlestick(
        x=df['Date'],
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name=user_ticker_company_name
    )

    data = [trace]

    graphJSON = json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder)
    return graphJSON


def create_macd_plot(user_ticker, user_ticker_company_name):
    df = user_ticker

    x = user_ticker['Date']
    y = user_ticker['Close']
    df = pd.DataFrame({'x': x, 'y': y})
    exp1 = user_ticker['Close'].ewm(span=12, adjust=False).mean()
    exp2 = user_ticker['Close'].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    exp3 = macd.ewm(span=9, adjust=False).mean()
    macdh = macd - exp3
    trace0 = go.Bar(
        x=df['x'],
        y=macdh,
        name=user_ticker_company_name
    )
    trace1 = go.Scatter(
        x=df['x'],
        y=macd,
        mode='lines',
        name='MACD Line'
    )
    trace2 = go.Scatter(
        x=df['x'],
        y=exp3,
        mode='lines',
        name='Signal Line'
    )

    data = [trace0, trace1, trace2]

    graphJSON = json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder)
    return graphJSON


def create_moving_average_plot(user_ticker, user_ticker_company_name):
    x = user_ticker['Date']
    y = user_ticker['Close']
    df = pd.DataFrame({'x': x, 'y': y})
    rolling_mean = df.y.rolling(window=30).mean()
    rolling_mean2 = df.y.rolling(window=60).mean()
    print(type(rolling_mean))

    trace0 = go.Scatter(
        x=df['x'],
        y=df['y'],
        mode='lines',
        name=user_ticker_company_name
    )
    trace1 = go.Scatter(
        x=df['x'],
        y=rolling_mean,
        mode='lines',
        name='30 Day MA'
    )
    trace2 = go.Scatter(
        x=df['x'],
        y=rolling_mean2,
        mode='lines',
        name='60 Day MA'
    )

    data = [trace0, trace1, trace2]
    average = round(rolling_mean.iloc[-1], 2)
    graphJSON = json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder)
    return average, graphJSON


def create_rsi_plot(user_ticker, user_ticker_company_name):
    delta = user_ticker['Close'].diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=13, adjust=False).mean()
    ema_down = down.ewm(com=13, adjust=False).mean()
    rsi = ema_up / ema_down
    user_ticker['RSI'] = 100 - (100 / (1 + rsi))

    # user_ticker = user_ticker.iloc[14:]

    x = user_ticker['Date']
    y = user_ticker['Close']
    df = pd.DataFrame({'x': x, 'y': y})

    trace1 = go.Scatter(
        x=df['x'],
        y=user_ticker['RSI'],
        mode='lines',
        name='RSI'
    )
    trace2 = go.Scatter(
        x=df['x'],
        y=[30] * len(df['x']),
        line=dict(dash='dash'),
        name='Over Sold'
    )
    trace3 = go.Scatter(
        x=df['x'],
        y=[70] * len(df['x']),
        line=dict(dash='dash'),
        name='Over Bought'
    )
    rsi_last = round(user_ticker['RSI'].iloc[-1], 2)
    data = [trace1, trace3, trace2]

    graphJSON = json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder)
    return rsi_last, graphJSON


def create_comparison_plot(user_ticker, spy_ticker, user_ticker_company_name, spy_ticker_company_name):
    x0 = user_ticker['Date']
    y0 = user_ticker['Close']
    df0 = pd.DataFrame({'x': x0, 'y': y0})

    x1 = spy_ticker['Date']
    y1 = spy_ticker['Close']
    df1 = pd.DataFrame({'x': x1, 'y': y1})

    trace0 = go.Scatter(
        x=df0['x'],
        y=df0['y'],
        mode='lines',
        name=user_ticker_company_name
    )
    trace1 = go.Scatter(
        x=df1['x'],
        y=df1['y'],
        mode='lines',
        name=spy_ticker_company_name
    )

    data = [trace0, trace1]

    graphJSON = json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder)
    return graphJSON


def buy_or_sell(rsi):
    if (rsi <= 100) & (rsi > 65):
        return 'Bull Market - Recommended to Buy'
    elif (rsi <= 65) & (rsi > 55):
        return 'Bear Market - Recommended to Sell'
    elif (rsi <= 55) & (rsi > 35):
        return 'Bull Market - Recommended to Buy'
    elif (rsi <= 35) & (rsi > 0):
        return 'Bear Market - Recommended to Sell'


def get_info(ticker, start, end):
    stock = yf.Ticker(ticker)

    if all([start, end]):
        data = stock.history(start=start, end=end)
    elif start is '' and end is not '':
        data = stock.history(end=end, period="max")
    elif start is not '' and end is '':
        data = stock.history(start=start)
    else:
        data = stock.history(period="max")

    if data.empty:
        return False, False  # no data and company name

    data.reset_index(level=0, inplace=True)
    data.drop(['Dividends', 'Stock Splits'], axis='columns', inplace=True)
    company_name = stock.info.get('longName')

    return data, company_name


def write_to_db(data):
    conn = sqlite3.connect(r"pythonsqlite.db")
    data.to_sql('Stock', conn, if_exists='replace', index=False)
    conn.close()


def read_from_db():
    conn = sqlite3.connect(r"pythonsqlite.db")
    return pd.read_sql('select * from Stock', conn)


def read_dates_from_db():
    conn = sqlite3.connect(r"pythonsqlite.db")
    start = pd.read_sql('select s.Date from Stock s limit 1', conn)['Date'].iloc[0].split()[0]
    end = pd.read_sql('select s.Date from Stock s order by Date desc limit 1', conn)['Date'].iloc[0].split()[0]
    return start, end


def increase_date_by_1(date):
    datetime_object = datetime.strptime(date, '%Y-%m-%d')
    datetime_object += timedelta(days=1)
    return str(datetime_object).split()[0]


if __name__ == '__main__':
    app.run()
